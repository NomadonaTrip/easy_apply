"""Role model and schemas."""

from datetime import datetime, timezone
from typing import Any, Optional, TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.experience import Skill, Accomplishment
    from app.models.resume import Resume


class Role(SQLModel, table=True):
    """Role database model - represents a career track for a user."""

    __tablename__ = "roles"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str = Field(max_length=100)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Relationship back to User
    user: Optional["User"] = Relationship(back_populates="roles")

    # Relationships to experience data (role-scoped)
    skills: list["Skill"] = Relationship(back_populates="role")
    accomplishments: list["Accomplishment"] = Relationship(back_populates="role")
    resumes: list["Resume"] = Relationship(back_populates="role")

    def __init__(self, **data: Any) -> None:
        """Initialize Role with validation.

        SQLModel table models bypass Pydantic validation, so we enforce
        constraints manually in __init__.
        """
        super().__init__(**data)
        self._validate_fields()

    def _validate_fields(self) -> None:
        """Validate field constraints."""
        if not self.name or len(self.name.strip()) < 1:
            raise ValueError("name cannot be empty")
        if len(self.name) > 100:
            raise ValueError("name cannot exceed 100 characters")
        if self.user_id is None:
            raise ValueError("user_id is required")

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<Role(id={self.id}, name='{self.name}', user_id={self.user_id})>"


class RoleCreate(SQLModel):
    """Request schema for role creation."""

    name: str = Field(min_length=1, max_length=100)


class RoleRead(SQLModel):
    """Response schema for role data."""

    id: int
    user_id: int
    name: str
    created_at: datetime
