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
    EXPORTED = "exported"
    SENT = "sent"
    CALLBACK = "callback"
    OFFER = "offer"
    CLOSED = "closed"


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
    resume_content: Optional[str] = Field(default=None)
    cover_letter_content: Optional[str] = Field(default=None)
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
        if self.status and not isinstance(self.status, ApplicationStatus):
            try:
                self.status = ApplicationStatus(self.status)
            except ValueError:
                raise ValueError(f"Invalid status: {self.status}")


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
    resume_content: Optional[str]
    cover_letter_content: Optional[str]
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
    resume_content: Optional[str] = None
    cover_letter_content: Optional[str] = None
