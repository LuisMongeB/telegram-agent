# src/agents/audio_processor.py
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from pydub import AudioSegment
from telegram import Update, Voice
from telegram.ext import ContextTypes


class AudioProcessor:
    def __init__(self, download_path: str = "downloads"):
        """Initialize the audio processor with a download path."""
        self.download_path = download_path
        self.temp_path = os.path.join(download_path, "temp")

        # Create necessary directories
        os.makedirs(download_path, exist_ok=True)
        os.makedirs(self.temp_path, exist_ok=True)

    async def download_voice_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> Optional[str]:
        """
        Download a voice message from Telegram and convert it to MP3 format.
        Returns the path to the converted MP3 file or None if download/conversion fails.
        """
        try:
            if not update.message or not update.message.voice:
                return None

            voice: Voice = update.message.voice
            file = await context.bot.get_file(voice.file_id)

            # Generate filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            msg_id = update.message.message_id

            # Temporary OGG file path
            ogg_filename = f"voice_{timestamp}_{msg_id}.ogg"
            ogg_filepath = os.path.join(self.temp_path, ogg_filename)

            # Final MP3 file path
            mp3_filename = f"voice_{timestamp}_{msg_id}.mp3"
            mp3_filepath = os.path.join(self.download_path, mp3_filename)

            # Download the OGG file
            await file.download_to_drive(ogg_filepath)

            # Convert OGG to MP3
            audio = AudioSegment.from_ogg(ogg_filepath)
            audio.export(mp3_filepath, format="mp3")

            # Clean up the temporary OGG file
            os.remove(ogg_filepath)

            logging.info(f"Successfully converted voice message to MP3: {mp3_filepath}")
            return mp3_filepath

        except Exception as e:
            logging.error(f"Error processing voice message: {str(e)}", exc_info=True)
            # Clean up any temporary files if they exist
            if "ogg_filepath" in locals() and os.path.exists(ogg_filepath):
                os.remove(ogg_filepath)
            return None

    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """Clean up old audio files. Returns number of files removed."""
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
