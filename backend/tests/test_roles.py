"""Tests for role endpoints."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
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


@pytest_asyncio.fixture
async def authenticated_client(client):
    """Create client with authenticated session."""
    # Register and login
    await client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "password123"}
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "password123"}
    )
    # Return client with session cookie
    client.cookies = login_response.cookies
    return client


# Test Role Model Creation (AC #1)

@pytest.mark.asyncio
async def test_role_table_exists(authenticated_client):
    """Test that Role table exists and has correct structure."""
    # Create a role - if table doesn't exist, this will fail
    response = await authenticated_client.post(
        "/api/v1/roles",
        json={"name": "Product Manager"}
    )
    assert response.status_code == 201
    data = response.json()
    # Verify all expected fields are present
    assert "id" in data
    assert "user_id" in data
    assert "name" in data
    assert "created_at" in data


# Test GET /api/v1/roles (AC #2)

@pytest.mark.asyncio
async def test_list_roles_returns_user_roles(authenticated_client):
    """Test GET /api/v1/roles returns all roles for current user."""
    # Create some roles
    await authenticated_client.post("/api/v1/roles", json={"name": "PM"})
    await authenticated_client.post("/api/v1/roles", json={"name": "BA"})

    response = await authenticated_client.get("/api/v1/roles")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    names = [r["name"] for r in data]
    assert "PM" in names
    assert "BA" in names


@pytest.mark.asyncio
async def test_list_roles_empty(authenticated_client):
    """Test GET /api/v1/roles returns empty list when no roles exist."""
    response = await authenticated_client.get("/api/v1/roles")
    assert response.status_code == 200
    assert response.json() == []


# Test POST /api/v1/roles (AC #3)

@pytest.mark.asyncio
async def test_create_role_success(authenticated_client):
    """Test creating a role with valid data."""
    response = await authenticated_client.post(
        "/api/v1/roles",
        json={"name": "Product Manager"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Product Manager"
    assert "id" in data
    assert "user_id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_role_validation_empty_name(authenticated_client):
    """Test role creation with empty name returns 422."""
    response = await authenticated_client.post(
        "/api/v1/roles",
        json={"name": ""}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_role_validation_name_too_long(authenticated_client):
    """Test role creation with name > 100 chars returns 422."""
    long_name = "x" * 101
    response = await authenticated_client.post(
        "/api/v1/roles",
        json={"name": long_name}
    )
    assert response.status_code == 422


# Test GET /api/v1/roles/{id}

@pytest.mark.asyncio
async def test_get_role_by_id(authenticated_client):
    """Test getting a single role by ID."""
    create_response = await authenticated_client.post(
        "/api/v1/roles",
        json={"name": "Test Role"}
    )
    role_id = create_response.json()["id"]

    response = await authenticated_client.get(f"/api/v1/roles/{role_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Role"


@pytest.mark.asyncio
async def test_get_role_not_found(authenticated_client):
    """Test 404 for non-existent role."""
    response = await authenticated_client.get("/api/v1/roles/99999")
    assert response.status_code == 404


# Test DELETE /api/v1/roles/{id} (AC #4)

@pytest.mark.asyncio
async def test_delete_role_success(authenticated_client):
    """Test deleting a role."""
    create_response = await authenticated_client.post(
        "/api/v1/roles",
        json={"name": "To Delete"}
    )
    role_id = create_response.json()["id"]

    delete_response = await authenticated_client.delete(f"/api/v1/roles/{role_id}")
    assert delete_response.status_code == 204

    # Verify deleted
    get_response = await authenticated_client.get(f"/api/v1/roles/{role_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_role_not_found(authenticated_client):
    """Test 404 when deleting non-existent role."""
    response = await authenticated_client.delete("/api/v1/roles/99999")
    assert response.status_code == 404


# Test Ownership Enforcement (AC #5)

@pytest.mark.asyncio
async def test_role_ownership_403_on_get(client):
    """Test that users cannot access other users' roles."""
    # Create first user and role
    await client.post(
        "/api/v1/auth/register",
        json={"username": "user1", "password": "password123"}
    )
    login1 = await client.post(
        "/api/v1/auth/login",
        json={"username": "user1", "password": "password123"}
    )
    client.cookies = login1.cookies

    create_response = await client.post(
        "/api/v1/roles",
        json={"name": "User1 Role"}
    )
    role_id = create_response.json()["id"]

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

    # Try to access user1's role
    response = await client.get(f"/api/v1/roles/{role_id}")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_role_ownership_403_on_delete(client):
    """Test that users cannot delete other users' roles."""
    # Create first user and role
    await client.post(
        "/api/v1/auth/register",
        json={"username": "owner", "password": "password123"}
    )
    login1 = await client.post(
        "/api/v1/auth/login",
        json={"username": "owner", "password": "password123"}
    )
    client.cookies = login1.cookies

    create_response = await client.post(
        "/api/v1/roles",
        json={"name": "Owner Role"}
    )
    role_id = create_response.json()["id"]

    # Create second user
    await client.post(
        "/api/v1/auth/register",
        json={"username": "attacker", "password": "password123"}
    )
    login2 = await client.post(
        "/api/v1/auth/login",
        json={"username": "attacker", "password": "password123"}
    )
    client.cookies = login2.cookies

    # Try to delete owner's role as attacker - should get 403
    response = await client.delete(f"/api/v1/roles/{role_id}")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_roles_shows_only_own_roles(client):
    """Test that listing roles only shows current user's roles."""
    # Create first user and roles
    await client.post(
        "/api/v1/auth/register",
        json={"username": "userA", "password": "password123"}
    )
    loginA = await client.post(
        "/api/v1/auth/login",
        json={"username": "userA", "password": "password123"}
    )
    client.cookies = loginA.cookies

    await client.post("/api/v1/roles", json={"name": "Role A1"})
    await client.post("/api/v1/roles", json={"name": "Role A2"})

    # Create second user and roles
    await client.post(
        "/api/v1/auth/register",
        json={"username": "userB", "password": "password123"}
    )
    loginB = await client.post(
        "/api/v1/auth/login",
        json={"username": "userB", "password": "password123"}
    )
    client.cookies = loginB.cookies

    await client.post("/api/v1/roles", json={"name": "Role B1"})

    # List roles - should only see userB's roles
    response = await client.get("/api/v1/roles")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Role B1"


