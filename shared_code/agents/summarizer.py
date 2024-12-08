import logging
from typing import Optional

from shared_code.services.openai_service import OpenAIService


class Summarizer:
    """
    Agent responsible for summarization of transcribed content. This class focuses solely
    on converting longer transcribed text into concise, meaningful summaries while preserving
    the key information and context from the original content.
    """

    def __init__(self, openai_service: OpenAIService):
        """
        Initialize the summarizer with an OpenAI service instance.

        Parameters:
            openai_service (OpenAIService): Service handling OpenAI API interactions
        """
        self.openai_service = openai_service

    async def summarize_transcription(
        self, transcription: str, language: str
    ) -> Optional[str]:
        """
        Summarizes the provided transcription using GPT, taking into account the language
        of the original content. The summary maintains the original language and tone while
        condensing the content into a clear, concise format.

        Parameters:
            transcription (str): The text to be summarized
            language (str): The detected language of the transcription, used to ensure
                          the summary maintains the same language

        Returns:
            Optional[str]: A concise summary of the transcription, or None if summarization fails
        """
        try:
            # Construct the message array for the chat completion
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert at summarizing spoken conversations. "
                        "Your task is to create a clear, concise summary of audio transcripts while:\n\n"
                        "1. Capturing the essential meaning and key points\n"
                        "2. Maintaining the original tone and language of the speaker\n"
                        "3. Preserving important details, numbers, or specific references\n"
                        "4. Keeping the summary to 2-3 sentences maximum\n"
                        "5. Using natural, conversational language that reflects spoken communication\n\n"
                        "Remember this is transcribed speech, so focus on the core message rather than exact wording. "
                        "If the transcript contains filler words or speech artifacts, distill the actual meaning.\n"
                        f"The detected language of this audio is: {language}"
                    ),
                },
                {"role": "user", "content": transcription},
            ]

            # Generate the summary using the OpenAI service
            summary = await self.openai_service.generate_chat_completion(
                messages=messages, model="gpt-4o-mini", temperature=0.2
            )

            if summary:
                logging.info(f"Successfully generated summary in {language}")
                return summary

            logging.warning("Failed to generate summary - no content returned")
            return None

        except Exception as e:
            logging.error(f"Error summarizing transcription: {str(e)}", exc_info=True)
            return None
