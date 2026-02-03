"""Authentication service with password hashing and user management."""

import bcrypt
from sqlmodel import select, func

from app.models.user import User, UserCreate
from app.database import async_session_maker


MAX_ACCOUNTS = 2


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


async def get_user_count() -> int:
    """Get total number of registered users."""
    async with async_session_maker() as session:
        result = await session.execute(select(func.count()).select_from(User))
        return result.scalar_one()


async def get_user_by_username(username: str) -> User | None:
    """Get user by username or None if not found."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        if user:
            # Expunge to detach from session so it can be used after session closes
            session.expunge(user)
        return user


async def get_user_by_id(user_id: int) -> User | None:
    """Get user by ID or None if not found."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user:
            session.expunge(user)
        return user


async def create_user(user_data: UserCreate) -> User:
    """
    Create a new user with hashed password.
    Raises ValueError if max accounts reached or username taken.

    Note: All checks and creation happen in a single transaction to prevent
    race conditions that could allow exceeding the 2-account limit.
    """
    async with async_session_maker() as session:
        # Check account limit (inside transaction)
        count_result = await session.execute(select(func.count()).select_from(User))
        if count_result.scalar_one() >= MAX_ACCOUNTS:
            raise ValueError("Maximum accounts reached")

        # Check username uniqueness (inside same transaction)
        existing_result = await session.execute(
            select(User).where(User.username == user_data.username)
        )
        if existing_result.scalar_one_or_none():
            raise ValueError("Username already taken")

        # Create user with hashed password (same transaction)
        user = User(
            username=user_data.username,
            password_hash=hash_password(user_data.password)
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        # Expunge so user can be used after session closes
        session.expunge(user)
        return user
