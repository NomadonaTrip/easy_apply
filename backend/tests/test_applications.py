"""Tests for application model and API endpoints."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.application import Application, ApplicationStatus


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
        json={"username": "appuser", "password": "password123"}
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "appuser", "password": "password123"}
    )
    client.cookies = login_response.cookies
    return client


@pytest_asyncio.fixture
async def client_with_role(authenticated_client):
    """Create authenticated client with a role and role header."""
    role_response = await authenticated_client.post(
        "/api/v1/roles",
        json={"name": "Software Engineer"}
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
            "company_name": "Acme Corp",
            "job_posting": "We are looking for a software engineer with Python experience."
        }
    )
    app_data = response.json()
    return client, role_id, app_data


# ============================================================
# Model Tests (AC #1)
# ============================================================

class TestApplicationModel:
    """Test Application model fields and validation."""

    def test_application_status_enum_values(self):
        """Test ApplicationStatus enum has all workflow states."""
        expected = [
            "created", "keywords", "researching", "reviewed",
            "exported", "sent", "callback", "offer", "closed"
        ]
        actual = [s.value for s in ApplicationStatus]
        assert actual == expected

    def test_application_model_requires_company_name(self):
        """Test Application model rejects empty company_name."""
        with pytest.raises(ValueError, match="company_name"):
            Application(
                role_id=1,
                company_name="",
                job_posting="Some job description here"
            )

    def test_application_model_requires_job_posting(self):
        """Test Application model rejects empty job_posting."""
        with pytest.raises(ValueError, match="job_posting"):
            Application(
                role_id=1,
                company_name="Acme",
                job_posting=""
            )

    def test_application_model_default_status(self):
        """Test Application model defaults to CREATED status."""
        app_obj = Application(
            role_id=1,
            company_name="Acme Corp",
            job_posting="Looking for developer"
        )
        assert app_obj.status == ApplicationStatus.CREATED

    def test_application_model_timestamps(self):
        """Test Application model sets created_at and updated_at."""
        app_obj = Application(
            role_id=1,
            company_name="Acme Corp",
            job_posting="Looking for developer"
        )
        assert app_obj.created_at is not None
        assert app_obj.updated_at is not None


# ============================================================
# POST /api/v1/applications (AC #3)
# ============================================================

class TestCreateApplication:
    """Test creating applications via API."""

    @pytest.mark.asyncio
    async def test_create_application_success(self, client_with_role):
        """Test POST /applications creates application with status 'created'."""
        client, role_id = client_with_role

        response = await client.post(
            "/api/v1/applications",
            json={
                "company_name": "Acme Corp",
                "job_posting": "We are looking for a software engineer with Python experience.",
                "job_url": "https://acme.com/jobs/123"
            }
        )
        assert response.status_code == 201

        data = response.json()
        assert data["company_name"] == "Acme Corp"
        assert data["job_posting"] == "We are looking for a software engineer with Python experience."
        assert data["job_url"] == "https://acme.com/jobs/123"
        assert data["status"] == "created"
        assert data["role_id"] == role_id
        assert data["id"] is not None
        assert data["created_at"] is not None
        assert data["updated_at"] is not None
        assert data["keywords"] is None
        assert data["research_data"] is None
        assert data["resume_content"] is None
        assert data["cover_letter_content"] is None

    @pytest.mark.asyncio
    async def test_create_application_minimal(self, client_with_role):
        """Test POST /applications with only required fields."""
        client, role_id = client_with_role

        response = await client.post(
            "/api/v1/applications",
            json={
                "company_name": "Test Corp",
                "job_posting": "Looking for a developer to join our team."
            }
        )
        assert response.status_code == 201

        data = response.json()
        assert data["company_name"] == "Test Corp"
        assert data["job_url"] is None

    @pytest.mark.asyncio
    async def test_create_application_validation_empty_company(self, client_with_role):
        """Test POST /applications rejects empty company_name."""
        client, role_id = client_with_role

        response = await client.post(
            "/api/v1/applications",
            json={
                "company_name": "",
                "job_posting": "Some job description here."
            }
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_application_validation_short_posting(self, client_with_role):
        """Test POST /applications rejects too-short job_posting."""
        client, role_id = client_with_role

        response = await client.post(
            "/api/v1/applications",
            json={
                "company_name": "Test Corp",
                "job_posting": "Short"
            }
        )
        assert response.status_code == 422


# ============================================================
# GET /api/v1/applications (AC #2)
# ============================================================

class TestListApplications:
    """Test listing applications via API."""

    @pytest.mark.asyncio
    async def test_list_applications_empty(self, client_with_role):
        """Test GET /applications returns empty list initially."""
        client, role_id = client_with_role

        response = await client.get("/api/v1/applications")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_applications_returns_all(self, client_with_role):
        """Test GET /applications returns all applications for role."""
        client, role_id = client_with_role

        # Create two applications
        await client.post(
            "/api/v1/applications",
            json={"company_name": "Corp A", "job_posting": "Job description A with enough text."}
        )
        await client.post(
            "/api/v1/applications",
            json={"company_name": "Corp B", "job_posting": "Job description B with enough text."}
        )

        response = await client.get("/api/v1/applications")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2
        names = [d["company_name"] for d in data]
        assert "Corp A" in names
        assert "Corp B" in names


# ============================================================
# GET /api/v1/applications/{id} (AC #4)
# ============================================================

class TestGetApplication:
    """Test getting single application via API."""

    @pytest.mark.asyncio
    async def test_get_application_success(self, client_with_application):
        """Test GET /applications/{id} returns single application."""
        client, role_id, app_data = client_with_application

        response = await client.get(f"/api/v1/applications/{app_data['id']}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == app_data["id"]
        assert data["company_name"] == "Acme Corp"

    @pytest.mark.asyncio
    async def test_get_application_not_found(self, client_with_role):
        """Test GET /applications/{id} returns 404 for nonexistent."""
        client, role_id = client_with_role

        response = await client.get("/api/v1/applications/99999")
        assert response.status_code == 404


# ============================================================
# PATCH /api/v1/applications/{id} (AC #5)
# ============================================================

class TestUpdateApplication:
    """Test updating applications via API."""

    @pytest.mark.asyncio
    async def test_update_application_status(self, client_with_application):
        """Test PATCH /applications/{id} updates status."""
        client, role_id, app_data = client_with_application

        response = await client.patch(
            f"/api/v1/applications/{app_data['id']}",
            json={"status": "keywords"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "keywords"

    @pytest.mark.asyncio
    async def test_update_application_keywords(self, client_with_application):
        """Test PATCH /applications/{id} updates keywords."""
        client, role_id, app_data = client_with_application
        import json

        keywords_json = json.dumps(["python", "fastapi", "react"])
        response = await client.patch(
            f"/api/v1/applications/{app_data['id']}",
            json={"keywords": keywords_json}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["keywords"] == keywords_json

    @pytest.mark.asyncio
    async def test_update_application_not_found(self, client_with_role):
        """Test PATCH /applications/{id} returns 404 for nonexistent."""
        client, role_id = client_with_role

        response = await client.patch(
            "/api/v1/applications/99999",
            json={"status": "keywords"}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_application_updated_at_changes(self, client_with_application):
        """Test PATCH /applications/{id} updates updated_at timestamp."""
        import asyncio

        client, role_id, app_data = client_with_application
        original_updated_at = app_data["updated_at"]

        # Ensure time ticks forward
        await asyncio.sleep(0.01)

        response = await client.patch(
            f"/api/v1/applications/{app_data['id']}",
            json={"company_name": "Updated Corp"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["company_name"] == "Updated Corp"
        assert data["updated_at"] != original_updated_at

    @pytest.mark.asyncio
    async def test_update_application_invalid_status(self, client_with_application):
        """Test PATCH /applications/{id} rejects invalid status value."""
        client, role_id, app_data = client_with_application

        response = await client.patch(
            f"/api/v1/applications/{app_data['id']}",
            json={"status": "bogus"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_application_empty_body(self, client_with_application):
        """Test PATCH /applications/{id} with empty body succeeds without changes."""
        client, role_id, app_data = client_with_application

        response = await client.patch(
            f"/api/v1/applications/{app_data['id']}",
            json={}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["company_name"] == app_data["company_name"]
        assert data["status"] == app_data["status"]


# ============================================================
# Role Isolation Tests (AC #6)
# ============================================================

class TestApplicationRoleIsolation:
    """Test that applications are scoped to roles."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_roles_applications(self, client):
        """Test applications are isolated between roles."""
        # Create first user with role
        await client.post(
            "/api/v1/auth/register",
            json={"username": "appuser1", "password": "password123"}
        )
        login1 = await client.post(
            "/api/v1/auth/login",
            json={"username": "appuser1", "password": "password123"}
        )
        client.cookies = login1.cookies

        role1_resp = await client.post(
            "/api/v1/roles",
            json={"name": "Role 1"}
        )
        role1_id = role1_resp.json()["id"]
        client.headers["X-Role-Id"] = str(role1_id)

        # Create application for role 1
        create_resp = await client.post(
            "/api/v1/applications",
            json={
                "company_name": "Role1 Company",
                "job_posting": "Job for role 1 with enough description text."
            }
        )
        app_id = create_resp.json()["id"]

        # Create second user with different role
        await client.post(
            "/api/v1/auth/register",
            json={"username": "appuser2", "password": "password123"}
        )
        login2 = await client.post(
            "/api/v1/auth/login",
            json={"username": "appuser2", "password": "password123"}
        )
        client.cookies = login2.cookies

        role2_resp = await client.post(
            "/api/v1/roles",
            json={"name": "Role 2"}
        )
        role2_id = role2_resp.json()["id"]
        client.headers["X-Role-Id"] = str(role2_id)

        # List applications for role 2 - should be empty
        response = await client.get("/api/v1/applications")
        assert response.status_code == 200
        assert response.json() == []

        # Try to get role 1's application via role 2 - should be 404
        response = await client.get(f"/api/v1/applications/{app_id}")
        assert response.status_code == 404

        # Try to update role 1's application via role 2 - should be 404
        response = await client.patch(
            f"/api/v1/applications/{app_id}",
            json={"status": "keywords"}
        )
        assert response.status_code == 404


# ============================================================
# Auth Tests
# ============================================================

class TestApplicationAuth:
    """Test authentication requirements."""

    @pytest.mark.asyncio
    async def test_applications_require_auth(self, client):
        """Test that application endpoints require authentication."""
        response = await client.get("/api/v1/applications")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_applications_require_role_header(self, authenticated_client):
        """Test that application endpoints require X-Role-Id header."""
        response = await authenticated_client.get("/api/v1/applications")
        assert response.status_code == 400
        assert "X-Role-Id" in response.json()["detail"]
