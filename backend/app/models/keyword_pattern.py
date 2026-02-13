"""Keyword pattern model for tracking keyword success patterns."""

from datetime import datetime, timezone
from typing import Any, Optional, TYPE_CHECKING

from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.role import Role


class KeywordPattern(SQLModel, table=True):
    """Tracks keyword success patterns for a role.

    Success is measured by applications that reached "callback" or "offer" status.
    """

    __tablename__ = "keyword_patterns"

    __table_args__ = (
        UniqueConstraint("role_id", "keyword", name="uq_keyword_pattern_role_keyword"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    role_id: int = Field(foreign_key="roles.id", index=True)
    keyword: str = Field(max_length=200, index=True)

    # Success metrics
    times_used: int = Field(default=0)
    times_successful: int = Field(default=0)

    # Calculated score (updated on each success)
    success_rate: float = Field(default=0.0)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Relationship back to Role
    role: Optional["Role"] = Relationship(back_populates="keyword_patterns")

    def __init__(self, **data: Any) -> None:
        """Manual validation required because table=True bypasses Pydantic."""
        super().__init__(**data)
        self._validate_fields()

    def _validate_fields(self) -> None:
        if self.role_id is None:
            raise ValueError("role_id is required")
        if not self.keyword or len(self.keyword.strip()) < 1:
            raise ValueError("keyword cannot be empty")
        if len(self.keyword) > 200:
            raise ValueError("keyword must be 200 characters or fewer")


class KeywordPatternRead(SQLModel):
    """Response schema for keyword pattern data."""

    id: int
    role_id: int
    keyword: str
    times_used: int
    times_successful: int
    success_rate: float
