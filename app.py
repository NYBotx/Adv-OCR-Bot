# app.py
import os
import logging
import easyocr
import pytesseract
import cv2
import numpy as np
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from motor.motor_asyncio import AsyncIOMotorClient
import io
import aiohttp
from datetime import datetime
from langdetect import detect
from googletrans import Translator
import tempfile
from pdf2image import convert_from_path
import json

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')

# Initialize MongoDB
client = AsyncIOMotorClient(MONGO_URI)
db = client.ocr_bot_db
users_collection = db.users
history_collection = db.history

# Initialize EasyOCR reader
reader = easyocr.Reader(['en', 'ch_sim', 'ja', 'ko', 'ru', 'ar', 'hi', 'th', 'vi', 'fr', 'de', 'es'])

# Supported languages
LANGUAGES = {
    'eng': 'English 🇬🇧',
    'spa': 'Spanish 🇪🇸',
    'fra': 'French 🇫🇷',
    'deu': 'German 🇩🇪',
    'ita': 'Italian 🇮🇹',
    'por': 'Portuguese 🇵🇹',
    'rus': 'Russian 🇷🇺',
    'jpn': 'Japanese 🇯🇵',
    'kor': 'Korean 🇰🇷',
    'chi_sim': 'Chinese Simplified 🇨🇳',
    'ara': 'Arabic 🇸🇦',
    'hin': 'Hindi 🇮🇳',
    'tha': 'Thai 🇹🇭',
    'vie': 'Vietnamese 🇻🇳'
}

