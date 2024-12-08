# src/agents/responder.py
import logging
from typing import Dict, List, Optional

from shared_code.services.openai_service import OpenAIService


class Responder:
    """
    Agent responsible for generating structured responses based on message summaries and context.
    This class analyzes message content and generates appropriate responses using OpenAI's GPT models.
    """

    def __init__(self, openai_service: OpenAIService):
        """
        Initialize the responder with an OpenAI service instance.

        Parameters:
            openai_service (OpenAIService): Service handling OpenAI API interactions
        """
        self.openai_service = openai_service
        # We could add configuration parameters here for response style, length, etc.
        self.max_context_messages = (
            3  # Number of previous messages to consider for context
        )

    async def generate_response(
        self, summary: str, context: Optional[List[Dict[str, str]]] = None
    ) -> Optional[str]:
        """
        Generate a response based on the provided summary and optional conversation context.

        The response will analyze the topics mentioned in the summary and present them in
        an organized format. The response maintains the same language as the input summary
        to ensure consistency in multilingual conversations.

        Parameters:
            summary (str): The processed summary of the user's message
            context (List[Dict[str, str]], optional): Previous conversation messages
                Each message should have 'role' and 'content' keys

        Returns:
            Optional[str]: Generated response organized as an unordered list of topics,
                          or None if generation fails
        """
        try:
            # Construct the context string from previous messages if available
            context_str = ""
            if context:
                # Take only the most recent messages up to our limit
                recent_context = context[-self.max_context_messages :]
                context_messages = [
                    f"{msg['role']}: {msg['content']}" for msg in recent_context
                ]
                context_str = "\n".join(context_messages)

            # Prepare the messages for the API call
            messages = [
                {
                    "role": "system",
                    "content": (
                        "Generate an unordered list of topics included in the summary "
                        "you will have been provided. Your answer must be in the language "
                        "used in the summary. Focus on key points and maintain the original "
                        "language style and tone. Each topic should be meaningful and "
                        "provide valuable insight into the content."
                    ),
                }
            ]

            # Add context and summary to the message list
            if context_str:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Previous context:\n{context_str}\n\n"
                            f"Current message summary:\n{summary}"
                        ),
                    }
                )
            else:
                messages.append(
                    {"role": "user", "content": f"Current message summary:\n{summary}"}
                )

            # Generate the response using the OpenAI service
            response_content = await self.openai_service.generate_chat_completion(
                messages=messages,
                model="gpt-4-turbo-preview",  # Using the latest model for best results
                temperature=0.7,  # Balanced between creativity and consistency
            )

            if response_content:
                logging.info("Successfully generated response from summary")
                return response_content

            logging.warning("Failed to generate response - no content returned")
            return None

        except Exception as e:
            logging.error(f"Error generating response: {str(e)}", exc_info=True)
            return None

    async def generate_follow_up(self, summary: str) -> Optional[str]:
        """
        Generate a follow-up question based on the summary content.
        This could be used to maintain conversation flow or request clarification.

        Parameters:
            summary (str): The summary to generate a follow-up for

        Returns:
            Optional[str]: A relevant follow-up question or None if generation fails
        """
        # This is a placeholder for future implementation
        # We could add this functionality to enhance the conversation
        pass
