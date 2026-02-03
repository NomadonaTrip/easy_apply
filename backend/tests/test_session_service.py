"""Tests for session service."""

import pytest
from datetime import datetime, timezone, timedelta
from app.services import session_service


def test_create_session_returns_token():
    """Session creation returns a secure token string."""
    token = session_service.create_session(user_id=1)
    assert isinstance(token, str)
    assert len(token) >= 32  # Secure token should be sufficiently long


def test_create_session_unique_tokens():
    """Each session creation generates a unique token."""
    token1 = session_service.create_session(user_id=1)
    token2 = session_service.create_session(user_id=1)
    assert token1 != token2


def test_validate_session_returns_user_id():
    """Valid session returns the correct user_id."""
    token = session_service.create_session(user_id=42)
    user_id = session_service.validate_session(token)
    assert user_id == 42


def test_validate_session_invalid_token():
    """Invalid token returns None."""
    result = session_service.validate_session("invalid-token-that-doesnt-exist")
    assert result is None


def test_invalidate_session_removes_session():
    """Invalidating a session prevents future validation."""
    token = session_service.create_session(user_id=1)
    assert session_service.validate_session(token) == 1

    result = session_service.invalidate_session(token)
    assert result is True

    assert session_service.validate_session(token) is None


def test_invalidate_session_nonexistent():
    """Invalidating a nonexistent session returns False."""
    result = session_service.invalidate_session("nonexistent-token")
    assert result is False


def test_session_expires_after_timeout():
    """Sessions expire after the timeout period."""
    # Create a session with a very short expiry for testing
    original_timeout = session_service.SESSION_TIMEOUT_HOURS
    try:
        # Temporarily set timeout to 0 for immediate expiry test
        session_service.SESSION_TIMEOUT_HOURS = 0

        # We need to manually manipulate the session to test expiry
        token = session_service.create_session(user_id=1)

        # Manually set the expiry to the past
        session_service._sessions[token]["expires_at"] = datetime.now(timezone.utc) - timedelta(hours=1)

        # Now validation should fail
        result = session_service.validate_session(token)
        assert result is None

        # Session should be cleaned up
        assert token not in session_service._sessions
    finally:
        session_service.SESSION_TIMEOUT_HOURS = original_timeout


def test_cleanup_expired_sessions():
    """cleanup_expired_sessions removes all expired sessions."""
    # Create some sessions
    token1 = session_service.create_session(user_id=1)
    token2 = session_service.create_session(user_id=2)
    token3 = session_service.create_session(user_id=3)

    # Mark token1 and token2 as expired
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    session_service._sessions[token1]["expires_at"] = past
    session_service._sessions[token2]["expires_at"] = past

    # Run cleanup
    session_service.cleanup_expired_sessions()

    # token1 and token2 should be gone, token3 should remain
    assert token1 not in session_service._sessions
    assert token2 not in session_service._sessions
    assert token3 in session_service._sessions


def test_session_timeout_default():
    """Session timeout is 24 hours by default."""
    assert session_service.SESSION_TIMEOUT_HOURS == 24


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear all sessions before and after each test."""
    session_service._sessions.clear()
    yield
    session_service._sessions.clear()
