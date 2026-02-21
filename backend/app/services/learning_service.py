"""Learning service for tracking keyword success patterns.

Tracks which keywords led to successful application outcomes (callback/offer)
and uses that data to boost keyword rankings for future applications.
"""

import json
import logging
from datetime import datetime, timezone

from sqlmodel import select, col

from app.database import async_session_maker
from app.models.keyword_pattern import KeywordPattern
from app.models.application import Application

logger = logging.getLogger(__name__)

# Statuses that count as "successful"
SUCCESS_STATUSES = ["callback", "offer"]

# Minimum uses before pattern is considered reliable
MIN_CONFIDENCE_THRESHOLD = 3


async def get_keyword_patterns(role_id: int) -> dict[str, float]:
    """Get keyword success patterns for a role.

    Returns dict of keyword -> success_rate (0.0 to 1.0).
    Only returns patterns with enough data (MIN_CONFIDENCE_THRESHOLD uses).
    """
    if role_id is None:
        raise ValueError("role_id is required")

    async with async_session_maker() as session:
        statement = select(KeywordPattern).where(
            KeywordPattern.role_id == role_id,
            KeywordPattern.times_used >= MIN_CONFIDENCE_THRESHOLD,
        )
        result = await session.execute(statement)
        patterns = result.scalars().all()

        return {p.keyword.lower(): p.success_rate for p in patterns}


async def record_keyword_usage(
    role_id: int,
    keywords: list[str],
) -> None:
    """Record that keywords were used in an application.

    Call this when an application is created with keywords.
    """
    if role_id is None:
        raise ValueError("role_id is required")

    # Normalize all keywords upfront
    normalized = []
    for keyword in keywords:
        keyword_lower = keyword.lower().strip()
        if keyword_lower:
            normalized.append(keyword_lower)

    if not normalized:
        return

    async with async_session_maker() as session:
        # Batch fetch all existing patterns in one query
        statement = select(KeywordPattern).where(
            KeywordPattern.role_id == role_id,
            col(KeywordPattern.keyword).in_(normalized),
        )
        result = await session.execute(statement)
        existing = {p.keyword: p for p in result.scalars().all()}

        for keyword_lower in normalized:
            pattern = existing.get(keyword_lower)
            if pattern:
                pattern.times_used += 1
                pattern.updated_at = datetime.now(timezone.utc)
            else:
                pattern = KeywordPattern(
                    role_id=role_id,
                    keyword=keyword_lower,
                    times_used=1,
                )
                session.add(pattern)

        await session.commit()


async def record_application_success(
    application: Application,
) -> None:
    """Record successful application outcome.

    Call this when application status changes to callback or offer.
    Updates success counts for all keywords used in this application.
    """
    if not application.keywords:
        return

    try:
        keywords_data = json.loads(application.keywords)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Could not parse keywords for application {application.id}")
        return

    # Normalize all keyword texts
    normalized = []
    for kw_entry in keywords_data:
        keyword_text = kw_entry.get("text", "") if isinstance(kw_entry, dict) else str(kw_entry)
        keyword_lower = keyword_text.lower().strip()
        if keyword_lower:
            normalized.append(keyword_lower)

    if not normalized:
        return

    async with async_session_maker() as session:
        # Batch fetch all matching patterns in one query
        statement = select(KeywordPattern).where(
            KeywordPattern.role_id == application.role_id,
            col(KeywordPattern.keyword).in_(normalized),
        )
        result = await session.execute(statement)
        existing = {p.keyword: p for p in result.scalars().all()}

        for keyword_lower in normalized:
            pattern = existing.get(keyword_lower)
            if pattern:
                pattern.times_successful += 1
                pattern.success_rate = min(1.0, pattern.times_successful / max(1, pattern.times_used))
                pattern.updated_at = datetime.now(timezone.utc)
            else:
                logger.warning(
                    "Keyword '%s' has no pattern entry for role %d "
                    "(application %d). Success not recorded.",
                    keyword_lower, application.role_id, application.id,
                )

        await session.commit()


def apply_pattern_boost(
    keywords: list[dict],
    patterns: dict[str, float],
    boost_weight: float = 0.3,
) -> list[dict]:
    """Apply pattern-based boosting to keyword scores.

    Args:
        keywords: List of {"keyword": str, "score": float, ...}
        patterns: Dict of keyword -> success_rate
        boost_weight: How much to weight pattern success (0-1)

    Returns:
        Keywords with adjusted scores, re-sorted by final score descending.
    """
    if not patterns:
        return keywords

    adjusted = []

    for kw in keywords:
        keyword_lower = kw["keyword"].lower()
        original_score = kw.get("score", 0.5)

        pattern_score = patterns.get(keyword_lower, 0.0)

        if pattern_score > 0:
            final_score = (1 - boost_weight) * original_score + boost_weight * pattern_score
            pattern_boosted = True
        else:
            final_score = original_score
            pattern_boosted = False

        adjusted.append({
            **kw,
            "score": final_score,
            "pattern_boosted": pattern_boosted,
        })

    adjusted.sort(key=lambda x: x["score"], reverse=True)

    return adjusted
