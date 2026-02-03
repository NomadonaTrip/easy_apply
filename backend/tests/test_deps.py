"""Tests for API dependencies."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlmodel import select
from app.main import app
from app.database import async_session_maker, init_db
from app.models.user import User
from app.services import session_service


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Initialize DB and clean up users before each test."""
    await init_db()
    async with async_session_maker() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        for user in users:
            await session.delete(user)
        await session.commit()
    # Clear sessions
    session_service._sessions.clear()
    yield


@pytest_asyncio.fixture
async def client():
    """Async test client for FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def authenticated_client(client):
    """Client with authenticated session."""
    # Register and login
    await client.post(
        "/api/v1/auth/register",
        json={"username": "authuser", "password": "password123"}
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "authuser", "password": "password123"}
    )
    # Return client with session cookie
    return client, login_response.cookies


@pytest.mark.asyncio
async def test_get_current_user_with_valid_session(authenticated_client):
    """get_current_user returns user with valid session cookie."""
    client, cookies = authenticated_client
    response = await client.get("/api/v1/auth/me", cookies=cookies)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "authuser"
    assert "id" in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_get_current_user_without_session(client):
    """get_current_user returns 401 without session cookie."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "not authenticated" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_current_user_with_invalid_session(client):
    """get_current_user returns 401 with invalid session cookie."""
    response = await client.get(
        "/api/v1/auth/me",
        cookies={"session": "invalid-token-that-doesnt-exist"}
    )
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower() or "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_current_user_with_expired_session(authenticated_client):
    """get_current_user returns 401 with expired session."""
    client, cookies = authenticated_client
    session_token = cookies.get("session")

    # Manually expire the session
    from datetime import datetime, timezone, timedelta
    if session_token in session_service._sessions:
        session_service._sessions[session_token]["expires_at"] = datetime.now(timezone.utc) - timedelta(hours=1)

    response = await client.get("/api/v1/auth/me", cookies=cookies)
    assert response.status_code == 401
