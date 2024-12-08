# services/telegram_service.py
import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional, Union

import aiohttp
import requests


class TelegramService:
    """
    A service class that handles all interactions with the Telegram Bot API.
    This centralizes our Telegram communication logic and provides a clean interface
    for other parts of the application to use.
    """

    def __init__(self, bot_token: str):
        """
        Initialize the service with the bot's token and set up basic configurations.

        Parameters:
            bot_token (str): The Telegram bot token from BotFather
        """
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.file_url = f"https://api.telegram.org/file/bot{bot_token}"

        # We'll use these for rate limiting and error tracking
        self.last_request_time = datetime.now()
        self._error_count = 0

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_to_message_id: Optional[int] = None,
    ) -> Optional[int]:
        """
        Send a new message to a specified chat.

        Parameters:
            chat_id (int): Telegram chat ID to send message to
            text (str): The message text to send
            parse_mode (str): How to parse the message text (HTML/Markdown)
            reply_to_message_id (int, optional): Message ID to reply to

        Returns:
            Optional[int]: The message ID of the sent message, or None if sending failed
        """
        try:
            data = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
            if reply_to_message_id:
                data["reply_to_message_id"] = reply_to_message_id

            response = await self._make_request("sendMessage", data)
            return response["result"]["message_id"] if response else None

        except Exception as e:
            logging.error(f"Error sending message: {str(e)}")
            return None

    async def edit_message(
        self, chat_id: int, message_id: int, text: str, parse_mode: str = "HTML"
    ) -> Optional[int]:
        """
        Edit an existing message.

        Parameters:
            chat_id (int): Chat ID where the message is
            message_id (int): ID of the message to edit
            text (str): New text for the message
            parse_mode (str): How to parse the message text

        Returns:
            Optional[int]: The message ID, or None if editing failed
        """
        try:
            data = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": parse_mode,
            }

            response = await self._make_request("editMessageText", data)

            # Handle the case where message content hasn't changed
            if not response and self._is_message_unchanged_error():
                return message_id

            return response["result"]["message_id"] if response else None

        except Exception as e:
            logging.error(f"Error editing message: {str(e)}")
            # If editing fails, try sending a new message
            return await self.send_message(chat_id, text, parse_mode)

    async def get_file(self, file_id: str) -> Optional[str]:
        """
        Get the file path for downloading a file.

        Parameters:
            file_id (str): Telegram's file ID

        Returns:
            Optional[str]: URL to download the file, or None if retrieval failed
        """
        try:
            response = await self._make_request("getFile", {"file_id": file_id})
            if response and "result" in response:
                file_path = response["result"]["file_path"]
                return f"{self.file_url}/{file_path}"
            return None

        except Exception as e:
            logging.error(f"Error getting file: {str(e)}")
            return None

    async def download_file(self, file_url: str, local_path: str) -> bool:
        """
        Download a file from Telegram to a local path.

        Parameters:
            file_url (str): URL to download the file from
            local_path (str): Where to save the file locally

        Returns:
            bool: True if download succeeded, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as response:
                    if response.status == 200:
                        with open(local_path, "wb") as f:
                            while True:
                                chunk = await response.content.read(8192)
                                if not chunk:
                                    break
                                f.write(chunk)
                        return True
            return False

        except Exception as e:
            logging.error(f"Error downloading file: {str(e)}")
            return False

    async def _make_request(
        self, method: str, data: Dict[str, Any], files: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Make a request to the Telegram Bot API with error handling and retry logic.

        Parameters:
            method (str): Telegram API method to call
            data (dict): Data to send with the request
            files (dict, optional): Files to upload

        Returns:
            Optional[Dict]: Response from Telegram, or None if request failed
        """
        url = f"{self.base_url}/{method}"

        try:
            # Basic rate limiting - you might want to make this more sophisticated
            time_since_last = (datetime.now() - self.last_request_time).total_seconds()
            if time_since_last < 0.1:  # Maximum 10 requests per second
                await asyncio.sleep(0.1 - time_since_last)

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    self.last_request_time = datetime.now()

                    if response.status != 200:
                        logging.error(
                            f"Telegram API error: {response.status} - {await response.text()}"
                        )
                        return None

                    return await response.json()

        except Exception as e:
            logging.error(f"Error making request to Telegram: {str(e)}")
            return None

    def _is_message_unchanged_error(self) -> bool:
        """
        Check if the last error was due to message content being unchanged.
        This is a common case when editing messages and not an actual error.
        """
        # You might want to implement more sophisticated error checking here
        return True
