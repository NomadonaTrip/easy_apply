"""Experience models for skills and accomplishments."""

from datetime import datetime, timezone
from typing import Any, Optional, TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.role import Role


class Skill(SQLModel, table=True):
    """Skill database model - represents a professional skill."""

    __tablename__ = "skills"

    id: Optional[int] = Field(default=None, primary_key=True)
    role_id: int = Field(foreign_key="roles.id", index=True)
    name: str = Field(max_length=200)
    category: Optional[str] = Field(default=None, max_length=100)
    source: Optional[str] = Field(default=None, max_length=50)  # "resume" or "application"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Relationship back to Role
    role: Optional["Role"] = Relationship(back_populates="skills")

    def __init__(self, **data: Any) -> None:
        """Initialize Skill with validation."""
        super().__init__(**data)
        self._validate_fields()

    def _validate_fields(self) -> None:
        """Validate field constraints."""
        if not self.name or len(self.name.strip()) < 1:
            raise ValueError("name cannot be empty")
        if len(self.name) > 200:
            raise ValueError("name cannot exceed 200 characters")
        if self.role_id is None:
            raise ValueError("role_id is required")


class SkillCreate(SQLModel):
    """Request schema for skill creation."""

    name: str = Field(min_length=1, max_length=200)
    category: Optional[str] = Field(default=None, max_length=100)
    source: Optional[str] = Field(default=None, max_length=50)


class SkillRead(SQLModel):
    """Response schema for skill data."""

    id: int
    role_id: int
    name: str
    category: Optional[str]
    source: Optional[str]
    created_at: datetime


class SkillUpdate(SQLModel):
    """Request schema for skill updates. All fields optional."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    category: Optional[str] = Field(default=None, max_length=100)
    source: Optional[str] = Field(default=None, max_length=50)


class Accomplishment(SQLModel, table=True):
    """Accomplishment database model - represents a professional achievement."""

    __tablename__ = "accomplishments"

    id: Optional[int] = Field(default=None, primary_key=True)
    role_id: int = Field(foreign_key="roles.id", index=True)
    description: str = Field(max_length=1000)
    context: Optional[str] = Field(default=None, max_length=500)
    source: Optional[str] = Field(default=None, max_length=50)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Relationship back to Role
    role: Optional["Role"] = Relationship(back_populates="accomplishments")

    def __init__(self, **data: Any) -> None:
        """Initialize Accomplishment with validation."""
        super().__init__(**data)
        self._validate_fields()

    def _validate_fields(self) -> None:
        """Validate field constraints."""
        if not self.description or len(self.description.strip()) < 1:
            raise ValueError("description cannot be empty")
        if len(self.description) > 1000:
            raise ValueError("description cannot exceed 1000 characters")
        if self.role_id is None:
            raise ValueError("role_id is required")


class AccomplishmentCreate(SQLModel):
    """Request schema for accomplishment creation."""

    description: str = Field(min_length=1, max_length=1000)
    context: Optional[str] = Field(default=None, max_length=500)
    source: Optional[str] = Field(default=None, max_length=50)


class AccomplishmentRead(SQLModel):
    """Response schema for accomplishment data."""

    id: int
    role_id: int
    description: str
    context: Optional[str]
    source: Optional[str]
    created_at: datetime


class AccomplishmentUpdate(SQLModel):
    """Request schema for accomplishment updates. All fields optional."""

    description: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    context: Optional[str] = Field(default=None, max_length=500)
    source: Optional[str] = Field(default=None, max_length=50)
