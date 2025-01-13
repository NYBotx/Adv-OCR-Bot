import os
import logging
from telegram.constants import ChatAction
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from pymongo import MongoClient
from bson import ObjectId  # Import ObjectId
import pytesseract
from PIL import Image
from io import BytesIO
import cv2
import numpy as np
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')
OWNER_USERNAME = "@NY_Botx"
PORT = 8080

client = MongoClient(MONGO_URI)
db = client['ocr_bot']
images_collection = db['images']

LOADING_ANIMATIONS = {
    'spinner': ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
    'pulse': ['□', '■'],
    'dots': ['●∙∙', '∙●∙', '∙∙●', '∙●∙'],
    'wave': ['⎯', '⎰', '⎱', '⎰']
}

class AnimatedOCRBot:
    def __init__(self):
        self.languages = {
            'eng': 'English 🇬🇧', 'hin': 'Hindi 🇮🇳',
            'fra': 'French 🇫🇷', 'spa': 'Spanish 🇪🇸',
            'deu': 'German 🇩🇪', 'ita': 'Italian 🇮🇹',
            'por': 'Portuguese 🇵🇹', 'rus': 'Russian 🇷🇺',
            'chi_sim': 'Chinese 🇨🇳', 'jpn': 'Japanese 🇯🇵'
        }
        self.settings = {
            'theme': ['Default 🎨', 'Dark 🌙', 'Light ☀️', 'Colorful 🌈'],
            'format': ['Modern ✨', 'Classic 📜', 'Minimal ⚡️', 'Fancy 🎭'],
            'animation': ['Smooth 🌊', 'Quick ⚡️', 'Elegant 🎯', 'Fun 🎪']
        }

    def main_menu_keyboard(self):
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📷 Extract Text", callback_data='ocr'),
                InlineKeyboardButton("⚙️ Settings", callback_data='settings')
            ],
            [
                InlineKeyboardButton("ℹ️ Help", callback_data='help'),
                InlineKeyboardButton("👤 About", callback_data='about')
            ],
            [
                InlineKeyboardButton("👨‍💻 Developer", url=f"https://t.me/{OWNER_USERNAME[1:]}")
            ]
        ])

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        intro_text = (
            "*Welcome to Advanced OCR Bot!*"
            "\n\n"
            "Transform your images into text with style! ✨\n\n"
            "🌟 *Features:*\n"
            "• Multi-language Support (10 languages)\n"
            "• Beautiful Animations\n"
            "• Custom Themes\n"
            "• Smart Format Detection\n"
            f"\n_Powered by {OWNER_USERNAME}_"
        )

        await update.message.reply_text(
            intro_text,
            reply_markup=self.main_menu_keyboard(),
            parse_mode='Markdown'
        )

    async def process_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            message = await update.message.reply_text("🔄 Starting OCR process...")

            photo = update.message.photo[-1]
            image_file = await context.bot.get_file(photo.file_id)
            image_bytes = await image_file.download_as_bytearray()

            image_id = images_collection.insert_one({"image": image_bytes}).inserted_id

            image = Image.open(BytesIO(image_bytes))
            img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            img_cv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            img_cv = cv2.threshold(img_cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

            text = pytesseract.image_to_string(img_cv)

            if not text.strip():
                await message.edit_text("⚠️ No text detected! Please try with a clearer image.")
                return

            result_text = (
                "📝 *Extracted Text:*\n"
                "━━━━━━━━━━━━━━━\n\n"
                f"❝ {text.strip()} ❞\n\n"
                "━━━━━━━━━━━━━━━\n"
                f"🔍 Processed by {OWNER_USERNAME}"
            )

            keyboard = [
                [
                    InlineKeyboardButton("🖼 View Image", callback_data=f'view_image:{image_id}'),
                    InlineKeyboardButton("🗑 Delete Image", callback_data=f'delete_image:{image_id}')
                ],
                [
                    InlineKeyboardButton("🏠 Main Menu", callback_data='menu')
                ]
            ]

            await message.edit_text(
                result_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"OCR Error: {str(e)}")
            await update.message.reply_text(
                "😔 An error occurred. Please try again with a different image."
            )

    # Image action handlers
    async def handle_image_actions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        action, image_id = query.data.split(":")
        image_doc = images_collection.find_one({"_id": ObjectId(image_id)})

        if not image_doc:
            await query.edit_message_text("⚠️ Image not found or already deleted.")
            return

        if action == 'view_image':
            image_bytes = image_doc['image']
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=BytesIO(image_bytes)
            )

        elif action == 'delete_image':
            images_collection.delete_one({"_id": ObjectId(image_id)})
            await query.edit_message_text("🗑 Image deleted successfully.")

    # Settings handlers
    async def settings_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        keyboard = [
            [
                InlineKeyboardButton("🎨 Themes", callback_data='set_theme'),
                InlineKeyboardButton("📝 Format", callback_data='set_format')
            ],
            [
                InlineKeyboardButton("🌊 Animations", callback_data='set_animation'),
                InlineKeyboardButton("🌍 Language", callback_data='set_language')
            ],
            [
                InlineKeyboardButton("⚡️ Performance", callback_data='set_performance'),
                InlineKeyboardButton("🔔 Notifications", callback_data='set_notifications')
            ],
            [
                InlineKeyboardButton("🏠 Main Menu", callback_data='menu')
            ]
        ]

        settings_text = (
            "*⚙️ Bot Settings*\n\n"
            "Customize your experience:\n\n"
            "🎨 *Themes:* Change bot appearance\n"
            "📝 *Format:* Adjust text styling\n"
            "🌊 *Animations:* Modify transitions\n"
            "🌍 *Language:* Set OCR language\n"
            "⚡️ *Performance:* Speed vs accuracy\n"
            "🔔 *Notifications:* Alert preferences"
        )

        await query.edit_message_text(
            settings_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    # Help and About handlers
    async def help_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("ℹ️ *Help*: This bot extracts text from images in various languages with customizable settings.")

    async def about_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(f"👤 *About*: This bot is developed by {OWNER_USERNAME}.")

    def run(self):
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        # Add handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(MessageHandler(filters.PHOTO, self.process_image))
        application.add_handler(CallbackQueryHandler(self.settings_handler, pattern='^settings$'))
        application.add_handler(CallbackQueryHandler(self.about_handler, pattern='^about$'))
        application.add_handler(CallbackQueryHandler(self.help_handler, pattern='^help$'))
        application.add_handler(CallbackQueryHandler(self.handle_image_actions, pattern='^view_image:'))
        application.add_handler(CallbackQueryHandler(self.handle_image_actions, pattern='^delete_image:'))

        # Start bot
        application.run_polling()

if __name__ == '__main__':
    bot = AnimatedOCRBot()
    bot.run()
