from collections.abc import AsyncGenerator
from typing import Optional

from fastapi import HTTPException, status, Cookie, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.user import User
from app.models.role import Role
from app.services import auth_service, session_service, role_service


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


async def get_current_role(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> Role:
    """
    Extract role_id from X-Role-Id header and validate ownership.

    This dependency ensures:
    1. X-Role-Id header is present
    2. Role exists in database
    3. Role belongs to the authenticated user

    Returns the Role object for use in endpoints.
    """
    role_id_header = request.headers.get("X-Role-Id")

    if not role_id_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Role-Id header required for this endpoint"
        )

    try:
        role_id = int(role_id_header)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Role-Id must be a valid integer"
        )

    role = await role_service.get_role_by_id(role_id)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    if role.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this role"
        )

    return role
