"""Research models and schemas for company research."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ResearchStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class ResearchSource(str, Enum):
    PROFILE = "profile"
    CULTURE = "culture"
    GLASSDOOR = "glassdoor"
    LINKEDIN = "linkedin"
    NEWS = "news"
    LEADERSHIP = "leadership"
    COMPETITORS = "competitors"


class ResearchSourceResult(BaseModel):
    """Result from researching a single source."""
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
    profile: Optional[ResearchSourceResult] = None
    culture: Optional[ResearchSourceResult] = None
    glassdoor: Optional[ResearchSourceResult] = None
    linkedin: Optional[ResearchSourceResult] = None
    news: Optional[ResearchSourceResult] = None
    leadership: Optional[ResearchSourceResult] = None
    competitors: Optional[ResearchSourceResult] = None
    gaps: list[str] = []  # List of sources that weren't found
    completed_at: Optional[str] = None
