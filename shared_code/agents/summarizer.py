# src/agents/summarizer.py
import logging
from typing import Dict, List, Optional, Tuple

from openai import OpenAI


class Summarizer:
    """Agent responsible for transcription and summarization of audio content."""

    def __init__(self, openai_client: OpenAI):
        self.client = openai_client

    async def transcribe_audio(self, audio_path: str) -> Optional[Tuple[str, str]]:
        """
        Transcribe audio file using Whisper.
        Returns a tuple of (transcription, detected_language) or None if failed.
        """
        try:
            with open(audio_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    prompt=None,  # Get additional info including language
                )

            detected_language = transcript.language
            text = transcript.text

            logging.info(f"Successfully transcribed audio: {audio_path}")
            logging.info(f"Detected language: {detected_language}")

            return text, detected_language

        except Exception as e:
            logging.error(f"Error transcribing audio: {str(e)}", exc_info=True)
            return None

    async def summarize_transcription(
        self, transcription: str, language: str
    ) -> Optional[str]:
        """Summarize transcription using GPT."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """
                        You are an expert at summarizing spoken conversations. Your task is to create a clear, concise summary of audio transcripts while:

                        1. Capturing the essential meaning and key points
                        2. Maintaining the original tone and language of the speaker
                        3. Preserving important details, numbers, or specific references
                        4. Keeping the summary to 2-3 sentences maximum
                        5. Using natural, conversational language that reflects spoken communication

                        Remember this is transcribed speech, so focus on the core message rather than exact wording. If the transcript contains filler words or speech artifacts, distill the actual meaning."""
                        f"The detected language of this audio is: {language}",
                    },
                    {"role": "user", "content": transcription},
                ],
            )
            summary = response.choices[0].message.content
            logging.info(f"Successfully generated summary in {language}")
            return summary

        except Exception as e:
            logging.error(f"Error summarizing transcription: {str(e)}", exc_info=True)
            return None
