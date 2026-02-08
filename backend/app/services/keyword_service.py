"""Keyword extraction service using LLM Provider."""

import json
import logging

from fastapi import HTTPException

from app.llm import get_llm_provider, Message, Role
from app.llm.prompts import PromptRegistry
from app.models.keyword import Keyword, KeywordList
from app.utils.llm_helpers import extract_json_from_response, generate_with_retry

logger = logging.getLogger(__name__)


async def extract_keywords(job_posting: str) -> KeywordList:
    """
    Extract and rank keywords from job posting using LLM Provider.

    Returns keywords with priority scores (1-10, higher = more important).
    """
    try:
        provider = get_llm_provider()

        prompt = PromptRegistry.get("keyword_extraction", job_posting=job_posting)

        messages = [Message(role=Role.USER, content=prompt)]
        response = await generate_with_retry(provider, messages)
        result = response.content

        if not result:
            raise HTTPException(status_code=500, detail="Failed to extract keywords")

        cleaned_json = extract_json_from_response(result)
        logger.debug(f"Raw LLM response length: {len(result)}, cleaned: {len(cleaned_json)}")

        try:
            data = json.loads(cleaned_json)
            keywords = [
                Keyword(
                    text=k["text"],
                    priority=k["priority"],
                    category=k.get("category", "general")
                )
                for k in data.get("keywords", [])
            ]
        except (json.JSONDecodeError, KeyError):
            logger.error(f"JSON parse failed. Raw response: {result[:500]}")
            raise HTTPException(status_code=500, detail="Failed to parse keyword extraction response")

        keywords.sort(key=lambda k: k.priority, reverse=True)

        return KeywordList(keywords=keywords)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Keyword extraction failed: {e}")
        raise HTTPException(status_code=500, detail="Keyword extraction failed")


def keywords_to_json(keyword_list: KeywordList) -> str:
    """Serialize keywords for database storage."""
    return json.dumps([k.model_dump() for k in keyword_list.keywords])


def json_to_keywords(json_str: str) -> KeywordList:
    """Deserialize keywords from database."""
    if not json_str:
        return KeywordList(keywords=[])
    data = json.loads(json_str)
    return KeywordList(keywords=[Keyword(**k) for k in data])
