"""EnrichmentCandidate model for experience enrichment suggestions."""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlmodel import SQLModel, Field


class EnrichmentCandidate(SQLModel, table=True):
    """Pending enrichment suggestion from document analysis."""

    __tablename__ = "enrichment_candidates"

    id: Optional[int] = Field(default=None, primary_key=True)
    role_id: int = Field(foreign_key="roles.id", index=True)
    # TODO: Add ON DELETE CASCADE when application deletion is implemented.
    # SQLite requires table recreation for FK constraint changes.
    application_id: int = Field(foreign_key="applications.id", index=True)
    document_type: str = Field(max_length=20)       # "resume" or "cover_letter"
    candidate_type: str = Field(max_length=20)       # "skill" or "accomplishment"
    name: str = Field(max_length=200)
    category: Optional[str] = Field(default=None, max_length=50)
    context: Optional[str] = Field(default=None)
    status: str = Field(default="pending", max_length=20)  # pending, accepted, dismissed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = Field(default=None)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._validate_fields()

    def _validate_fields(self) -> None:
        if not self.name or len(self.name.strip()) < 1:
            raise ValueError("name cannot be empty")
        if self.document_type not in ("resume", "cover_letter"):
            raise ValueError("document_type must be 'resume' or 'cover_letter'")
        if self.candidate_type not in ("skill", "accomplishment"):
            raise ValueError("candidate_type must be 'skill' or 'accomplishment'")
        if self.status not in ("pending", "accepted", "dismissed"):
            raise ValueError("status must be 'pending', 'accepted', or 'dismissed'")
        # Truncate LLM-generated category if it exceeds column max_length
        if self.category and len(self.category) > 50:
            self.category = self.category[:50]


class EnrichmentCandidateRead(SQLModel):
    """Response schema for enrichment candidate data."""

    id: int
    role_id: int
    application_id: int
    document_type: str
    candidate_type: str
    name: str
    category: Optional[str] = None
    context: Optional[str] = None
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
