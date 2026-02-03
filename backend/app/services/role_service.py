"""Role service with CRUD operations."""

from typing import Optional

from sqlmodel import select

from app.models.role import Role, RoleCreate
from app.database import async_session_maker


async def get_roles_by_user(user_id: int) -> list[Role]:
    """Get all roles for a user."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Role).where(Role.user_id == user_id)
        )
        roles = result.scalars().all()
        # Expunge all roles to detach from session
        for role in roles:
            session.expunge(role)
        return list(roles)


async def get_role_by_id(role_id: int) -> Optional[Role]:
    """Get role by ID or None if not found."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Role).where(Role.id == role_id)
        )
        role = result.scalar_one_or_none()
        if role:
            session.expunge(role)
        return role


async def create_role(user_id: int, role_data: RoleCreate) -> Role:
    """Create a new role for a user."""
    async with async_session_maker() as session:
        role = Role(
            user_id=user_id,
            name=role_data.name
        )
        session.add(role)
        await session.commit()
        await session.refresh(role)
        session.expunge(role)
        return role


async def delete_role(role_id: int, user_id: int) -> bool:
    """
    Delete a role with ownership verification.
    Returns True if deleted, raises ValueError if not found or not owned.
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(Role).where(Role.id == role_id)
        )
        role = result.scalar_one_or_none()

        if not role:
            raise ValueError("Role not found")
        if role.user_id != user_id:
            raise ValueError("Access denied to this role")

        await session.delete(role)
        await session.commit()
        return True
