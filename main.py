import os
import logging
import easyocr
import fitz  # PyMuPDF
import numpy as np
import cv2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Animation, Document
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from PIL import Image
import pytesseract
from langdetect import detect
from googletrans import Translator
from motor.motor_asyncio import AsyncIOMotorClient
import io
import aiohttp
from datetime import datetime
import tempfile
import asyncio
from pdf2image import convert_from_path
import json

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# Initialize MongoDB connection
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(MONGO_URI)
db = client.ocr_bot_db
users_collection = db.users
history_collection = db.history

# Initialize EasyOCR reader
reader = easyocr.Reader(['en', 'ch_sim', 'ja', 'ko', 'ru', 'ar', 'hi', 'th', 'vi', 'fr', 'de', 'es'])

# Enhanced language support
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
    'vie': 'Vietnamese 🇻🇳',
    'ben': 'Bengali 🇧🇩',
    'tur': 'Turkish 🇹🇷'
}

class AdvancedOCRBot:
    def __init__(self):
        self.translator = Translator()
        self.processing_tasks = {}
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message when the command /start is issued."""
        user = update.effective_user
        welcome_text = (
            f"👋 Hello {user.first_name}!\n\n"
            "I'm an advanced OCR Bot that can:\n"
            "🔍 Extract text from images\n"
            "📄 Process PDF documents\n"
            "🌍 Support multiple languages\n"
            "📝 Enhance text recognition\n"
            "🔄 Provide translations\n\n"
            "Send me any image or PDF to get started!"
        )
        
        keyboard = [
            [InlineKeyboardButton("📚 Help", callback_data='help'),
             InlineKeyboardButton("🌍 Languages", callback_data='languages')],
            [InlineKeyboardButton("⚙️ Settings", callback_data='settings'),
             InlineKeyboardButton("📊 History", callback_data='history')]
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
                        'preferred_lang': 'eng',
                        'auto_translate': False,
                        'use_enhanced_ocr': True
                    }
                }
            },
            upsert=True
        )
        
        await update.message.reply_animation(
            animation='https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif',
            caption=welcome_text,
            reply_markup=reply_markup
        )

    async def process_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process PDF documents."""
        try:
            # Send processing message
            processing_msg = await update.message.reply_text("📄 Processing PDF document...")
            
            # Download PDF file
            file = await context.bot.get_file(update.message.document.file_id)
            
            with tempfile.NameporaryDirectory() as temp_dir:
                pdf_path = os.path.join(temp_dir, "document.pdf")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(file.file_path) as response:
                        pdf_data = await response.read()
                        
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_data)
                
                # Convert PDF to images
                images = convert_from_path(pdf_path)
                
                # Process each page
                all_text = []
                for i, image in enumerate(images):
                    await processing_msg.edit_text(f"📄 Processing page {i+1}/{len(images)}...")
                    
                    # Convert PIL image to numpy array for EasyOCR
                    img_np = np.array(image)
                    
                    # Use EasyOCR for text extraction
                    results = reader.readtext(img_np)
                    page_text = "\n".join([text for _, text, conf in results if conf > 0.5])
                    all_text.append(f"Page {i+1}:\n{page_text}\n")
                
                # Combine results
                final_text = "\n".join(all_text)
                
                # Store in history
                await history_collection.insert_one({
                    'user_id': update.effective_user.id,
                    'text': final_text,
                    'source_type': 'pdf',
                    'filename': update.message.document.file_name,
                    'timestamp': datetime.utcnow()
                })
                
                # Create response keyboard
                keyboard = [
                    [InlineKeyboardButton("📥 Download Text", callback_data='download_text'),
                     InlineKeyboardButton("🔄 Translate", callback_data='translate')],
                    [InlineKeyboardButton("📊 Analysis", callback_data='analyze'),
                     InlineKeyboardButton("💾 Save", callback_data='save')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Send results
                if len(final_text) > 4000:
                    # Split long text into multiple messages
                    chunks = [final_text[i:i+4000] for i in range(0, len(final_text), 4000)]
                    for i, chunk in enumerate(chunks):
                        if i == 0:
                            await processing_msg.edit_text(
                                f"📄 Extracted Text (Part {i+1}/{len(chunks)}):\n\n{chunk}",
                                reply_markup=reply_markup if i == len(chunks)-1 else None
                            )
                        else:
                            await update.message.reply_text(
                                f"📄 Extracted Text (Part {i+1}/{len(chunks)}):\n\n{chunk}",
                                reply_markup=reply_markup if i == len(chunks)-1 else None
                            )
                else:
                    await processing_msg.edit_text(
                        f"📄 Extracted Text:\n\n{final_text}",
                        reply_markup=reply_markup
                    )
                
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            await update.message.reply_text(
                "❌ Sorry, an error occurred while processing your PDF. Please try again."
            )

    async def process_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process images with enhanced OCR capabilities."""
        try:
            processing_msg = await update.message.reply_text("🔄 Processing image...")
            
            # Get user settings
            user_settings = await users_collection.find_one({'user_id': update.effective_user.id})
            use_enhanced_ocr = user_settings.get('settings', {}).get('use_enhanced_ocr', True)
            
            # Get image file
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(file.file_path) as response:
                    image_data = await response.read()
            
            # Process with EasyOCR if enhanced OCR is enabled
            if use_enhanced_ocr:
                # Convert bytes to numpy array
                nparr = np.frombuffer(image_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                # Preprocess image
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                denoised = cv2.fastNlMeansDenoising(gray)
                
                # Use EasyOCR
                results = reader.readtext(denoised)
                text = "\n".join([text for _, text, conf in results if conf > 0.5])
            else:
                # Fallback to Tesseract
                image = Image.open(io.BytesIO(image_data))
                text = pytesseract.image_to_string(image)
            
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
                'ocr_method': 'easyocr' if use_enhanced_ocr else 'tesseract'
            })
            
            # Create response keyboard
            keyboard = [
                [InlineKeyboardButton("🔄 Translate", callback_data=f'translate_{detected_lang}'),
                 InlineKeyboardButton("📋 Copy", callback_data='copy')],
                [InlineKeyboardButton("🔍 Enhanced OCR", callback_data='enhanced_ocr'),
                 InlineKeyboardButton("📊 Analysis", callback_data='analyze')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_msg.edit_text(
                f"📝 *Extracted Text:*\n\n{text}\n\n"
                f"🌍 Detected Language: {LANGUAGES.get(detected_lang, detected_lang)}\n"
                f"🔍 OCR Method: {'Enhanced (EasyOCR)' if use_enhanced_ocr else 'Standard (Tesseract)",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            await update.message.reply_text(
                "❌ Sorry, an error occurred while processing your image. Please try again."
            )

    async def analyze_text(self, text: str):
        """Analyze extracted text for additional insights."""
        analysis = {
            'word_count': len(text.split()),
            'character_count': len(text),
            'line_count': len(text.splitlines()),
            'numbers': len([w for w in text.split() if w.isdigit()]),
            'special_chars': len([c for c in text if not c.isalnum() and not c.isspace()]),
            'language_confidence': None
        }
        
        try:
            # Attempt to detect language with confidence
            from langdetect import detect_langs
            langs = detect_langs(text)
            if langs:
                analysis['language_confidence'] = {
                    str(lang): round(lang.prob * 100, 2) for lang in langs
                }
        except:
            pass
        
        return analysis

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced button handler with new features."""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'analyze':
            # Get text from message
            text = query.message.text.split('\n\n')[1]
            analysis = await self.analyze_text(text)
            
            analysis_text = (
                "📊 *Text Analysis:*\n\n"
                f"📝 Word Count: {analysis['word_count']}\n"
                f"📏 Character Count: {analysis['character_count']}\n"
                f"📋 Line Count: {analysis['line_count']}\n"
                f"🔢 Numbers Found: {analysis['numbers']}\n"
                f"❗ Special Characters: {analysis['special_chars']}\n"
            )
            
            if analysis['language_confidence']:
                analysis_text += "\n🌍 *Language Confidence:*\n"
                for lang, conf in analysis['language_confidence'].items():
                    analysis_text += f"{LANGUAGES.get(lang, lang)}: {conf}%\n"
            
            await query.message.reply_text(analysis_text, parse_mode='Markdown')
            
        elif query.data == 'enhanced_ocr':
            # Toggle enhanced OCR setting
            user = await users_collection.find_one({'user_id': query.from_user.id})
            current_setting = user.get('settings', {}).get('use_enhanced_ocr', True)
            
            await users_collection.update_one(
                {'user_id': query.from_user.id},
                {'$set': {'settings.use_enhanced_ocr': not current_setting}}
            )
            
            await query.message.reply_text(
                f"🔍 OCR Mode set to: {'Enhanced (EasyOCR)' if not current_setting else 'Standard (Tesseract)'}"
            )
            
        elif query.data == 'download_text':
            text = query.message.text.split('\n\n')[1]
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt') as f:
                f.write(text)
                f.seek(0)
                await query.message.reply_document(
                    document=open(f.name, 'rb'),
                    filename='extracted_text.txt'
                )
        
        # Handle other button actions from previous implementation...

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Log errors and send error message to user."""
        logger.error(f"Update {update} caused error {context.error}")
        error_text = (
            "❌ An error occurred while processing your request.\n\n"
            "Please try again or contact support if the problem persists."
        )
        if update.effective_message:
            await update.effective_message.reply_text(error_text)

    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user settings."""
        user = await users_collection.find_one({'user_id': update.effective_user.id})
        settings = user.get('settings', {})
        
        keyboard = [
            [InlineKeyboardButton(
                f"{'✅' if settings.get('use_enhanced_ocr', True) else '❌'} Enhanced OCR",
                callback_data='toggle_enhanced_ocr'
            )],
            [InlineKeyboardButton(
                f"{'✅' if settings.get('auto_translate', False) else '❌'} Auto Translate",
                callback_data='toggle_auto_translate'
            )],
            [InlineKeyboardButton("🌍 Preferred Language", callback_data='set_language')],
            [InlineKeyboardButton("⬅️ Back", callback_data='main_menu')]
        ]
        
        settings_text = (
            "⚙️ *Current Settings:*\n\n"
            f"🔍 Enhanced OCR: {'Enabled' if settings.get('use_enhanced_ocr', True) else 'Disabled'}\n"
            f"🔄 Auto Translate: {'Enabled' if settings.get('auto_translate', False) else 'Disabled'}\n"
            f"🌍 Preferred Language: {LANGUAGES.get(settings.get('preferred_lang', 'eng'), 'English')}"
        )
        
        await update.message.reply_text(
            settings_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document uploads (PDF and images)."""
        document = update.message.document
        
        if document.mime_type == 'application/pdf':
            await self.process_pdf(update, context)
        elif document.mime_type.startswith('image/'):
            # Convert document to photo format and process
            processing_msg = await update.message.reply_text("🔄 Converting document...")
            
            file = await context.bot.get_file(document.file_id)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(file.file_path) as response:
                    image_data = await response.read()
            
            # Convert to PIL Image for processing
            image = Image.open(io.BytesIO(image_data))
            
            # Save as temporary file
            with tempfile.NamedTemporaryFile(suffix='.jpg') as temp_file:
                image.save(temp_file.name)
                
                # Send as photo and process
                sent_photo = await update.message.reply_photo(
                    photo=open(temp_file.name, 'rb')
                )
                
                # Update context with sent photo
                update.message.photo = [sent_photo.photo[-1]]
                await self.process_image(update, context)
                
            await processing_msg.delete()
        else:
            await update.message.reply_text(
                "⚠️ Please send a PDF document or image file."
            )

    async def translate_text(self, text: str, source_lang: str, target_lang: str):
        """Translate text between languages."""
        try:
            translation = self.translator.translate(
                text,
                src=source_lang,
                dest=target_lang
            )
            return translation.text
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return None

    async def image_enhancement(self, image_data: bytes):
        """Enhance image for better OCR results."""
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Apply enhancements
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Deskewing if needed
        coords = np.column_stack(np.where(thresh > 0))
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            thresh, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        
        return rotated

    async def handle_callback_settings(self, query: CallbackQuery):
        """Handle settings-related callbacks."""
        data = query.data
        user_id = query.from_user.id
        
        if data == 'toggle_enhanced_ocr':
            await users_collection.update_one(
                {'user_id': user_id},
                [{'$set': {
                    'settings.use_enhanced_ocr': {
                        '$not': '$settings.use_enhanced_ocr'
                    }
                }}]
            )
        elif data == 'toggle_auto_translate':
            await users_collection.update_one(
                {'user_id': user_id},
                [{'$set': {
                    'settings.auto_translate': {
                        '$not': '$settings.auto_translate'
                    }
                }}]
            )
        elif data == 'set_language':
            # Create language selection keyboard
            keyboard = []
            row = []
            for i, (lang_code, lang_name) in enumerate(LANGUAGES.items()):
                if i > 0 and i % 2 == 0:
                    keyboard.append(row)
                    row = []
                row.append(InlineKeyboardButton(
                    lang_name,
                    callback_data=f'set_lang_{lang_code}'
                ))
            if row:
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='settings')])
            
            await query.message.edit_text(
                "🌍 Select your preferred language:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # Refresh settings view
        await self.settings(query.message, None)

def main():
    """Start the bot."""
    # Create bot instance
    bot = AdvancedOCRBot()
    
    # Initialize bot with token
    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()

    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("settings", bot.settings))
    application.add_handler(MessageHandler(filters.PHOTO, bot.process_image))
    application.add_handler(MessageHandler(filters.Document.ALL, bot.handle_document))
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    
    # Add error handler
    application.add_error_handler(bot.error_handler)

    # Start the Bot
    print("🤖 Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
