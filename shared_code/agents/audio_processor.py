# src/agents/audio_processor.py
import asyncio
import logging
import os
import subprocess
from datetime import datetime
from typing import Any, Dict, Optional

from pydub import AudioSegment
from telegram import Audio, Update, Voice
from telegram.ext import ContextTypes


class AudioProcessor:
    def __init__(self, download_path: str = "downloads"):
        """Initialize the audio processor with a download path."""
        self.download_path = download_path
        self.temp_path = os.path.join(download_path, "temp")

        # Create necessary directories
        os.makedirs(download_path, exist_ok=True)
        os.makedirs(self.temp_path, exist_ok=True)

    async def convert_to_m4a(self, input_file, output_file):
        # Check file extension
        file_ext = input_file.lower().split(".")[-1]

        command = ["ffmpeg", "-y"]  # Overwrite output file if it exists

        # Add input options based on file type
        if file_ext == "oga" or file_ext == "ogg":
            command.extend(
                ["-f", "ogg", "-i", input_file]  # Force OGG format for input
            )
        else:
            command.extend(["-i", input_file])

        # Add output options
        command.extend(
            [
                "-acodec",
                "aac",
                "-b:a",
                "64k",
                "-ar",
                "44100",  # Set sample rate
                "-ac",
                "2",  # Set to stereo
                output_file,
            ]
        )

        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode()
            logging.error(f"FFmpeg error for {file_ext} file: {error_msg}")
            raise Exception(f"FFmpeg conversion failed: {error_msg}")

        return output_file

    async def download_voice_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> Optional[str]:
        """
        Download a voice message from Telegram and convert it to MP3 format.
        Returns the path to the converted MP3 file or None if download/conversion fails.
        """
        logging.info(f"\nUPDATE:\n\n{update.message}")
        try:
            if not update.message:
                return None
            if update.message.voice:

                voice: Voice = update.message.voice
                file = await context.bot.get_file(voice.file_id)

                # Generate filenames
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                msg_id = update.message.message_id

                # Temporary OGG file path
                ogg_filename = f"voice_{timestamp}_{msg_id}.ogg"
                ogg_filepath = os.path.join(self.temp_path, ogg_filename)

                # Final M4A file path

                m4a_filename = f"voice_{timestamp}_{msg_id}.m4a"
                m4a_filepath = os.path.join(self.download_path, m4a_filename)
                # Download the OGG file
                await file.download_to_drive(ogg_filepath)

                # Convert OGG to M4A
                audio = AudioSegment.from_ogg(ogg_filepath)

                await self.convert_to_m4a(ogg_filepath, m4a_filepath)

                logging.info(
                    f"Successfully converted voice message to MP3: {m4a_filepath}"
                )
                # Clean up the temporary OGG file
                os.remove(ogg_filepath)
                return m4a_filepath

            elif update.message.audio:
                # Process M4A
                audio: Audio = update.message.audio
                file = await context.bot.get_file(audio.file_id)

                # Generate filenames
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                msg_id = update.message.message_id

                # M4A path
                m4a_filename = f"voice_{timestamp}_{msg_id}.m4a"
                m4a_filepath = os.path.join(self.download_path, m4a_filename)

                # Just download the file - no conversion needed
                await file.download_to_drive(m4a_filepath)
                logging.info(f"Successfully downloaded audio message: {m4a_filepath}")

                return m4a_filepath

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
