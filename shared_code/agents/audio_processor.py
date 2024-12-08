# src/agents/audio_processor.py
import asyncio
import logging
import os
import subprocess
import tempfile
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from shared_code.agents.responder import Responder
from shared_code.agents.summarizer import Summarizer  # For type hints
from shared_code.services.openai_service import OpenAIService  # For type hints

# We don't need OpenAI imports anymore since we're using the service
from shared_code.services.telegram_service import TelegramService  # For type hints


class AudioProcessor:
    def __init__(self, download_path: str = "downloads"):
        """
        Initialize the audio processor with download path and required services.
        The download_path parameter specifies where audio files will be temporarily stored.
        """
        self.download_path = download_path
        self.temp_path = os.path.join(download_path, "temp")

        # Create necessary directories
        os.makedirs(download_path, exist_ok=True)
        os.makedirs(self.temp_path, exist_ok=True)

        # Language mapping for human-readable output
        self.language_names = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "ru": "Russian",
            "de": "German",
        }

    async def convert_to_m4a(self, input_file: str, output_file: str) -> str:
        """
        Convert any audio file to M4A format using FFmpeg.
        Returns the path to the converted file.
        """
        file_ext = input_file.lower().split(".")[-1]
        command = ["ffmpeg", "-y"]  # Overwrite output file if it exists

        # Configure input options based on file type
        if file_ext in ["oga", "ogg"]:
            command.extend(["-f", "ogg", "-i", input_file])
        else:
            command.extend(["-i", input_file])

        # Set output options for optimal quality and compatibility
        command.extend(
            [
                "-acodec",
                "aac",
                "-b:a",
                "64k",
                "-ar",
                "44100",  # Standard sample rate
                "-ac",
                "2",  # Stereo output
                output_file,
            ]
        )

        # Execute FFmpeg command
        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode()
            logging.error(f"FFmpeg error for {file_ext} file: {error_msg}")
            raise Exception(f"FFmpeg conversion failed: {error_msg}")

        return output_file

    async def process_voice_message(
        self,
        message_data: Dict[str, Any],
        telegram_service: Any,
        openai_service: Any,
        summarizer: Any,
        responder: Any,
    ) -> None:
        """
        Process a voice message through the complete pipeline:
        1. Download and convert audio
        2. Transcribe the content
        3. Generate summary and response
        4. Handle user communication throughout the process
        """
        temp_file = None
        m4a_path = None
        status_message_id = None
        last_status = None

        try:
            # Send initial status update to user
            new_status = "🎧 Processing your voice message..."
            status_message_id = await telegram_service.send_message(
                message_data["chat_id"], new_status
            )
            last_status = new_status

            # Create temporary file with appropriate extension
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".oga" if message_data.get("voice") else ".m4a", delete=False
            )

            # Download the voice file
            file_url = await telegram_service.get_file(message_data["file_id"])
            await telegram_service.download_file(file_url, temp_file.name)

            # Convert audio if needed
            if message_data.get("voice"):
                m4a_path = os.path.join(
                    self.temp_path, f"voice_{message_data['message_id']}.m4a"
                )
                await self.convert_to_m4a(temp_file.name, m4a_path)
            else:
                m4a_path = temp_file.name

            # Update status for transcription
            new_status = "🔍 Transcribing your message..."
            status_message_id = await telegram_service.edit_message(
                message_data["chat_id"], status_message_id, new_status
            )

            # Process audio content
            transcription_result = await openai_service.transcribe_audio(m4a_path)
            if not transcription_result:
                await telegram_service.edit_message(
                    message_data["chat_id"],
                    status_message_id,
                    "❌ Sorry, I couldn't transcribe your message.",
                )
                return

            # Handle transcription results
            transcription, detected_language = transcription_result
            word_count = len(transcription.split())
            language_display = self.language_names.get(
                detected_language, detected_language.upper()
            )

            # For short messages, only provide transcription
            if word_count < 100:
                await telegram_service.edit_message(
                    message_data["chat_id"],
                    status_message_id,
                    f"📝 <b>Transcription</b> (in {language_display}):\n\n"
                    f"{transcription}\n\n",
                )
                return

            # Process longer messages with summary and response
            await telegram_service.edit_message(
                message_data["chat_id"],
                status_message_id,
                f"💭 Analyzing your message in {language_display}...",
            )

            # Generate summary
            summary = await summarizer.summarize_transcription(
                transcription, detected_language
            )
            if not summary:
                await telegram_service.edit_message(
                    message_data["chat_id"],
                    status_message_id,
                    "❌ Sorry, I couldn't analyze your message.",
                )
                return

            # Generate response
            response = await responder.generate_response(summary=summary)
            if not response:
                await telegram_service.edit_message(
                    message_data["chat_id"],
                    status_message_id,
                    "❌ Sorry, I couldn't generate a response.",
                )
                return

            # Send complete analysis to user
            await telegram_service.edit_message(
                message_data["chat_id"],
                status_message_id,
                f"📝 <b>Transcription</b> (in {language_display}):\n"
                f"{transcription}\n\n"
                f"📋 <b>Summary</b>:\n"
                f"{summary}\n\n"
                f"🤖 <b>Response</b>:\n"
                f"{response}",
            )

        except Exception as e:
            logging.error(f"Error processing voice message: {str(e)}", exc_info=True)
            if status_message_id:
                await telegram_service.edit_message(
                    message_data["chat_id"],
                    status_message_id,
                    "❌ Sorry, an error occurred while processing your message.",
                )

        finally:
            # Clean up temporary files
            self._cleanup_temp_files([temp_file, m4a_path])

    def _cleanup_temp_files(self, files: list) -> None:
        """Helper method to safely clean up temporary files."""
        for file in files:
            if file and os.path.exists(file.name if hasattr(file, "name") else file):
                try:
                    os.unlink(file.name if hasattr(file, "name") else file)
                except Exception as e:
                    logging.error(f"Error cleaning up temporary file: {str(e)}")

    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up audio files older than the specified age.
        Returns the number of files removed.
        """
        current_time = datetime.now()
        files_removed = 0

        for directory in [self.download_path, self.temp_path]:
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                file_time = datetime.fromtimestamp(os.path.getctime(filepath))

                if (current_time - file_time).total_seconds() > max_age_hours * 3600:
                    try:
                        os.remove(filepath)
                        files_removed += 1
                        logging.info(f"Removed old audio file: {filepath}")
                    except Exception as e:
                        logging.error(f"Error removing file {filepath}: {str(e)}")

        return files_removed
