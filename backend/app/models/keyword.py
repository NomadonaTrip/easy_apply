"""Keyword schemas for job description keyword extraction."""

from enum import Enum

from pydantic import BaseModel, Field


class KeywordCategory(str, Enum):
    TECHNICAL_SKILL = "technical_skill"
    SOFT_SKILL = "soft_skill"
    EXPERIENCE = "experience"
    QUALIFICATION = "qualification"
    TOOL = "tool"
    DOMAIN = "domain"
    GENERAL = "general"


class Keyword(BaseModel):
    """Single keyword with priority and category."""

    text: str = Field(min_length=1, max_length=100)
    priority: int = Field(ge=1, le=10)
    category: KeywordCategory = KeywordCategory.GENERAL


class KeywordList(BaseModel):
    """List of keywords for an application."""

    keywords: list[Keyword] = []


class KeywordExtractionResponse(BaseModel):
    """Response from keyword extraction endpoint."""

    application_id: int
    keywords: list[Keyword]
    status: str
