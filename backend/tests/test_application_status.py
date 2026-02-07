"""Tests for application status update endpoint."""

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
    """Create client with authenticated session."""
    await client.post(
        "/api/v1/auth/register",
        json={"username": "statususer", "password": "password123"}
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "statususer", "password": "password123"}
    )
    client.cookies = login_response.cookies
    return client


@pytest_asyncio.fixture
async def client_with_role(authenticated_client):
    """Create authenticated client with a role and role header."""
    role_response = await authenticated_client.post(
        "/api/v1/roles",
        json={"name": "Test Engineer"}
    )
    role_id = role_response.json()["id"]
    authenticated_client.headers["X-Role-Id"] = str(role_id)
    return authenticated_client, role_id


@pytest_asyncio.fixture
async def client_with_application(client_with_role):
    """Create client with a role that has an application."""
    client, role_id = client_with_role
    response = await client.post(
        "/api/v1/applications",
        json={
            "company_name": "Status Test Corp",
            "job_posting": "We need a developer with experience in testing and status management."
        }
    )
    app_data = response.json()
    return client, role_id, app_data


@pytest.mark.asyncio
async def test_status_update_returns_200(client_with_application):
    """Test that status update endpoint returns 200."""
    client, role_id, app_data = client_with_application

    response = await client.patch(
        f"/api/v1/applications/{app_data['id']}/status",
        json={"status": "keywords"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "keywords"


@pytest.mark.asyncio
async def test_status_update_changes_updated_at(client_with_application):
    """Test that status update changes the updated_at timestamp."""
    client, role_id, app_data = client_with_application
    original_updated_at = app_data["updated_at"]

    response = await client.patch(
        f"/api/v1/applications/{app_data['id']}/status",
        json={"status": "keywords"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "keywords"
    assert response.json()["updated_at"] != original_updated_at


@pytest.mark.asyncio
async def test_status_update_invalid_status(client_with_application):
    """Test that invalid status returns 422."""
    client, role_id, app_data = client_with_application

    response = await client.patch(
        f"/api/v1/applications/{app_data['id']}/status",
        json={"status": "nonexistent"}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_status_update_nonexistent_application(client_with_role):
    """Test that updating nonexistent application returns 404."""
    client, role_id = client_with_role

    response = await client.patch(
        "/api/v1/applications/99999/status",
        json={"status": "keywords"}
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_status_update_preserves_other_fields(client_with_application):
    """Test that status update does not alter other fields."""
    client, role_id, app_data = client_with_application

    response = await client.patch(
        f"/api/v1/applications/{app_data['id']}/status",
        json={"status": "keywords"}
    )

    result = response.json()
    assert result["company_name"] == app_data["company_name"]
    assert result["job_posting"] == app_data["job_posting"]


@pytest.mark.asyncio
async def test_status_update_requires_auth(client):
    """Test that status update requires authentication."""
    response = await client.patch(
        "/api/v1/applications/1/status",
        json={"status": "keywords"}
    )

    # Should return 401 or 403 without auth
    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_status_update_rejects_invalid_transition(client_with_application):
    """Test that invalid status transitions are rejected (e.g., created -> sent)."""
    client, role_id, app_data = client_with_application

    response = await client.patch(
        f"/api/v1/applications/{app_data['id']}/status",
        json={"status": "sent"}
    )

    assert response.status_code == 422
    assert "Invalid transition" in response.json()["detail"]


@pytest.mark.asyncio
async def test_status_update_allows_valid_sequential_transition(client_with_application):
    """Test that valid sequential transitions work (created -> keywords -> researching)."""
    client, role_id, app_data = client_with_application

    # created -> keywords
    response = await client.patch(
        f"/api/v1/applications/{app_data['id']}/status",
        json={"status": "keywords"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "keywords"

    # keywords -> researching
    response = await client.patch(
        f"/api/v1/applications/{app_data['id']}/status",
        json={"status": "researching"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "researching"
