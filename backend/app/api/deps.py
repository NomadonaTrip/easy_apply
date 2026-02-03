from collections.abc import AsyncGenerator
from typing import Optional

from fastapi import HTTPException, status, Cookie
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.user import User
from app.services import auth_service, session_service


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database session."""
    async with async_session_maker() as session:
        yield session


async def get_current_user(
    session: Optional[str] = Cookie(default=None)
) -> User:
    """
    Dependency to get the current authenticated user.
    Raises 401 if not authenticated.
    """
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    user_id = session_service.validate_session(session)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )

    user = await auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user
