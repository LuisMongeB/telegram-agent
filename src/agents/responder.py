# src/agents/responder.py
import logging
from typing import Dict, List, Optional

from openai import OpenAI


class Responder:
    """Agent responsible for generating responses based on summaries and context."""

    def __init__(self, openai_client: OpenAI):
        self.client = openai_client

    async def generate_response(
        self, summary: str, context: List[Dict[str, str]] = None
    ) -> Optional[str]:
        """Generate response considering summary and previous context."""
        try:
            # Prepare context from previous interactions
            context_str = ""
            if context:
                context_str = "\n".join(
                    [
                        f"{msg['role']}: {msg['content']}"
                        for msg in context[-3:]  # Last 3 messages
                    ]
                )

            messages = [
                {
                    "role": "system",
                    "content": (
                        "Generate an unordered list of topics included in the summary you will have been provided."
                        "Your answer must be in the language used in the summary."
                    ),
                }
            ]

            if context_str:
                messages.append(
                    {
                        "role": "user",
                        "content": f"Previous context:\n{context_str}\n\nCurrent message summary:\n{summary}",
                    }
                )
            else:
                messages.append(
                    {"role": "user", "content": f"Current message summary:\n{summary}"}
                )

            response = self.client.chat.completions.create(  # Removed await
                model="gpt-4o-mini", messages=messages
            )

            logging.info("Successfully generated response")
            return response.choices[0].message.content

        except Exception as e:
            logging.error(f"Error generating response: {str(e)}", exc_info=True)
            return None
