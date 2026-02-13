"""Application model and schemas."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlmodel import SQLModel, Field


class ApplicationStatus(str, Enum):
    CREATED = "created"
    KEYWORDS = "keywords"
    RESEARCHING = "researching"
    REVIEWED = "reviewed"
    GENERATING = "generating"
    EXPORTED = "exported"
    SENT = "sent"
    CALLBACK = "callback"
    OFFER = "offer"
    CLOSED = "closed"


class GenerationStatus(str, Enum):
    IDLE = "idle"
    GENERATING_RESUME = "generating_resume"
    GENERATING_COVER_LETTER = "generating_cover_letter"
    COMPLETE = "complete"
    FAILED = "failed"


class Application(SQLModel, table=True):
    """Application database model - represents a job application."""

    __tablename__ = "applications"

    id: Optional[int] = Field(default=None, primary_key=True)
    role_id: int = Field(foreign_key="roles.id", index=True)
    company_name: str = Field(max_length=255)
    job_posting: str  # Full job description text
    job_url: Optional[str] = Field(default=None, max_length=2048)
    status: ApplicationStatus = Field(default=ApplicationStatus.CREATED)
    keywords: Optional[str] = Field(default=None)  # JSON string of keyword list
    research_data: Optional[str] = Field(default=None)  # JSON string
    manual_context: Optional[str] = Field(default=None, max_length=5000)
    generation_status: GenerationStatus = Field(default=GenerationStatus.IDLE)
    resume_content: Optional[str] = Field(default=None)
    cover_letter_content: Optional[str] = Field(default=None)
    cover_letter_tone: Optional[str] = Field(default=None, max_length=50)
    resume_violations_fixed: Optional[int] = Field(default=None)
    resume_constraint_warnings: Optional[str] = Field(default=None)  # JSON list
    cover_letter_violations_fixed: Optional[int] = Field(default=None)
    cover_letter_constraint_warnings: Optional[str] = Field(default=None)  # JSON list
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __init__(self, **data: Any) -> None:
        """Manual validation required because table=True bypasses Pydantic."""
        super().__init__(**data)
        self._validate_fields()

    def _validate_fields(self) -> None:
        if not self.company_name or len(self.company_name.strip()) < 1:
            raise ValueError("company_name cannot be empty")
        if len(self.company_name) > 255:
            raise ValueError("company_name must be 255 characters or fewer")
        if not self.job_posting or len(self.job_posting.strip()) < 1:
            raise ValueError("job_posting cannot be empty")
        if self.job_url and len(self.job_url) > 2048:
            raise ValueError("job_url must be 2048 characters or fewer")
        if self.manual_context and len(self.manual_context) > 5000:
            raise ValueError("manual_context must be 5000 characters or fewer")
        if self.status and not isinstance(self.status, ApplicationStatus):
            try:
                self.status = ApplicationStatus(self.status)
            except ValueError:
                raise ValueError(f"Invalid status: {self.status}")
        if self.generation_status and not isinstance(self.generation_status, GenerationStatus):
            try:
                self.generation_status = GenerationStatus(self.generation_status)
            except ValueError:
                raise ValueError(f"Invalid generation_status: {self.generation_status}")


class ApplicationCreate(SQLModel):
    """Request schema for application creation."""

    company_name: str = Field(min_length=1, max_length=255)
    job_posting: str = Field(min_length=10)
    job_url: Optional[str] = Field(default=None, max_length=2048)


class ApplicationRead(SQLModel):
    """Response schema for application data."""

    id: int
    role_id: int
    company_name: str
    job_posting: str
    job_url: Optional[str]
    status: ApplicationStatus
    keywords: Optional[str]
    research_data: Optional[str]
    manual_context: Optional[str]
    generation_status: GenerationStatus
    resume_content: Optional[str]
    cover_letter_content: Optional[str]
    cover_letter_tone: Optional[str]
    resume_violations_fixed: Optional[int]
    resume_constraint_warnings: Optional[str]
    cover_letter_violations_fixed: Optional[int]
    cover_letter_constraint_warnings: Optional[str]
    created_at: datetime
    updated_at: datetime


class ApplicationUpdate(SQLModel):
    """Update schema for application (all optional)."""

    company_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    job_posting: Optional[str] = Field(default=None, min_length=1)
    job_url: Optional[str] = Field(default=None, max_length=2048)
    status: Optional[ApplicationStatus] = None
    keywords: Optional[str] = None
    research_data: Optional[str] = None
    # manual_context excluded: all writes must go through the dedicated
    # PATCH /{id}/context endpoint which applies HTML sanitization.
    generation_status: Optional[GenerationStatus] = None
    resume_content: Optional[str] = None
    cover_letter_content: Optional[str] = None
    cover_letter_tone: Optional[str] = Field(default=None, max_length=50)
    resume_violations_fixed: Optional[int] = None
    resume_constraint_warnings: Optional[str] = None
    cover_letter_violations_fixed: Optional[int] = None
    cover_letter_constraint_warnings: Optional[str] = None
