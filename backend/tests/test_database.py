"""Database configuration and User model tests."""

from datetime import timezone

import pytest
from pydantic import ValidationError
from sqlmodel import select
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.database import async_session_maker, init_db
from app.config import DATA_DIR
from app.models.user import User, UserCreate, UserRead

# Valid bcrypt hash format (60 chars) for testing
VALID_BCRYPT_HASH = "$2b$12$" + "a" * 53  # 60 chars total
VALID_BCRYPT_HASH_2 = "$2b$12$" + "b" * 53  # Different hash for uniqueness tests


async def cleanup_users():
    """Helper to clean up all users from the database."""
    async with async_session_maker() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        for user in users:
            await session.delete(user)
        await session.commit()


# =============================================================================
# Database Configuration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_database_file_created():
    """Test that SQLite database file is created at expected location."""
    await init_db()
    assert (DATA_DIR / "easy_apply.db").exists()


@pytest.mark.asyncio
async def test_wal_mode_enabled():
    """Test that WAL mode is enabled for SQLite."""
    await init_db()
    async with async_session_maker() as session:
        result = await session.execute(text("PRAGMA journal_mode"))
        row = result.fetchone()
        assert row[0].lower() == "wal"


@pytest.mark.asyncio
async def test_foreign_keys_enabled():
    """Test that foreign keys pragma is enabled for SQLite."""
    await init_db()
    async with async_session_maker() as session:
        result = await session.execute(text("PRAGMA foreign_keys"))
        row = result.fetchone()
        assert row[0] == 1, "Foreign keys should be enabled"


# =============================================================================
# User Model Tests
# =============================================================================

