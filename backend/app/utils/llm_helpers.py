"""Shared LLM helper utilities."""

import asyncio
import logging
import re

from google.genai.errors import ClientError

from app.llm import Message

logger = logging.getLogger(__name__)

# Rate limit settings for Gemini API
LLM_RETRY_MAX_ATTEMPTS = 3
LLM_RETRY_BASE_DELAY = 5.0  # seconds


def extract_json_from_response(content: str) -> str:
    """
    Extract JSON from LLM response, handling markdown code blocks.

    LLM responses often wrap JSON in ```json ... ``` blocks.
    This was a known bug in Epic 2 Story 2.7.

    Args:
        content: Raw LLM response content

    Returns:
        Cleaned JSON string
    """
    if not content:
        return ""

    code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    match = re.search(code_block_pattern, content)
    if match:
        return match.group(1).strip()

    return content.strip()


async def generate_with_retry(provider, messages: list[Message]) -> Message:
    """Call provider.generate with retry on 429 rate limit errors."""
    for attempt in range(LLM_RETRY_MAX_ATTEMPTS):
        try:
            return await provider.generate(messages)
        except ClientError as e:
            if e.code == 429 and attempt < LLM_RETRY_MAX_ATTEMPTS - 1:
                delay = LLM_RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    f"Gemini rate limit hit (429), retrying in {delay}s "
                    f"(attempt {attempt + 1}/{LLM_RETRY_MAX_ATTEMPTS})"
                )
                await asyncio.sleep(delay)
            else:
                raise
