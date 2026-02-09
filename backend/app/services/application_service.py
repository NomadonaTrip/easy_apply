"""Application service with CRUD operations."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import select

from app.database import async_session_maker
from app.models.application import Application, ApplicationCreate, ApplicationUpdate


async def get_applications(role_id: int) -> list[Application]:
    """Get all applications for a role.

    CRITICAL: Always filter by role_id - no exceptions!
    """
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    async with async_session_maker() as session:
        result = await session.execute(
            select(Application)
            .where(Application.role_id == role_id)
            .order_by(Application.updated_at.desc())
        )
        applications = result.scalars().all()
        for app in applications:
            session.expunge(app)
        return list(applications)


async def get_application(id: int, role_id: int) -> Optional[Application]:
    """Get single application, verify role ownership."""
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    async with async_session_maker() as session:
        result = await session.execute(
            select(Application).where(
                Application.id == id,
                Application.role_id == role_id  # ALWAYS include role filter
            )
        )
        application = result.scalar_one_or_none()
        if application:
            session.expunge(application)
        return application


async def create_application(
    role_id: int,
    data: ApplicationCreate,
) -> Application:
    """Create application. role_id injected from auth context, not user input."""
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    async with async_session_maker() as session:
        application = Application(**data.model_dump(), role_id=role_id)
        session.add(application)
        await session.commit()
        await session.refresh(application)
        session.expunge(application)
        return application


async def update_application(
    id: int,
    role_id: int,
    data: ApplicationUpdate,
) -> Optional[Application]:
    """Update with role ownership check."""
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    async with async_session_maker() as session:
        result = await session.execute(
            select(Application).where(
                Application.id == id,
                Application.role_id == role_id
            )
        )
        application = result.scalar_one_or_none()
        if not application:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(application, key, value)
        application.updated_at = datetime.now(timezone.utc)

        session.add(application)
        await session.commit()
        await session.refresh(application)
        session.expunge(application)
        return application


async def update_manual_context(
    id: int,
    role_id: int,
    sanitized_context: str,
) -> Optional[Application]:
    """Update manual_context with role ownership check.

    This is the ONLY write path for manual_context. The value must be
    pre-sanitized (html.escape) by the caller in the API layer.
    """
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    async with async_session_maker() as session:
        result = await session.execute(
            select(Application).where(
                Application.id == id,
                Application.role_id == role_id
            )
        )
        application = result.scalar_one_or_none()
        if not application:
            return None

        application.manual_context = sanitized_context
        application.updated_at = datetime.now(timezone.utc)

        session.add(application)
        await session.commit()
        await session.refresh(application)
        session.expunge(application)
        return application