class OCRBot:
    def __init__(self):
        self.translator = Translator()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        user = update.effective_user
        welcome_text = (
            f"👋 Hello {user.first_name}!\n\n"
            "Welcome to the OCR Bot! I can help you with:\n"
            "🔍 Extracting text from images\n"
            "📄 Processing PDF documents\n"
            "🌍 Translation services\n"
            "📊 Text analysis\n\n"
            "Send me any image or PDF to get started!"
        )

        keyboard = [
            [InlineKeyboardButton("📚 Help", callback_data='help'),
             InlineKeyboardButton("⚙️ Settings", callback_data='settings')],
            [InlineKeyboardButton("🌍 Languages", callback_data='languages')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await users_collection.update_one(
            {'user_id': user.id},
            {
                '$set': {
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_seen': datetime.utcnow(),
                    'settings': {
                        'use_enhanced_ocr': True,
                        'auto_translate': False,
                        'preferred_lang': 'eng'
                    }
                }
            },
            upsert=True
        )

        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

    async def process_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process images with OCR"""
        try:
            processing_msg = await update.message.reply_text("🔄 Processing image...")
            
            # Get user settings
            user_data = await users_collection.find_one({'user_id': update.effective_user.id})
            use_enhanced_ocr = user_data.get('settings', {}).get('use_enhanced_ocr', True)
            
            # Get image file
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(file.file_path) as response:
                    image_data = await response.read()
            
            # Convert to np array
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if use_enhanced_ocr:
                try:
                    # Preprocess
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    denoised = cv2.fastNlMeansDenoising(gray)
                    
                    # EasyOCR
                    results = reader.readtext(denoised)
                    text = "\n".join([result[1] for result in results if len(result) >= 2])
                    ocr_method = 'easyocr'
                except:
                    use_enhanced_ocr = False
            
            if not use_enhanced_ocr:
                # Fallback to Tesseract
                image = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                text = pytesseract.image_to_string(image)
                ocr_method = 'tesseract'
            
            if not text.strip():
                await processing_msg.edit_text("⚠️ No text detected in the image.")
                return
            
            # Detect language
            try:
                detected_lang = detect(text)
            except:
                detected_lang = 'unknown'
            
            # Store in history
            await history_collection.insert_one({
                'user_id': update.effective_user.id,
                'text': text,
                'detected_language': detected_lang,
                'timestamp': datetime.utcnow(),
                'image_file_id': photo.file_id,
                'ocr_method': ocr_method
            })
            
            keyboard = [
                [InlineKeyboardButton("🔄 Translate", callback_data=f'translate_{detected_lang}'),
                 InlineKeyboardButton("📋 Copy", callback_data='copy')],
                [InlineKeyboardButton("📊 Analysis", callback_data='analyze')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_msg.edit_text(
                f"📝 *Extracted Text:*\n\n{text}\n\n"
                f"🌍 Detected Language: {LANGUAGES.get(detected_lang, detected_lang)}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            await processing_msg.edit_text("❌ Error processing image. Please try again.")

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document uploads"""
        document = update.message.document
        
        if document.mime_type == 'application/pdf':
            await self.process_pdf(update, context)
        elif document.mime_type.startswith('image/'):
            processing_msg = await update.message.reply_text("🔄 Processing document...")
            
            file = await context.bot.get_file(document.file_id)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(file.file_path) as response:
                    image_data = await response.read()
            
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_file.write(image_data)
                temp_file.flush()
                
                sent_photo = await update.message.reply_photo(photo=open(temp_file.name, 'rb'))
                update.message.photo = [sent_photo.photo[-1]]
                await self.process_image(update, context)
                
                os.unlink(temp_file.name)
            
            await processing_msg.delete()
        else:
            await update.message.reply_text("⚠️ Please send a PDF or image file.")

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'help':
            help_text = (
                "🤖 *Available Commands:*\n\n"
                "/start - Start the bot\n"
                "/help - Show this help message\n"
                "/settings - Configure your preferences\n\n"
                "📝 *How to use:*\n"
                "1. Send any image or PDF containing text\n"
                "2. Wait for the text extraction\n"
                "3. Use the buttons to translate or analyze the text"
            )
            await query.message.edit_text(help_text, parse_mode='Markdown')
            
        elif query.data == 'settings':
            await self.show_settings(query.message, query.from_user.id)
            
        elif query.data.startswith('translate_'):
            await self.handle_translation(query)
            
        elif query.data == 'analyze':
            await self.analyze_text(query.message)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        if update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again later."
            )

    async def show_settings(self, message, user_id):
        """Show user settings"""
        user = await users_collection.find_one({'user_id': user_id})
        settings = user.get('settings', {})
        
        keyboard = [
            [InlineKeyboardButton(
                f"{'✅' if settings.get('use_enhanced_ocr', True) else '❌'} Enhanced OCR",
                callback_data='toggle_ocr'
            )],
            [InlineKeyboardButton(
                f"{'✅' if settings.get('auto_translate', False) else '❌'} Auto Translate",
                callback_data='toggle_translate'
            )],
            [InlineKeyboardButton("⬅️ Back", callback_data='start')]
        ]
        
        await message.edit_text(
            "⚙️ *Settings:*\n\n"
            f"🔍 Enhanced OCR: {'Enabled' if settings.get('use_enhanced_ocr', True) else 'Disabled'}\n"
            f"🔄 Auto Translate: {'Enabled' if settings.get('auto_translate', False) else 'Disabled'}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def analyze_text(self, message):
        """Analyze extracted text"""
        text = message.text.split('\n\n')[1]
        
        analysis = {
            'characters': len(text),
            'words': len(text.split()),
            'lines': len(text.splitlines()),
            'spaces': text.count(' '),
            'numbers': sum(c.isdigit() for c in text),
            'special': sum(not c.isalnum() and not c.isspace() for c in text)
        }
        
        analysis_text = (
            "📊 *Text Analysis:*\n\n"
            f"📝 Characters: {analysis['characters']}\n"
            f"📚 Words: {analysis['words']}\n"
            f"📋 Lines: {analysis['lines']}\n"
            f"⚪ Spaces: {analysis['spaces']}\n"
            f"🔢 Numbers: {analysis['numbers']}\n"
            f"❗ Special Characters: {analysis['special']}"
        )
        
        await message.reply_text(analysis_text, parse_mode='Markdown')

def main():
    """Start the bot"""
    bot = OCRBot()
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(MessageHandler(filters.PHOTO, bot.process_image))
    application.add_handler(MessageHandler(filters.Document.ALL, bot.handle_document))
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    application.add_error_handler(bot.error_handler)
    
    # Start the Bot
    print("🤖 Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
