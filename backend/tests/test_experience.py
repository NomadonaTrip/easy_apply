"""Tests for experience endpoints."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


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
    """Create client with authenticated session and a role."""
    # Register and login
    await client.post(
        "/api/v1/auth/register",
        json={"username": "expuser", "password": "password123"}
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "expuser", "password": "password123"}
    )
    client.cookies = login_response.cookies
    return client


@pytest_asyncio.fixture
async def client_with_role(authenticated_client):
    """Create authenticated client with a role and role header."""
    # Create a role
    role_response = await authenticated_client.post(
        "/api/v1/roles",
        json={"name": "Software Engineer"}
    )
    role_id = role_response.json()["id"]

    # Add role header to all subsequent requests
    authenticated_client.headers["X-Role-Id"] = str(role_id)
    return authenticated_client, role_id


@pytest_asyncio.fixture
async def client_with_data(client_with_role):
    """Create client with role that has skills and accomplishments."""
    client, role_id = client_with_role

    # Create skills
    await client.post(
        "/api/v1/experience/skills",
        json={"name": "Python", "category": "Programming"}
    )
    await client.post(
        "/api/v1/experience/skills",
        json={"name": "FastAPI", "category": "Programming"}
    )
    await client.post(
        "/api/v1/experience/skills",
        json={"name": "React", "category": "Frontend"}
    )
    await client.post(
        "/api/v1/experience/skills",
        json={"name": "Leadership", "category": None}
    )

    # Create accomplishments
    await client.post(
        "/api/v1/experience/accomplishments",
        json={"description": "Led team of 5 developers", "context": "Tech Lead", "source": "resume"}
    )
    await client.post(
        "/api/v1/experience/accomplishments",
        json={"description": "Reduced deployment time by 50%", "source": "application"}
    )

    return client, role_id


# Test GET /api/v1/experience (AC #1, #2)

@pytest.mark.asyncio
async def test_get_experience_returns_skills_and_accomplishments(client_with_data):
    """Test GET /experience returns combined skills and accomplishments."""
    client, role_id = client_with_data

    response = await client.get("/api/v1/experience")
    assert response.status_code == 200

    data = response.json()
    assert "skills" in data
    assert "accomplishments" in data
    assert "skills_count" in data
    assert "accomplishments_count" in data

    assert data["skills_count"] == 4
    assert data["accomplishments_count"] == 2
    assert len(data["skills"]) == 4
    assert len(data["accomplishments"]) == 2


@pytest.mark.asyncio
async def test_get_experience_empty_when_no_data(client_with_role):
    """Test GET /experience returns empty lists when no data exists."""
    client, role_id = client_with_role

    response = await client.get("/api/v1/experience")
    assert response.status_code == 200

    data = response.json()
    assert data["skills"] == []
    assert data["accomplishments"] == []
    assert data["skills_count"] == 0
    assert data["accomplishments_count"] == 0


# Test GET /api/v1/experience/skills (AC #1)

@pytest.mark.asyncio
async def test_get_skills_returns_list(client_with_data):
    """Test GET /experience/skills returns list of skills."""
    client, role_id = client_with_data

    response = await client.get("/api/v1/experience/skills")
    assert response.status_code == 200

    skills = response.json()
    assert len(skills) == 4
    skill_names = [s["name"] for s in skills]
    assert "Python" in skill_names
    assert "FastAPI" in skill_names


@pytest.mark.asyncio
async def test_get_skills_empty(client_with_role):
    """Test GET /experience/skills returns empty list when no skills."""
    client, role_id = client_with_role

    response = await client.get("/api/v1/experience/skills")
    assert response.status_code == 200
    assert response.json() == []


# Test GET /api/v1/experience/accomplishments (AC #2)

@pytest.mark.asyncio
async def test_get_accomplishments_returns_list(client_with_data):
    """Test GET /experience/accomplishments returns list of accomplishments."""
    client, role_id = client_with_data

    response = await client.get("/api/v1/experience/accomplishments")
    assert response.status_code == 200

    accomplishments = response.json()
    assert len(accomplishments) == 2
    descriptions = [a["description"] for a in accomplishments]
    assert "Led team of 5 developers" in descriptions


@pytest.mark.asyncio
async def test_get_accomplishments_empty(client_with_role):
    """Test GET /experience/accomplishments returns empty list when no accomplishments."""
    client, role_id = client_with_role

    response = await client.get("/api/v1/experience/accomplishments")
    assert response.status_code == 200
    assert response.json() == []


# Test GET /api/v1/experience/stats (AC #4)

@pytest.mark.asyncio
async def test_get_experience_stats(client_with_data):
    """Test GET /experience/stats returns correct statistics."""
    client, role_id = client_with_data

    response = await client.get("/api/v1/experience/stats")
    assert response.status_code == 200

    stats = response.json()
    assert stats["total_skills"] == 4
    assert stats["total_accomplishments"] == 2
    assert "skills_by_category" in stats

    # Check category grouping
    categories = stats["skills_by_category"]
    assert categories["Programming"] == 2
    assert categories["Frontend"] == 1
    assert categories["Uncategorized"] == 1


@pytest.mark.asyncio
async def test_get_experience_stats_empty(client_with_role):
    """Test GET /experience/stats returns zeros when no data."""
    client, role_id = client_with_role

    response = await client.get("/api/v1/experience/stats")
    assert response.status_code == 200

    stats = response.json()
    assert stats["total_skills"] == 0
    assert stats["total_accomplishments"] == 0
    assert stats["skills_by_category"] == {}


# Test Role Isolation (AC #3)

@pytest.mark.asyncio
async def test_experience_role_isolation(client):
    """Test that experience data is isolated between roles."""
    # Create first user with role and data
    await client.post(
        "/api/v1/auth/register",
        json={"username": "user1", "password": "password123"}
    )
    login1 = await client.post(
        "/api/v1/auth/login",
        json={"username": "user1", "password": "password123"}
    )
    client.cookies = login1.cookies

    # Create role for user1
    role1_response = await client.post(
        "/api/v1/roles",
        json={"name": "Role 1"}
    )
    role1_id = role1_response.json()["id"]
    client.headers["X-Role-Id"] = str(role1_id)

    # Add skills for user1/role1
    await client.post(
        "/api/v1/experience/skills",
        json={"name": "User1 Skill", "category": "Test"}
    )

    # Create second user with different role
    await client.post(
        "/api/v1/auth/register",
        json={"username": "user2", "password": "password123"}
    )
    login2 = await client.post(
        "/api/v1/auth/login",
        json={"username": "user2", "password": "password123"}
    )
    client.cookies = login2.cookies

    # Create role for user2
    role2_response = await client.post(
        "/api/v1/roles",
        json={"name": "Role 2"}
    )
    role2_id = role2_response.json()["id"]
    client.headers["X-Role-Id"] = str(role2_id)

    # Add skills for user2/role2
    await client.post(
        "/api/v1/experience/skills",
        json={"name": "User2 Skill", "category": "Test"}
    )

    # Get experience for user2/role2 - should only see their data
    response = await client.get("/api/v1/experience")
    assert response.status_code == 200

    data = response.json()
    assert data["skills_count"] == 1
    skill_names = [s["name"] for s in data["skills"]]
    assert "User2 Skill" in skill_names
    assert "User1 Skill" not in skill_names


# Test Authentication Required

@pytest.mark.asyncio
async def test_experience_requires_auth(client):
    """Test that experience endpoints require authentication."""
    response = await client.get("/api/v1/experience")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_experience_requires_role_header(authenticated_client):
    """Test that experience endpoints require X-Role-Id header."""
    response = await authenticated_client.get("/api/v1/experience")
    assert response.status_code == 400
    assert "X-Role-Id" in response.json()["detail"]
