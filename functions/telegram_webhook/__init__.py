import json
import logging
import os
import tempfile
from typing import Optional, Tuple

import azure.functions as func
import requests
from openai import OpenAI
from pydub import AudioSegment

from shared_code.agents.audio_processor import AudioProcessor
from shared_code.agents.responder import Responder
from shared_code.agents.summarizer import Summarizer


def get_file_download_url(file_id: str) -> str:
    """Get the file download URL from Telegram."""
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not found")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile"
    response = requests.post(url, json={"file_id": file_id})
    response.raise_for_status()

    file_path = response.json()["result"]["file_path"]
    return f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"


async def send_telegram_response(
    chat_id: int, text: str, message_id: Optional[int] = None
) -> int:
    """Send or edit response in Telegram. Returns message_id."""
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not found")

    try:
        if message_id:
            # Edit existing message
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
            data = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": "HTML",
            }
        else:
            # Send new message
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}

        response = requests.post(url, json=data)

        # Check if we got a 400 error due to same message content
        if response.status_code == 400 and message_id:
            # If editing failed, try sending a new message
            logging.info("Failed to edit message, sending new one")
            return await send_telegram_response(chat_id, text)

        response.raise_for_status()
        return message_id or response.json()["result"]["message_id"]

    except Exception as e:
        logging.error(f"Error sending telegram message: {str(e)}")
        # If editing fails, send a new message
        if message_id:
            return await send_telegram_response(chat_id, text)
        raise


async def process_voice_message(message_data: dict) -> Optional[str]:
    """Process voice message and return the response text."""
    temp_file = None
    m4a_path = None
    status_message_id = None
    last_status = None  # Track last status message

    logging.info(f"message_data: {message_data}")
    try:
        # Initialize components
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        audio_processor = AudioProcessor(download_path=tempfile.gettempdir())
        summarizer = Summarizer(openai_client)
        responder = Responder(openai_client)

        # Only send new status if it's different from last status
        new_status = "🎧 Processing your voice message..."
        if new_status != last_status:
            status_message_id = await send_telegram_response(
                message_data["chat_id"], new_status
            )
            last_status = new_status

        # Download and save voice file
        file_url = get_file_download_url(message_data["file_id"])
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".oga" if message_data.get("voice") else ".m4a", delete=False
        )

        response = requests.get(file_url, stream=True)
        response.raise_for_status()
        with open(temp_file.name, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        if message_data.get("voice"):
            # Convert to MP3
            m4a_path = os.path.join(
                tempfile.gettempdir(), f"voice_{message_data['message_id']}.m4a"
            )

            await audio_processor.convert_to_m4a(temp_file.name, m4a_path)

        elif message_data.get("audio"):
            m4a_path = temp_file.name

        # Update status
        new_status = "🔍 Transcribing your message..."
        if new_status != last_status:
            status_message_id = await send_telegram_response(
                message_data["chat_id"], new_status, status_message_id
            )
            last_status = new_status

        # Process audio
        transcription_result = await summarizer.transcribe_audio(m4a_path)
        if not transcription_result:
            return await send_telegram_response(
                message_data["chat_id"],
                "❌ Sorry, I couldn't transcribe your message.",
                status_message_id,
            )

        transcription, detected_language = transcription_result
        word_count = len(transcription.split())

        # Map language codes to readable names
        language_names = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "ru": "Russian",
            "de": "German",
        }
        language_display = language_names.get(
            detected_language, detected_language.upper()
        )

        # For short messages, only show transcription
        if word_count < 100:
            await send_telegram_response(
                message_data["chat_id"],
                f"📝 <b>Transcription</b> (in {language_display}):\n\n"
                f"{transcription}\n\n"
                f"ℹ️ Message is too short for summary ({word_count} words)",
                status_message_id,
            )
            return

        # For longer messages, get summary and response
        await send_telegram_response(
            message_data["chat_id"],
            f"💭 Analyzing your message in {language_display}...",
            status_message_id,
        )

        summary = await summarizer.summarize_transcription(
            transcription, detected_language
        )
        if not summary:
            await send_telegram_response(
                message_data["chat_id"],
                "❌ Sorry, I couldn't analyze your message.",
                status_message_id,
            )
            return

        response = await responder.generate_response(summary=summary)
        if not response:
            await send_telegram_response(
                message_data["chat_id"],
                "❌ Sorry, I couldn't generate a response.",
                status_message_id,
            )
            return

        # Send final response
        await send_telegram_response(
            message_data["chat_id"],
            f"📝 <b>Transcription</b> (in {language_display}):\n"
            f"{transcription}\n\n"
            f"📋 <b>Summary</b>:\n"
            f"{summary}\n\n"
            f"🤖 <b>Response</b>:\n"
            f"{response}",
            status_message_id,
        )

    except Exception as e:
        logging.error(f"Error processing voice message: {str(e)}", exc_info=True)
        if status_message_id:
            await send_telegram_response(
                message_data["chat_id"],
                "❌ Sorry, an error occurred while processing your message.",
                status_message_id,
            )

    finally:
        # Cleanup temporary files
        try:
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            if m4a_path and os.path.exists(m4a_path):
                os.unlink(m4a_path)
        except Exception as e:
            logging.error(f"Error cleaning up temporary files: {str(e)}")


async def main(req: func.HttpRequest) -> func.HttpResponse:
    """Main function handler for the Telegram webhook."""
    logging.info("Python HTTP trigger function processed a request.")

    try:
        # Parse Telegram update
        update_data = req.get_json()
        logging.info(f"Received update data: {update_data}")

        # Check if it's a voice message
        if not (message := update_data.get("message")) or not (
            message.get("voice") or message.get("audio")
        ):
            return func.HttpResponse("Not a voice message", status_code=200)

        file_id = (
            message["voice"]["file_id"]
            if message.get("voice")
            else message["audio"]["file_id"]
        )
        duration = (
            message["voice"]["duration"]
            if message.get("voice")
            else message["audio"]["duration"]
        )

        if duration > 600:
            await send_telegram_response(
                message["chat"]["id"], "Audio must be less than 10 minutes long."
            )
            return func.HttpResponse(
                json.dumps({"status": "message processed"}),
                mimetype="application/json",
                status_code=200,
            )
        # Extract message data
        message_data = {
            "chat_id": message["chat"]["id"],
            "message_id": message["message_id"],
            "file_id": file_id,
            "duration": duration,
            "user_id": message["from"]["id"],
            "voice": message.get("voice"),
            "audio": message.get("audio"),
        }

        # Process voice message and get response
        response_text = await process_voice_message(message_data)

        # Send response to Telegram
        if response_text:
            await send_telegram_response(message_data["chat_id"], response_text)

        return func.HttpResponse(
            json.dumps({"status": "message processed"}),
            mimetype="application/json",
            status_code=200,
        )

    except Exception as e:
        logging.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"status": "error", "message": str(e)}),
            mimetype="application/json",
            status_code=500,
        )
