"""Shared LLM helper utilities."""

import asyncio
import logging
import re
from typing import Optional

from google.genai.errors import ClientError

from app.llm import Message
from app.llm.base import Tool
from app.llm.types import ToolCall
from app.models.research import ResearchResult

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


async def generate_with_retry(provider, messages: list[Message], config=None) -> Message:
    """Call provider.generate with retry on 429 rate limit errors."""
    for attempt in range(LLM_RETRY_MAX_ATTEMPTS):
        try:
            return await provider.generate(messages, config)
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


def build_research_context(research: ResearchResult) -> tuple[str, Optional[str]]:
    """Build research context and gap note for generation prompts.

    Extracts found research content into a formatted string and produces
    a gap note listing missing categories. Generation services should include
    both in their prompts so the LLM knows what context is available vs missing.

    Args:
        research: Parsed ResearchResult from application.research_data.

    Returns:
        Tuple of (research_context_str, gap_note_str_or_none).
        research_context_str: Formatted research findings for prompt injection.
        gap_note_str: Note about missing categories, or None if no gaps.
    """
    category_labels = {
        "strategic_initiatives": "Strategic Initiatives",
        "competitive_landscape": "Competitive Landscape",
        "news_momentum": "Recent News & Momentum",
        "industry_context": "Industry Context",
        "culture_values": "Culture & Values",
        "leadership_direction": "Leadership Direction",
    }

    research_parts: list[str] = []
    for key, label in category_labels.items():
        source_data = getattr(research, key, None)
        if source_data and source_data.found and source_data.content:
            partial_marker = " (Note: this information may be incomplete)" if source_data.partial else ""
            research_parts.append(f"## {label}{partial_marker}\n{source_data.content}")

    research_context = "\n\n".join(research_parts) if research_parts else "No research data available."

    gap_note: Optional[str] = None
    if research.gaps:
        gap_labels = [category_labels.get(g, g) for g in research.gaps]
        gap_note = (
            f"Note: The following research categories were unavailable: {', '.join(gap_labels)}. "
            "Proceed with available information and focus on demonstrated skills and experience."
        )
        logger.info(
            "Generation proceeding with %d gaps: %s",
            len(research.gaps),
            ", ".join(research.gaps),
        )

    return research_context, gap_note


async def generate_with_tools_with_retry(
    provider, messages: list[Message], tools: list[Tool], config=None
) -> tuple[Message, list[ToolCall]]:
    """Call provider.generate_with_tools with retry on 429 rate limit errors."""
    for attempt in range(LLM_RETRY_MAX_ATTEMPTS):
        try:
            return await provider.generate_with_tools(messages, tools, config)
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