# Test Authentication Required

@pytest.mark.asyncio
async def test_roles_require_auth(client):
    """Test that role endpoints require authentication."""
    response = await client.get("/api/v1/roles")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_role_requires_auth(client):
    """Test that creating a role requires authentication."""
    response = await client.post(
        "/api/v1/roles",
        json={"name": "Unauthorized"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_role_requires_auth(client):
    """Test that deleting a role requires authentication."""
    response = await client.delete("/api/v1/roles/1")
    assert response.status_code == 401


# Test Cascade Delete (Task 1a)

@pytest.mark.asyncio
async def test_user_delete_cascades_to_roles():
    """Test that deleting a user cascades to delete their roles."""
    from app.models.role import Role

    # Create user and roles directly in database
    async with async_session_maker() as session:
        # First create the user
        from app.models.user import User
        user = User(
            username="cascadetest",
            password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # bcrypt hash
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

        # Create roles for this user
        role1 = Role(user_id=user_id, name="Role 1")
        role2 = Role(user_id=user_id, name="Role 2")
        session.add(role1)
        session.add(role2)
        await session.commit()

        # Verify roles exist
        result = await session.execute(
            select(Role).where(Role.user_id == user_id)
        )
        roles = result.scalars().all()
        assert len(roles) == 2

        # Delete the user
        await session.delete(user)
        await session.commit()

        # Verify roles were cascade deleted
        result = await session.execute(
            select(Role).where(Role.user_id == user_id)
        )
        roles = result.scalars().all()
        assert len(roles) == 0
