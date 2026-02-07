"""Tests for test database isolation infrastructure (Story 0.0)."""

import pytest
from sqlmodel import select

from app.config import settings


# =============================================================================
# Task 1: Test Database Configuration Tests
# =============================================================================


def test_settings_has_testing_flag():
    """Test that Settings has a testing flag, defaulting to False."""
    assert hasattr(settings, "testing")
    # Verify the field accepts False (conftest sets testing=True before tests run)
    original = settings.testing
    try:
        settings.testing = False
        assert settings.testing is False
    finally:
        settings.testing = original


def test_settings_testing_flag_changes_database_url():
    """Test that when testing=True, database_url points to test DB."""
    original = settings.testing
    try:
        settings.testing = True
        assert "test_easy_apply.db" in settings.database_url
    finally:
        settings.testing = original


def test_settings_production_database_url():
    """Test that when testing=False, database_url points to production DB."""
    original = settings.testing
    try:
        settings.testing = False
        assert "easy_apply.db" in settings.database_url
        assert "test_easy_apply.db" not in settings.database_url
    finally:
        settings.testing = original


# =============================================================================
# Task 2: Test DB Isolation Verification
# =============================================================================


@pytest.mark.asyncio
async def test_tests_use_test_database():
    """Test that the test suite uses the test database, not production."""
    from app.database import async_session_maker
    from sqlalchemy import text

    async with async_session_maker() as session:
        # Check the database file path by querying the pragma
        result = await session.execute(text("PRAGMA database_list"))
        rows = result.fetchall()
        db_path = rows[0][2]  # The file path is the third column
        assert "test_easy_apply.db" in db_path, (
            f"Tests should use test DB but using: {db_path}"
        )


@pytest.mark.asyncio
async def test_production_db_not_affected():
    """Test that production database is not modified by tests."""
    # Production DB may or may not exist; if it does, we just verify
    # we're not connected to it
    from app.database import get_engine

    url = str(get_engine().url)
    assert "test_easy_apply.db" in url, (
        f"Engine should point to test DB but points to: {url}"
    )


@pytest.mark.asyncio
async def test_clean_database_fixture_isolates_tests():
    """Test that each test starts with a clean database state."""
    from app.database import async_session_maker
    from app.models.user import User

    # At the start of any test, the database should be empty
    # (the autouse clean_database fixture runs before each test)
    async with async_session_maker() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        assert len(users) == 0, "Database should be clean at test start"


