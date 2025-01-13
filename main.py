# main.py
import os
import logging
from telegram.constants import ChatAction  # Updated import for versions >=20.0
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
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
OWNER_USERNAME = "@NY_Botx"

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

    async def animate_message(self, message, frames, duration=2):
        """Create loading animation"""
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < duration:
            for frame in frames:
                try:
                    await message.edit_text(f"{message.text.split()[0]} {frame}")
                    await asyncio.sleep(0.2)
                except Exception:
                    pass

    async def typing_animation(self, message, text):
        """Create typing effect"""
        current = ""
        for char in text:
            current += char
            try:
                await message.edit_text(current + "▋")
                await asyncio.sleep(0.05)
            except Exception:
                pass
        return message

    def main_menu_keyboard(self):
        """Create main menu keyboard"""
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
        """Handle /start command"""
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        message = await update.message.reply_text("🚀 Initializing...")

        intro_text = (
            "*Welcome to Advanced OCR Bot!*\n\n"
            "Transform your images into text with style! ✨\n\n"
            "🌟 *Features:*\n"
            "• Multi-language Support (10 languages)\n"
            "• Beautiful Animations\n"
            "• Custom Themes\n"
            "• Smart Format Detection\n"
            f"\n_Powered by {OWNER_USERNAME}_"
        )

        await self.typing_animation(message, intro_text)
        await message.edit_text(
            intro_text,
            reply_markup=self.main_menu_keyboard(),
            parse_mode='Markdown'
        )

    async def settings_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle settings menu"""
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

    async def about_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle about section"""
        query = update.callback_query
        await query.answer()

        about_text = (
            "*About OCR Bot*\n\n"
            "Version: 2.0 ✨\n"
            "Created: January 2024\n\n"
            "🚀 *Features:*\n"
            "• Advanced Text Extraction\n"
            "• Multi-language Support\n"
            "• Beautiful Animations\n"
            "• Custom Themes\n\n"
            f"Developer: {OWNER_USERNAME}\n"
            "Framework: Python-Telegram-Bot\n\n"
            "Made with ❤️ for the community"
        )

        keyboard = [
            [
                InlineKeyboardButton("⭐️ Rate Bot", callback_data='rate'),
                InlineKeyboardButton("💬 Feedback", callback_data='feedback')
            ],
            [
                InlineKeyboardButton("🏠 Main Menu", callback_data='menu')
            ]
        ]

        await query.edit_message_text(
            about_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def help_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle help section"""
        query = update.callback_query
        await query.answer()

        help_text = (
            "*📖 How to Use OCR Bot*\n\n"
            "1️⃣ Send any image with text\n"
            "2️⃣ Wait for processing animation\n"
            "3️⃣ Get beautifully formatted result\n\n"
            "📋 *Commands:*\n"
            "/start - Start the bot\n"
            "/settings - Configure bot\n"
            "/help - Show this help\n\n"
            "💡 *Tips:*\n"
            "• Use clear images\n"
            "• Proper lighting helps\n"
            "• Supported formats: JPG, PNG\n\n"
            "Need help? Contact developer"
        )

        keyboard = [
            [
                InlineKeyboardButton("📝 Examples", callback_data='examples'),
                InlineKeyboardButton("❓ FAQ", callback_data='faq')
            ],
            [
                InlineKeyboardButton("🏠 Main Menu", callback_data='menu')
            ]
        ]

        await query.edit_message_text(
            help_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def process_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process image with animations"""
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        message = await update.message.reply_text("🔄 Starting OCR process...")

        # Animated processing stages
        stages = [
            ("📸 Capturing image", LOADING_ANIMATIONS['spinner']),
            ("✨ Enhancing quality", LOADING_ANIMATIONS['pulse']),
            ("🔍 Extracting text", LOADING_ANIMATIONS['dots']),
            ("📝 Formatting result", LOADING_ANIMATIONS['wave'])
        ]

        try:
            # Process image
            photo = update.message.photo[-1]
            image_file = await context.bot.get_file(photo.file_id)
            image_bytes = await image_file.download_as_bytearray()

            # Show processing animations
            for stage_text, animation in stages:
                await message.edit_text(stage_text)
                await self.animate_message(message, animation)

                if "Capturing" in stage_text:
                    image = Image.open(BytesIO(image_bytes))
                elif "Enhancing" in stage_text:
                    img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                    img_cv = cv2.threshold(img_cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
                elif "Extracting" in stage_text:
                    text = pytesseract.image_to_string(img_cv)

            if not text.strip():
                await message.edit_text("⚠️ No text detected! Please try with a clearer image.")
                return

            # Format result
            result_text = (
                "📝 *Extracted Text:*\n"
                "━━━━━━━━━━━━━━━\n\n"
                f"❝ {text.strip()} ❞\n\n"
                "━━━━━━━━━━━━━━━\n"
                f"🔍 Processed by {OWNER_USERNAME}"
            )

            keyboard = [
                [
                    InlineKeyboardButton("📋 Copy", callback_data='copy'),
                    InlineKeyboardButton("🔄 New Scan", callback_data='ocr')
                ],
                [
                    InlineKeyboardButton("⚙️ Settings", callback_data='settings'),
                    InlineKeyboardButton("📤 Share", switch_inline_query=f"OCR Result")
                ],
                [
                    InlineKeyboardButton("🏠 Main Menu", callback_data='menu')
                ]
            ]

            await self.typing_animation(message, result_text)
            await message.edit_text(
                result_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"OCR Error: {str(e)}")
            await message.edit_text(
                "😔 An error occurred. Please try again with a different image."
            )

    def run(self):
        """Run the bot"""
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(MessageHandler(filters.PHOTO, self.process_image))
        application.add_handler(CallbackQueryHandler(self.settings_handler, pattern='^settings$'))
        application.add_handler(CallbackQueryHandler(self.about_handler, pattern='^about$'))
        application.add_handler(CallbackQueryHandler(self.help_handler, pattern='^help$'))
        
        # Start bot
        application.run_polling()

if __name__ == '__main__':
    bot = AnimatedOCRBot()
    bot.run()
