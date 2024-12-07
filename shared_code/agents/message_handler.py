# src/agents/message_handler.py
import logging
from typing import Optional, Tuple

from telegram import Update
from telegram.ext import ContextTypes

from .audio_buffer import AudioBuffer
from .audio_processor import AudioProcessor
from .responder import Responder
from .summarizer import Summarizer


class AudioMessageHandler:
    def __init__(
        self,
        audio_processor: AudioProcessor,
        audio_buffer: AudioBuffer,
        summarizer: Summarizer,
        responder: Responder,
    ):
        self.audio_processor = audio_processor
        self.audio_buffer = audio_buffer
        self.summarizer = summarizer
        self.responder = responder

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming voice and audio messages."""
        try:
            if not update.message or (
                not update.message.voice and not update.message.audio
            ):
                return

            chat_id = update.message.chat_id
            message_id = update.message.message_id

            # Send initial processing message
            processing_msg = await update.message.reply_text(
                "🎧 Processing your audio message..."
            )

            # Download and convert audio
            audio_path = await self.audio_processor.download_voice_message(
                update, context
            )
            if not audio_path:
                await processing_msg.edit_text(
                    "❌ Sorry, I couldn't process your audio message. Please try again."
                )
                return

            # Get duration from either voice or audio message
            duration = None
            if update.message.voice:
                duration = update.message.voice.duration
            elif update.message.audio:
                duration = update.message.audio.duration

            # Store in buffer
            buffer_key = self.audio_buffer.add_entry(
                message_id=message_id,
                chat_id=chat_id,
                user_id=update.message.from_user.id,
                filepath=audio_path,
                duration=duration,
            )

            # Update processing status
            await processing_msg.edit_text("🔍 Transcribing your message...")

            # Transcribe audio and detect language
            transcription_result = await self.summarizer.transcribe_audio(audio_path)
            if not transcription_result:
                await processing_msg.edit_text(
                    "❌ Sorry, I couldn't transcribe your message. Please try again."
                )
                return

            transcription, detected_language = transcription_result

            # Update processing status with detected language
            language_emoji = "🌐" if detected_language != "en" else "🇬🇧"
            await processing_msg.edit_text(
                f"{language_emoji} Analyzing your message in {detected_language}..."
            )

            # Summarize transcription
            summary = await self.summarizer.summarize_transcription(
                transcription, detected_language
            )
            if not summary:
                await processing_msg.edit_text(
                    "❌ Sorry, I couldn't analyze your message. Please try again."
                )
                return

            # Get chat history from buffer
            chat_history = self.audio_buffer.get_chat_history(chat_id)

            # Generate response
            response = await self.responder.generate_response(
                summary=summary,
                context=[
                    {"role": "user", "content": entry.transcription}
                    for entry in chat_history
                    if entry.transcription
                ],
            )

            if not response:
                await processing_msg.edit_text(
                    "❌ Sorry, I couldn't generate a response. Please try again."
                )
                return

            # Update the transcription in buffer
            self.audio_buffer.update_transcription(buffer_key, transcription)

            # Send final response
            await processing_msg.edit_text(response)

        except Exception as e:
            logging.error(f"Error processing audio message: {str(e)}", exc_info=True)
            if "processing_msg" in locals():
                await processing_msg.edit_text(
                    "❌ Sorry, something went wrong. Please try again later."
                )
