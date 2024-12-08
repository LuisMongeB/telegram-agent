# services/openai_service.py
import asyncio
import logging
from typing import Any, Dict, Optional, Tuple

import backoff
from openai import OpenAI, OpenAIError


class OpenAIService:
    """
    A service class that manages interactions with the OpenAI API.
    This service handles the complexity of making API calls, provides error handling,
    and implements retry logic for improved reliability.
    """

    def __init__(self, api_key: str):
        """
        Initialize the OpenAI service with required configuration.

        The service creates a synchronous OpenAI client but provides an async interface
        to maintain consistency with our application's architecture. This allows us to
        handle multiple requests concurrently while working with OpenAI's sync client.

        Parameters:
            api_key (str): OpenAI API key for authentication
        """
        if not api_key:
            raise ValueError("OpenAI API key cannot be empty")

        self._client = OpenAI(api_key=api_key)
        self.default_model = "gpt-4-turbo-preview"
        self.max_retries = 3

    @property
    def client(self) -> OpenAI:
        """
        Provide controlled access to the OpenAI client instance.
        This property allows us to add monitoring or logging in the future.
        """
        return self._client

    @backoff.on_exception(
        backoff.expo,
        OpenAIError,
        max_tries=3,
        giveup=lambda e: isinstance(e, KeyError),
    )
    async def transcribe_audio(
        self, audio_path: str, prompt: Optional[str] = None
    ) -> Optional[Tuple[str, str]]:
        """
        Transcribe an audio file using OpenAI's Whisper model.

        This method wraps the synchronous OpenAI client call in an async interface.
        We use asyncio.to_thread to run the API call in a separate thread, preventing
        it from blocking the event loop while maintaining our async architecture.

        Parameters:
            audio_path (str): Path to the audio file
            prompt (str, optional): Optional transcription prompt

        Returns:
            Optional[Tuple[str, str]]: (transcription_text, detected_language) or None
        """
        try:
            # Define our synchronous transcription operation
            def _transcribe():
                with open(audio_path, "rb") as audio_file:
                    return self._client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="verbose_json",
                        prompt=prompt,
                    )

            # Run the synchronous operation in a thread pool
            transcript = await asyncio.to_thread(_transcribe)

            text = transcript.text
            detected_language = transcript.language

            logging.info(f"Successfully transcribed audio: {audio_path}")
            logging.info(f"Detected language: {detected_language}")

            return text, detected_language

        except FileNotFoundError:
            logging.error(f"Audio file not found: {audio_path}")
            return None
        except OpenAIError as e:
            logging.error(f"OpenAI API error: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}", exc_info=True)
            return None

    @backoff.on_exception(backoff.expo, OpenAIError, max_tries=3)
    async def generate_chat_completion(
        self,
        messages: list,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        """
        Generate a chat completion using OpenAI's API.

        Like the transcription method, this wraps the synchronous client call
        in an async interface using asyncio.to_thread to prevent blocking.

        Parameters:
            messages (list): Conversation messages
            model (str, optional): Model to use
            temperature (float): Response randomness
            max_tokens (int, optional): Max response length

        Returns:
            Optional[str]: Generated response or None if failed
        """
        try:
            # Define our synchronous chat completion operation
            def _generate_completion():
                return self._client.chat.completions.create(
                    model=model or self.default_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

            # Run the synchronous operation in a thread pool
            response = await asyncio.to_thread(_generate_completion)
            return response.choices[0].message.content

        except OpenAIError as e:
            logging.error(f"OpenAI API error: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            return None

    async def check_api_status(self) -> bool:
        """
        Verify API accessibility and key validity.

        This method attempts a minimal API call to check if we can
        successfully communicate with OpenAI's services.

        Returns:
            bool: True if API is accessible, False otherwise
        """
        try:

            def _check_status():
                return self._client.chat.completions.create(
                    model=self.default_model,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=5,
                )

            await asyncio.to_thread(_check_status)
            return True

        except OpenAIError:
            return False

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass
