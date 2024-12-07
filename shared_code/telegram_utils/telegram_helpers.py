import logging

from telegram import Update
from telegram.ext import ContextTypes


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    logging.error(f"Error occurred: {context.error}")
    if update:
        await update.message.reply_text(
            "Sorry, something went wrong processing your message."
        )
