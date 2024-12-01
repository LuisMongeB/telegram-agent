# src/main.py
import logging
import os

from dotenv import load_dotenv
from openai import OpenAI
from telegram.ext import Application, MessageHandler, filters

from agents.audio_buffer import AudioBuffer
from agents.audio_processor import AudioProcessor
from agents.message_handler import VoiceMessageHandler  # Updated import
from agents.responder import Responder
from agents.summarizer import Summarizer

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def main():
    """Start the bot."""
    try:
        # Initialize OpenAI client
        openai_client = OpenAI(
            api_key=OPENAI_API_KEY,
        )

        # Initialize components
        audio_processor = AudioProcessor()
        audio_buffer = AudioBuffer()
        summarizer = Summarizer(openai_client)
        responder = Responder(openai_client)

        # Initialize voice message handler with all components
        voice_handler = VoiceMessageHandler(  # Updated class name
            audio_processor=audio_processor,
            audio_buffer=audio_buffer,
            summarizer=summarizer,
            responder=responder,
        )

        # Create application instance
        application = Application.builder().token(TOKEN).build()

        # Add voice message handler
        application.add_handler(
            MessageHandler(
                filters.VOICE & ~filters.COMMAND, voice_handler.handle_voice_message
            )
        )

        # Start polling
        logging.info("Bot started")
        application.run_polling()

    except Exception as e:
        logging.error(f"Error starting bot: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()
