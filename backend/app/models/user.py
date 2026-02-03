"""User model and schemas."""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    """User database model."""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=50)
    password_hash: str = Field(max_length=255)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __init__(self, **data: Any) -> None:
        """Initialize User with validation.

        SQLModel table models bypass Pydantic validation, so we enforce
        constraints manually in __init__.
        """
        super().__init__(**data)
        self._validate_fields()

    def _validate_fields(self) -> None:
        """Validate field constraints."""
        if not self.username or len(self.username) < 1:
            raise ValueError("username cannot be empty")
        if len(self.username) > 50:
            raise ValueError("username cannot exceed 50 characters")
        if not self.password_hash:
            raise ValueError("password_hash is required")
        if len(self.password_hash) < 60:
            raise ValueError("password_hash must be at least 60 characters")
        if len(self.password_hash) > 255:
            raise ValueError("password_hash cannot exceed 255 characters")

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<User(id={self.id}, username='{self.username}')>"


class UserCreate(SQLModel):
    """Request schema for user registration."""

    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class UserRead(SQLModel):
    """Response schema for user data (never expose password_hash)."""

    id: int
    username: str
    created_at: datetime
