# src/commands/help_command.py

import logging
from dataclasses import dataclass
from typing import Dict, Optional

from shared_code.services.telegram_service import TelegramService


@dataclass
class HelpCommandConfig:
    """
    This configuration class centralizes our help messages. By using a dataclass,
    we can easily modify the help text without changing the command logic.
    We also make it easier to add new sections or modify existing ones.
    """

    general_help: str = (
        "🤖 <b>Nebula Bot Help Guide</b>\n\n"
        "I'm your voice processing assistant that helps with messages "
        "from Telegram and WhatsApp chats.\n\n"
        "🎯 <b>Main Features</b>:\n"
        "• Voice message transcription\n"
        "• Automatic language detection\n"
        "• Smart summarization for longer messages\n"
        "• Contextual responses\n\n"
        "📱 <b>Supported Messages</b>:\n"
        "• Voice messages (up to 10 minutes)\n"
        "• Audio files (m4a and ogg format)\n\n"
        "💡 <b>Tips</b>:\n"
        "• Forward messages from WhatsApp or Telegram!\n"
        "• Messages under 100 words get transcription only\n"
        "• Longer messages receive summaries and responses\n"
        "• All audio is processed securely and deleted after analysis"
    )


class HelpCommand:
    """
    This class handles the /help command for our bot. It's responsible for
    providing users with information about bot features and available commands.
    """

    def __init__(self, telegram_service: TelegramService):
        """
        Initialize with the services we need. We use dependency injection here,
        passing in the telegram_service rather than creating it inside the class.
        """
        self.telegram_service = telegram_service
        self.config = HelpCommandConfig()

    async def execute(self, chat_id: int, **kwargs) -> bool:
        """
        Handle the help command execution. This method follows the same pattern
        as your start command, ensuring consistency across command implementations.

        Parameters:
            chat_id: The Telegram chat ID to send the help message to
            **kwargs: Additional arguments (for future extensibility)

        Returns:
            bool: True if help message was sent successfully, False otherwise
        """
        try:
            # Build and send the help message
            help_message = await self._build_help_message()
            await self.telegram_service.send_message(chat_id, help_message)
            logging.info(f"Sent help message to chat_id: {chat_id}")
            return True

        except Exception as e:
            logging.error(f"Error sending help message to chat_id {chat_id}: {str(e)}")
            return False

    async def _build_help_message(self) -> str:
        """
        Construct the complete help message. We keep this in a separate method
        to make it easier to modify the message structure or add new sections.
        """
        return f"{self.config.general_help}\n\n" f"Type /start to begin using the bot!"
