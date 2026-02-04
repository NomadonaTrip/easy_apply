"""Resume model and schemas."""

from datetime import datetime, timezone
from typing import Any, Optional, TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

# Import allowed extensions from file_storage to maintain single source of truth
from app.utils.file_storage import ALLOWED_EXTENSIONS as ALLOWED_FILE_TYPES

if TYPE_CHECKING:
    from app.models.role import Role


class Resume(SQLModel, table=True):
    """Resume database model - represents an uploaded resume file."""

    __tablename__ = "resumes"

    id: Optional[int] = Field(default=None, primary_key=True)
    role_id: int = Field(foreign_key="roles.id", index=True)
    filename: str = Field(max_length=255)
    file_path: str = Field(max_length=500)  # Relative path from data/
    file_type: str = Field(max_length=50)  # "pdf" or "docx"
    file_size: int  # bytes
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    processed: bool = Field(default=False)  # True after skill extraction

    # Relationship back to Role
    role: Optional["Role"] = Relationship(back_populates="resumes")

    def __init__(self, **data: Any) -> None:
        """Initialize Resume with validation.

        SQLModel table models bypass Pydantic validation, so we enforce
        constraints manually in __init__.
        """
        super().__init__(**data)
        self._validate_fields()

    def _validate_fields(self) -> None:
        """Validate field constraints."""
        if not self.filename or len(self.filename.strip()) < 1:
            raise ValueError("filename cannot be empty")
        if len(self.filename) > 255:
            raise ValueError("filename cannot exceed 255 characters")
        if self.role_id is None:
            raise ValueError("role_id is required")
        if self.file_type not in ALLOWED_FILE_TYPES:
            raise ValueError(f"file_type must be one of: {', '.join(ALLOWED_FILE_TYPES)}")
        if self.file_size is None or self.file_size < 0:
            raise ValueError("file_size must be a positive integer")
        if not self.file_path or len(self.file_path.strip()) < 1:
            raise ValueError("file_path cannot be empty")

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<Resume(id={self.id}, filename='{self.filename}', role_id={self.role_id})>"


class ResumeCreate(SQLModel):
    """Schema for internal resume creation (not exposed via API)."""

    filename: str = Field(min_length=1, max_length=255)
    file_type: str = Field(min_length=1, max_length=50)
    file_size: int = Field(ge=0)
    file_path: str = Field(min_length=1, max_length=500)


class ResumeRead(SQLModel):
    """Response schema for resume data."""

    id: int
    role_id: int
    filename: str
    file_path: str
    file_type: str
    file_size: int
    uploaded_at: datetime
    processed: bool
