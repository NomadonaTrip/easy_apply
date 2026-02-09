"""Research models and schemas for company research."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ResearchStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class ResearchCategory(str, Enum):
    STRATEGIC_INITIATIVES = "strategic_initiatives"
    COMPETITIVE_LANDSCAPE = "competitive_landscape"
    NEWS_MOMENTUM = "news_momentum"
    INDUSTRY_CONTEXT = "industry_context"
    CULTURE_VALUES = "culture_values"
    LEADERSHIP_DIRECTION = "leadership_direction"


class ResearchSourceResult(BaseModel):
    """Result from researching a single strategic category."""
    found: bool
    content: Optional[str] = None
    reason: Optional[str] = None  # If not found, why


class ResearchProgressEvent(BaseModel):
    """SSE event for research progress."""
    type: str = "progress"
    source: str
    status: str = "searching"
    message: str


class ResearchCompleteEvent(BaseModel):
    """SSE event for research completion."""
    type: str = "complete"
    research_data: dict[str, ResearchSourceResult]


class ResearchErrorEvent(BaseModel):
    """SSE event for research error."""
    type: str = "error"
    message: str


class ResearchResult(BaseModel):
    """Complete research result stored in application."""
    strategic_initiatives: Optional[ResearchSourceResult] = None
    competitive_landscape: Optional[ResearchSourceResult] = None
    news_momentum: Optional[ResearchSourceResult] = None
    industry_context: Optional[ResearchSourceResult] = None
    culture_values: Optional[ResearchSourceResult] = None
    leadership_direction: Optional[ResearchSourceResult] = None
    synthesis: Optional[str] = None  # Strategic narrative answering the core research question
    gaps: list[str] = []  # List of categories with incomplete context
    completed_at: Optional[str] = None
