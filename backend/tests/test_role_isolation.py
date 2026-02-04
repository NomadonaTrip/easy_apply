"""Tests for role isolation dependency and enforcement."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


# Database cleanup is handled by conftest.py's clean_database fixture


@pytest_asyncio.fixture
async def client():
    """Async test client for FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def user_with_roles(client):
    """Create a user with two roles and return auth cookies + role IDs."""
    # Register and login
    await client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "password123"}
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "password123"}
    )
    cookies = login_response.cookies

    # Create two roles
    client.cookies = cookies
    pm_response = await client.post("/api/v1/roles", json={"name": "PM"})
    ba_response = await client.post("/api/v1/roles", json={"name": "BA"})

    return {
        "cookies": cookies,
        "pm_role_id": pm_response.json()["id"],
        "ba_role_id": ba_response.json()["id"],
    }


# Test X-Role-Id header requirement (AC #4)

@pytest.mark.asyncio
async def test_missing_role_header_returns_400(client, user_with_roles):
    """Requests without X-Role-Id header should return 400."""
    client.cookies = user_with_roles["cookies"]

    # Request to a role-scoped endpoint without X-Role-Id header
    response = await client.get("/api/v1/experience/skills")
    assert response.status_code == 400
    assert "X-Role-Id" in response.json()["detail"]


@pytest.mark.asyncio
async def test_invalid_role_id_format_returns_400(client, user_with_roles):
    """Non-integer X-Role-Id header should return 400."""
    client.cookies = user_with_roles["cookies"]

    response = await client.get(
        "/api/v1/experience/skills",
        headers={"X-Role-Id": "not-a-number"}
    )
    assert response.status_code == 400
    assert "valid integer" in response.json()["detail"]


@pytest.mark.asyncio
async def test_nonexistent_role_returns_404(client, user_with_roles):
    """X-Role-Id for non-existent role should return 404."""
    client.cookies = user_with_roles["cookies"]

    response = await client.get(
        "/api/v1/experience/skills",
        headers={"X-Role-Id": "99999"}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# Test role ownership (AC #5)

@pytest.mark.asyncio
async def test_wrong_user_role_returns_403(client):
    """Accessing another user's role should return 403."""
    # Create first user with a role
    await client.post(
        "/api/v1/auth/register",
        json={"username": "user1", "password": "password123"}
    )
    login1 = await client.post(
        "/api/v1/auth/login",
        json={"username": "user1", "password": "password123"}
    )
    client.cookies = login1.cookies

    role_response = await client.post("/api/v1/roles", json={"name": "User1 Role"})
    user1_role_id = role_response.json()["id"]

    # Create second user
    await client.post(
        "/api/v1/auth/register",
        json={"username": "user2", "password": "password123"}
    )
    login2 = await client.post(
        "/api/v1/auth/login",
        json={"username": "user2", "password": "password123"}
    )
    client.cookies = login2.cookies

    # Try to use user1's role_id as user2
    response = await client.get(
        "/api/v1/experience/skills",
        headers={"X-Role-Id": str(user1_role_id)}
    )
    assert response.status_code == 403
    assert "denied" in response.json()["detail"].lower()


# Test valid role access

@pytest.mark.asyncio
async def test_valid_role_header_succeeds(client, user_with_roles):
    """Valid X-Role-Id header for own role should succeed."""
    client.cookies = user_with_roles["cookies"]

    response = await client.get(
        "/api/v1/experience/skills",
        headers={"X-Role-Id": str(user_with_roles["pm_role_id"])}
    )
    # Should return 200 with empty list (no skills yet)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_role_switch_isolates_data(client, user_with_roles):
    """Data created under one role should not appear under another."""
    client.cookies = user_with_roles["cookies"]
    pm_role_id = user_with_roles["pm_role_id"]
    ba_role_id = user_with_roles["ba_role_id"]

    # Create a skill under PM role
    create_response = await client.post(
        "/api/v1/experience/skills",
        json={"name": "Project Management", "category": "Leadership"},
        headers={"X-Role-Id": str(pm_role_id)}
    )
    assert create_response.status_code == 201

    # Verify skill appears under PM role
    pm_skills = await client.get(
        "/api/v1/experience/skills",
        headers={"X-Role-Id": str(pm_role_id)}
    )
    assert len(pm_skills.json()) == 1
    assert pm_skills.json()[0]["name"] == "Project Management"

    # Verify skill does NOT appear under BA role
    ba_skills = await client.get(
        "/api/v1/experience/skills",
        headers={"X-Role-Id": str(ba_role_id)}
    )
    assert len(ba_skills.json()) == 0


# Test unauthenticated access

@pytest.mark.asyncio
async def test_unauthenticated_with_role_header_returns_401(client):
    """X-Role-Id header without authentication should return 401."""
    response = await client.get(
        "/api/v1/experience/skills",
        headers={"X-Role-Id": "1"}
    )
    assert response.status_code == 401
