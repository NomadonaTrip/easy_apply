"""Tests for authentication service."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlmodel import select
from app.main import app
from app.database import async_session_maker, init_db
from app.models.user import User


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
    yield


@pytest_asyncio.fixture
async def client():
    """Async test client for FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_register_success(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "password123"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert "id" in data
    assert "created_at" in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_duplicate_username(client):
    # First registration
    await client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "password123"}
    )
    # Second registration with same username
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "different123"}
    )
    assert response.status_code == 409
    assert "already taken" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_max_accounts(client):
    # Create first two accounts
    await client.post("/api/v1/auth/register", json={"username": "user1", "password": "password123"})
    await client.post("/api/v1/auth/register", json={"username": "user2", "password": "password123"})

    # Try to create third account
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "user3", "password": "password123"}
    )
    assert response.status_code == 409
    assert "maximum" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_password_too_short(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "short"}
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_register_username_too_short(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "ab", "password": "password123"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_account_limit_check(client):
    response = await client.get("/api/v1/auth/account-limit")
    assert response.status_code == 200
    data = response.json()
    assert data["current_count"] == 0
    assert data["max_accounts"] == 2
    assert data["registration_allowed"] == True


@pytest.mark.asyncio
async def test_password_is_hashed(client):
    await client.post(
        "/api/v1/auth/register",
        json={"username": "hashtest", "password": "password123"}
    )
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.username == "hashtest"))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.password_hash != "password123"
        assert user.password_hash.startswith("$2b$")  # bcrypt prefix


# Login Tests (Story 1-4)

@pytest.mark.asyncio
async def test_login_success(client):
    """Successful login returns user data and sets session cookie."""
    # First register a user
    await client.post(
        "/api/v1/auth/register",
        json={"username": "logintest", "password": "password123"}
    )

    # Then login
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "logintest", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "logintest"
    assert "id" in data
    assert "created_at" in data
    assert "password_hash" not in data
    assert "session" in response.cookies


@pytest.mark.asyncio
async def test_login_invalid_username(client):
    """Login with nonexistent username returns 401."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "nonexistent", "password": "password123"}
    )
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_invalid_password(client):
    """Login with wrong password returns 401."""
    # Register first
    await client.post(
        "/api/v1/auth/register",
        json={"username": "pwtest", "password": "password123"}
    )

    # Login with wrong password
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "pwtest", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_cookie_is_httponly(client):
    """Session cookie should be HTTP-only."""
    # Register and login
    await client.post(
        "/api/v1/auth/register",
        json={"username": "cookietest", "password": "password123"}
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "cookietest", "password": "password123"}
    )
    assert response.status_code == 200

    # Check cookie headers - httponly should be set
    set_cookie = response.headers.get("set-cookie", "")
    assert "httponly" in set_cookie.lower()


@pytest.mark.asyncio
async def test_login_cookie_has_samesite_lax(client):
    """Session cookie should have SameSite=Lax for CSRF protection."""
    # Register and login
    await client.post(
        "/api/v1/auth/register",
        json={"username": "samesitetest", "password": "password123"}
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "samesitetest", "password": "password123"}
    )
    assert response.status_code == 200

    # Check cookie headers - samesite=lax should be set
    set_cookie = response.headers.get("set-cookie", "")
    assert "samesite=lax" in set_cookie.lower()


# Logout Tests (Story 1-5)

@pytest.mark.asyncio
async def test_logout_clears_session(client):
    """Logout returns 200 and clears session cookie."""
    # Register and login first
    await client.post(
        "/api/v1/auth/register",
        json={"username": "logouttest", "password": "password123"}
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "logouttest", "password": "password123"}
    )

    # Set the session cookie on the client from login response
    session_cookie = login_response.cookies.get("session")
    client.cookies.set("session", session_cookie)

    # Logout
    logout_response = await client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 200

    # Verify session cookie is cleared via Set-Cookie header
    set_cookie = logout_response.headers.get("set-cookie", "")
    assert "session=" in set_cookie.lower()
    # Cookie should be set to expire (max-age=0 or expires in the past)
    assert 'max-age=0' in set_cookie.lower() or '="";' in set_cookie


@pytest.mark.asyncio
async def test_logout_invalidates_session_server_side(client):
    """Session is invalidated server-side after logout."""
    # Register and login
    await client.post(
        "/api/v1/auth/register",
        json={"username": "invalidtest", "password": "password123"}
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "invalidtest", "password": "password123"}
    )
    session_cookie = login_response.cookies.get("session")

    # Set the session cookie on the client
    client.cookies.set("session", session_cookie)

    # Logout
    await client.post("/api/v1/auth/logout")

    # Clear client cookies and set the old session token manually
    client.cookies.clear()
    client.cookies.set("session", session_cookie)

    # Try to use the old session cookie - should be invalidated server-side
    me_response = await client.get("/api/v1/auth/me")
    assert me_response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_after_logout(client):
    """Protected routes return 401 after logout."""
    # Register and login
    await client.post(
        "/api/v1/auth/register",
        json={"username": "protectedtest", "password": "password123"}
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "protectedtest", "password": "password123"}
    )
    session_cookie = login_response.cookies.get("session")

    # Set the session cookie on the client
    client.cookies.set("session", session_cookie)

    # Verify can access protected route
    me_response = await client.get("/api/v1/auth/me")
    assert me_response.status_code == 200

    # Logout
    await client.post("/api/v1/auth/logout")

    # Clear client cookies and set the old session token manually
    client.cookies.clear()
    client.cookies.set("session", session_cookie)

    # Verify protected route is now inaccessible with old session token
    me_response_after = await client.get("/api/v1/auth/me")
    assert me_response_after.status_code == 401


@pytest.mark.asyncio
async def test_logout_without_session(client):
    """Logout without being logged in should still return 200."""
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200