@pytest.mark.asyncio
async def test_user_model_create_and_read():
    """Test creating and reading a User model."""
    await init_db()
    await cleanup_users()

    async with async_session_maker() as session:
        user = User(
            username="testuser",
            password_hash=VALID_BCRYPT_HASH
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert user.id is not None
        assert user.username == "testuser"
        assert user.created_at is not None

    await cleanup_users()


@pytest.mark.asyncio
async def test_username_unique_constraint():
    """Test that username has a unique constraint."""
    await init_db()
    await cleanup_users()

    async with async_session_maker() as session:
        user1 = User(username="unique_user", password_hash=VALID_BCRYPT_HASH)
        session.add(user1)
        await session.commit()

    async with async_session_maker() as session:
        user2 = User(username="unique_user", password_hash=VALID_BCRYPT_HASH_2)
        session.add(user2)

        with pytest.raises(IntegrityError):
            await session.commit()

        await session.rollback()

    await cleanup_users()


@pytest.mark.asyncio
async def test_user_model_fields():
    """Test that User model has all required fields with correct types."""
    await init_db()
    await cleanup_users()

    async with async_session_maker() as session:
        user = User(
            username="fieldtest",
            password_hash=VALID_BCRYPT_HASH
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Verify field types
        assert isinstance(user.id, int)
        assert isinstance(user.username, str)
        assert isinstance(user.password_hash, str)
        assert user.created_at is not None

    await cleanup_users()


@pytest.mark.asyncio
async def test_user_created_at_timestamp():
    """Test that created_at timestamp is generated correctly.

    Note: SQLite doesn't preserve timezone info, so we verify the timestamp
    is generated close to current UTC time rather than checking tzinfo.
    """
    await init_db()
    await cleanup_users()

    from datetime import datetime, timedelta

    before = datetime.now(timezone.utc).replace(tzinfo=None)

    async with async_session_maker() as session:
        user = User(
            username="utctest",
            password_hash=VALID_BCRYPT_HASH
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        after = datetime.now(timezone.utc).replace(tzinfo=None)

        # Verify timestamp is within reasonable range (accounts for test execution time)
        assert user.created_at is not None
        assert before <= user.created_at <= after + timedelta(seconds=1)

    await cleanup_users()


# =============================================================================
# Schema Validation Tests (synchronous - no DB needed)
# =============================================================================

def test_user_create_schema_valid():
    """Test UserCreate schema with valid data."""
    user_create = UserCreate(username="validuser", password="validpassword123")
    assert user_create.username == "validuser"
    assert user_create.password == "validpassword123"


def test_user_create_username_min_length():
    """Test UserCreate rejects username shorter than 3 characters."""
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(username="ab", password="validpassword123")

    errors = exc_info.value.errors()
    assert any(e["loc"] == ("username",) and "at least 3" in str(e["msg"]).lower() for e in errors)


def test_user_create_username_max_length():
    """Test UserCreate rejects username longer than 50 characters."""
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(username="a" * 51, password="validpassword123")

    errors = exc_info.value.errors()
    assert any(e["loc"] == ("username",) and "at most 50" in str(e["msg"]).lower() for e in errors)


def test_user_create_password_min_length():
    """Test UserCreate rejects password shorter than 8 characters."""
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(username="validuser", password="short")

    errors = exc_info.value.errors()
    assert any(e["loc"] == ("password",) and "at least 8" in str(e["msg"]).lower() for e in errors)


def test_user_create_password_max_length():
    """Test UserCreate rejects password longer than 128 characters."""
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(username="validuser", password="a" * 129)

    errors = exc_info.value.errors()
    assert any(e["loc"] == ("password",) and "at most 128" in str(e["msg"]).lower() for e in errors)


def test_user_read_schema_excludes_password_hash():
    """Test UserRead schema does not expose password_hash field."""
    # Verify password_hash is not in UserRead fields
    assert "password_hash" not in UserRead.model_fields

    # Verify UserRead has expected fields
    assert "id" in UserRead.model_fields
    assert "username" in UserRead.model_fields
    assert "created_at" in UserRead.model_fields


@pytest.mark.asyncio
async def test_user_read_schema_from_user():
    """Test UserRead schema can be created from User model data."""
    await init_db()
    await cleanup_users()

    async with async_session_maker() as session:
        user = User(
            username="schematest",
            password_hash=VALID_BCRYPT_HASH
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Create UserRead from User data
        user_read = UserRead(
            id=user.id,
            username=user.username,
            created_at=user.created_at
        )

        assert user_read.id == user.id
        assert user_read.username == user.username
        assert user_read.created_at == user.created_at
        # Ensure password_hash is not accessible
        assert "password_hash" not in user_read.model_dump()

    await cleanup_users()


# =============================================================================
# User Model Validation Tests (SQLModel table model validation)
# =============================================================================

def test_user_model_rejects_empty_username():
    """Test User model rejects empty username."""
    with pytest.raises(ValueError, match="username cannot be empty"):
        User(username='', password_hash=VALID_BCRYPT_HASH)


def test_user_model_rejects_short_password_hash():
    """Test User model rejects password_hash < 60 chars."""
    with pytest.raises(ValueError, match="password_hash must be at least 60"):
        User(username='testuser', password_hash='tooshort')


def test_user_model_rejects_long_username():
    """Test User model rejects username > 50 chars."""
    with pytest.raises(ValueError, match="username cannot exceed 50"):
        User(username='a' * 51, password_hash=VALID_BCRYPT_HASH)


def test_user_model_rejects_long_password_hash():
    """Test User model rejects password_hash > 255 chars."""
    with pytest.raises(ValueError, match="password_hash cannot exceed 255"):
        User(username='testuser', password_hash='x' * 256)


def test_user_model_accepts_valid_boundary_values():
    """Test User model accepts valid boundary values."""
    # Min username (1 char) with valid hash
    user_min = User(username='a', password_hash=VALID_BCRYPT_HASH)
    assert user_min.username == 'a'

    # Max username (50 chars) with valid hash
    user_max = User(username='a' * 50, password_hash=VALID_BCRYPT_HASH)
    assert len(user_max.username) == 50

    # Exactly 60 char password_hash (min valid)
    user_hash_min = User(username='test', password_hash='x' * 60)
    assert len(user_hash_min.password_hash) == 60


# =============================================================================
# Boundary Value Tests for UserCreate Schema
# =============================================================================

def test_user_create_boundary_values_min():
    """Test UserCreate accepts minimum boundary values."""
    user = UserCreate(username="abc", password="12345678")  # 3 chars, 8 chars
    assert user.username == "abc"
    assert user.password == "12345678"


def test_user_create_boundary_values_max():
    """Test UserCreate accepts maximum boundary values."""
    user = UserCreate(username="a" * 50, password="p" * 128)  # 50 chars, 128 chars
    assert len(user.username) == 50
    assert len(user.password) == 128


# =============================================================================
# get_session Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_session_provides_working_session():
    """Test that get_session provides a working database session."""
    from app.database import get_session

    await init_db()
    await cleanup_users()

    # Use the dependency
    session_gen = get_session()
    session = await session_gen.__anext__()

    try:
        # Create a user through the session
        user = User(username="session_test", password_hash=VALID_BCRYPT_HASH)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert user.id is not None
    finally:
        # Cleanup
        await session_gen.aclose()

    await cleanup_users()


@pytest.mark.asyncio
async def test_get_session_no_commit_means_no_persist():
    """Test that uncommitted changes are not persisted."""
    from app.database import get_session

    await init_db()
    await cleanup_users()

    # Use the dependency but don't commit
    session_gen = get_session()
    session = await session_gen.__anext__()

    user = User(username="no_commit_test", password_hash=VALID_BCRYPT_HASH)
    session.add(user)
    # Don't commit, just close
    await session_gen.aclose()

    # Verify user was not persisted
    async with async_session_maker() as verify_session:
        result = await verify_session.execute(
            select(User).where(User.username == "no_commit_test")
        )
        assert result.scalar_one_or_none() is None
