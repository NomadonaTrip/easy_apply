"""Session management service with in-memory storage."""

import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

# In-memory session storage (sufficient for 2-user local tool)
# Format: {session_token: {"user_id": int, "expires_at": datetime}}
_sessions: dict[str, dict] = {}

SESSION_TIMEOUT_HOURS = 24


def create_session(user_id: int) -> str:
    """Create a new session and return the token."""
    # Generate secure random token
    token = secrets.token_urlsafe(32)

    # Store session with expiry
    _sessions[token] = {
        "user_id": user_id,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=SESSION_TIMEOUT_HOURS)
    }

    return token


def validate_session(token: str) -> Optional[int]:
    """Validate session token, return user_id if valid."""
    session = _sessions.get(token)
    if not session:
        return None

    # Check expiry
    if datetime.now(timezone.utc) > session["expires_at"]:
        # Clean up expired session
        del _sessions[token]
        return None

    return session["user_id"]


def invalidate_session(token: str) -> bool:
    """Invalidate a session (logout). Returns True if session existed."""
    if token in _sessions:
        del _sessions[token]
        return True
    return False


def cleanup_expired_sessions() -> None:
    """Remove all expired sessions."""
    now = datetime.now(timezone.utc)
    expired = [token for token, data in _sessions.items() if now > data["expires_at"]]
    for token in expired:
        del _sessions[token]
