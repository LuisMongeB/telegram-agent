import json
import logging
import os
from typing import Optional

import azure.functions as func

from shared_code.agents.audio_processor import AudioProcessor
from shared_code.agents.responder import Responder
from shared_code.agents.summarizer import Summarizer
from shared_code.commands.command_registry import CommandRegistry
from shared_code.commands.help_command import HelpCommand
from shared_code.commands.start_command import StartCommand
from shared_code.services.openai_service import OpenAIService

# from shared_code.services.storage_service import StorageService
from shared_code.services.telegram_service import TelegramService

# Initialize our services. We keep these at module level because Azure Functions
# can reuse the same instance across multiple invocations, improving performance.
telegram_service = TelegramService(os.getenv("TELEGRAM_BOT_TOKEN"))
openai_service = OpenAIService(os.getenv("OPENAI_API_KEY"))
# storage_service = StorageService(os.getenv("STORAGE_CONNECTION_STRING"))

# Initialize our commands and registry
command_registry = CommandRegistry()
start_command = StartCommand(telegram_service)
help_command = HelpCommand(telegram_service)

# Initialize our processing components with the appropriate services
audio_processor = AudioProcessor()
summarizer = Summarizer(openai_service)  # Updated to use service instead of client
responder = Responder(openai_service)  # Updated to use service instead of client

# Register commands with the registry
command_registry.register(
    "start",
    start_command.execute,  # Now using the dedicated command class
    "Start the bot",
    "Initialize the bot and see welcome message",
)
command_registry.register(
    "help",
    help_command.execute,  # Now using the dedicated command class
    "Help",
    "Gets tips on how to use Nebula",
)


async def handle_media_message(message: dict) -> None:
    """
    Processes incoming voice or audio messages through our processing pipeline.
    This function extracts necessary information and coordinates between different
    components to process the audio content.
    """
    message_data = {
        "chat_id": message["chat"]["id"],
        "message_id": message["message_id"],
        "file_id": (message.get("voice", {}) or message.get("audio", {})).get(
            "file_id"
        ),
        "duration": (message.get("voice", {}) or message.get("audio", {})).get(
            "duration"
        ),
        "user_id": message["from"]["id"],
        "voice": message.get("voice"),
        "audio": message.get("audio"),
    }

    # Pass the message through our processing pipeline
    await audio_processor.process_voice_message(
        message_data, telegram_service, openai_service, summarizer, responder
    )


async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main webhook handler for Telegram updates. This function serves as the entry point
    for all Telegram interactions, routing different types of messages to their
    appropriate handlers.
    """
    logging.info("Processing new Telegram webhook request")

    try:
        update_data = req.get_json()
        logging.info(f"Received update data: {update_data}")

        if not (message := update_data.get("message")):
            logging.info("Update contained no message")
            return func.HttpResponse("Not a message", status_code=200)

        # Handle command messages (e.g., /start)
        if "entities" in message and message["entities"][0]["type"] == "bot_command":
            command_text = message["text"]
            chat_id = message["chat"]["id"]
            user_name = message["from"].get(
                "first_name"
            )  # Get user's name if available

            logging.info(f"Processing command: {command_text} from user: {user_name}")

            # Use the command registry to handle the command
            if command_text == "/start" and user_name:
                # Use personalized start command if we have the user's name
                await start_command.execute_with_name(chat_id, user_name)
            else:
                await command_registry.handle_command(command_text, chat_id)

            return func.HttpResponse(
                json.dumps({"status": "command processed"}),
                mimetype="application/json",
                status_code=200,
            )

        # Handle voice and audio messages
        if message.get("voice") or message.get("audio"):
            duration = message.get("voice", {}).get("duration") or message.get(
                "audio", {}
            ).get("duration")

            # Check message duration limit
            if duration > 600:  # 10 minutes in seconds
                await telegram_service.send_message(
                    message["chat"]["id"], "Audio must be less than 10 minutes long."
                )
                return func.HttpResponse(
                    json.dumps({"status": "message processed"}),
                    mimetype="application/json",
                    status_code=200,
                )

            await handle_media_message(message)
            return func.HttpResponse(
                json.dumps({"status": "message processed"}),
                mimetype="application/json",
                status_code=200,
            )

        # Handle unsupported message types
        logging.info("Received unsupported message type")
        return func.HttpResponse("Message type not supported", status_code=200)

    except Exception as e:
        logging.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"status": "error", "message": str(e)}),
            mimetype="application/json",
            status_code=500,
        )
