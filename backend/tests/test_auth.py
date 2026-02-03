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
