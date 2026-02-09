"""Tests for manual context API endpoints (Story 4-6)."""

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
        json={"username": "contextuser", "password": "password123"}
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "contextuser", "password": "password123"}
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
# PATCH /api/v1/applications/{id}/context (AC #3)
# ============================================================

class TestSaveManualContext:
    """Test saving manual context via PATCH endpoint."""

    @pytest.mark.asyncio
    async def test_save_manual_context_success(self, client_with_application):
        """Test PATCH /applications/{id}/context saves context."""
        client, role_id, app_data = client_with_application

        response = await client.patch(
            f"/api/v1/applications/{app_data['id']}/context",
            json={"manual_context": "The company has a great engineering culture."}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["application_id"] == app_data["id"]
        assert data["manual_context"] == "The company has a great engineering culture."
        assert "message" in data

    @pytest.mark.asyncio
    async def test_save_empty_context(self, client_with_application):
        """Test PATCH /applications/{id}/context allows empty string."""
        client, role_id, app_data = client_with_application

        response = await client.patch(
            f"/api/v1/applications/{app_data['id']}/context",
            json={"manual_context": ""}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["manual_context"] == ""

    @pytest.mark.asyncio
    async def test_save_context_trims_whitespace(self, client_with_application):
        """Test context is trimmed of leading/trailing whitespace."""
        client, role_id, app_data = client_with_application

        response = await client.patch(
            f"/api/v1/applications/{app_data['id']}/context",
            json={"manual_context": "  Some context with spaces  "}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["manual_context"] == "Some context with spaces"

    @pytest.mark.asyncio
    async def test_save_context_sanitizes_html(self, client_with_application):
        """Test HTML entities are escaped in context."""
        client, role_id, app_data = client_with_application

        response = await client.patch(
            f"/api/v1/applications/{app_data['id']}/context",
            json={"manual_context": "Good <b>company</b> with &amp; values"}
        )

        assert response.status_code == 200
        data = response.json()
        # HTML should be escaped
        assert "<b>" not in data["manual_context"]
        assert "&lt;b&gt;" in data["manual_context"]

    @pytest.mark.asyncio
    async def test_save_context_escapes_script_tags(self, client_with_application):
        """Test context escapes script tags via html.escape()."""
        client, role_id, app_data = client_with_application

        response = await client.patch(
            f"/api/v1/applications/{app_data['id']}/context",
            json={"manual_context": "<script>alert('xss')</script>"}
        )

        assert response.status_code == 200
        data = response.json()
        # Script tags should be HTML-escaped, not rejected
        assert "<script>" not in data["manual_context"]
        assert "&lt;script&gt;" in data["manual_context"]

    @pytest.mark.asyncio
    async def test_save_context_escapes_javascript_uri(self, client_with_application):
        """Test context containing javascript: is escaped, not rejected."""
        client, role_id, app_data = client_with_application

        response = await client.patch(
            f"/api/v1/applications/{app_data['id']}/context",
            json={"manual_context": "javascript:alert(1)"}
        )

        # Content is accepted and stored (html.escape handles safety)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_save_context_max_length(self, client_with_application):
        """Test context enforces 5000 character max length."""
        client, role_id, app_data = client_with_application

        response = await client.patch(
            f"/api/v1/applications/{app_data['id']}/context",
            json={"manual_context": "x" * 5001}
        )

        assert response.status_code == 422  # Pydantic validation

    @pytest.mark.asyncio
    async def test_save_context_at_max_length(self, client_with_application):
        """Test context accepts exactly 5000 characters."""
        client, role_id, app_data = client_with_application

        response = await client.patch(
            f"/api/v1/applications/{app_data['id']}/context",
            json={"manual_context": "x" * 5000}
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_save_context_not_found(self, client_with_role):
        """Test PATCH /applications/{id}/context returns 404 for nonexistent app."""
        client, role_id = client_with_role

        response = await client.patch(
            "/api/v1/applications/99999/context",
            json={"manual_context": "Some context"}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_save_context_requires_auth(self, client):
        """Test endpoint requires authentication."""
        response = await client.patch(
            "/api/v1/applications/1/context",
            json={"manual_context": "Some context"}
        )

        assert response.status_code == 401


# ============================================================
# GET /api/v1/applications/{id}/context (AC #5)
# ============================================================

class TestGetManualContext:
    """Test retrieving manual context via GET endpoint."""

    @pytest.mark.asyncio
    async def test_get_context_empty(self, client_with_application):
        """Test GET /applications/{id}/context returns empty when no context set."""
        client, role_id, app_data = client_with_application

        response = await client.get(
            f"/api/v1/applications/{app_data['id']}/context"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["application_id"] == app_data["id"]
        assert data["manual_context"] == ""
        assert isinstance(data["gaps"], list)

    @pytest.mark.asyncio
    async def test_get_context_after_save(self, client_with_application):
        """Test GET /applications/{id}/context returns saved context."""
        client, role_id, app_data = client_with_application

        # Save context first
        await client.patch(
            f"/api/v1/applications/{app_data['id']}/context",
            json={"manual_context": "Insider knowledge about the company."}
        )

        # Retrieve it
        response = await client.get(
            f"/api/v1/applications/{app_data['id']}/context"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["manual_context"] == "Insider knowledge about the company."

    @pytest.mark.asyncio
    async def test_get_context_not_found(self, client_with_role):
        """Test GET /applications/{id}/context returns 404 for nonexistent app."""
        client, role_id = client_with_role

        response = await client.get(
            "/api/v1/applications/99999/context"
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_context_returns_gaps(self, client_with_application):
        """Test GET /applications/{id}/context returns gaps from research_data."""
        client, role_id, app_data = client_with_application
        import json

        # Set research_data with gaps
        research_data = json.dumps({
            "gaps": ["strategic_initiatives", "competitive_landscape"],
            "synthesis": "Test synthesis"
        })
        await client.patch(
            f"/api/v1/applications/{app_data['id']}",
            json={"research_data": research_data}
        )

        response = await client.get(
            f"/api/v1/applications/{app_data['id']}/context"
        )

        assert response.status_code == 200
        data = response.json()
        assert "strategic_initiatives" in data["gaps"]
        assert "competitive_landscape" in data["gaps"]


# ============================================================
# Role Isolation Tests (AC #3)
# ============================================================

class TestManualContextRoleIsolation:
    """Test that manual context endpoints respect role isolation."""

    @pytest.mark.asyncio
    async def test_cannot_save_context_for_other_roles_app(self, client):
        """Test PATCH /applications/{id}/context is role-isolated."""
        # Create first user with role and application
        await client.post(
            "/api/v1/auth/register",
            json={"username": "ctxuser1", "password": "password123"}
        )
        login1 = await client.post(
            "/api/v1/auth/login",
            json={"username": "ctxuser1", "password": "password123"}
        )
        client.cookies = login1.cookies

        role1_resp = await client.post(
            "/api/v1/roles",
            json={"name": "Role 1"}
        )
        role1_id = role1_resp.json()["id"]
        client.headers["X-Role-Id"] = str(role1_id)

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
            json={"username": "ctxuser2", "password": "password123"}
        )
        login2 = await client.post(
            "/api/v1/auth/login",
            json={"username": "ctxuser2", "password": "password123"}
        )
        client.cookies = login2.cookies

        role2_resp = await client.post(
            "/api/v1/roles",
            json={"name": "Role 2"}
        )
        role2_id = role2_resp.json()["id"]
        client.headers["X-Role-Id"] = str(role2_id)

        # Try to save context on role 1's application via role 2 - should 404
        response = await client.patch(
            f"/api/v1/applications/{app_id}/context",
            json={"manual_context": "Shouldn't work"}
        )
        assert response.status_code == 404

        # Try to get context on role 1's application via role 2 - should 404
        response = await client.get(
            f"/api/v1/applications/{app_id}/context"
        )
        assert response.status_code == 404


# ============================================================
# Application Read Includes manual_context (AC #5)
# ============================================================

class TestApplicationReadIncludesContext:
    """Test that GET /applications/{id} includes manual_context field."""

    @pytest.mark.asyncio
    async def test_application_read_has_manual_context(self, client_with_application):
        """Test application response includes manual_context field."""
        client, role_id, app_data = client_with_application

        # Save some context
        await client.patch(
            f"/api/v1/applications/{app_data['id']}/context",
            json={"manual_context": "Important context."}
        )

        # Get the full application
        response = await client.get(
            f"/api/v1/applications/{app_data['id']}"
        )

        assert response.status_code == 200
        data = response.json()
        assert "manual_context" in data
        assert data["manual_context"] == "Important context."


# ============================================================
# Sanitization Bypass Prevention (H2 fix)
# ============================================================

class TestManualContextSanitizationBypass:
    """Test that general PATCH endpoint cannot write manual_context directly."""

    @pytest.mark.asyncio
    async def test_general_patch_ignores_manual_context(self, client_with_application):
        """Test PATCH /applications/{id} ignores manual_context field.

        manual_context was removed from ApplicationUpdate to force all writes
        through the dedicated /context endpoint which applies HTML sanitization.
        """
        client, role_id, app_data = client_with_application

        # Try to set manual_context via general update endpoint
        response = await client.patch(
            f"/api/v1/applications/{app_data['id']}",
            json={"manual_context": "<script>unsanitized</script>"}
        )

        assert response.status_code == 200

        # Verify manual_context was NOT written
        get_response = await client.get(
            f"/api/v1/applications/{app_data['id']}/context"
        )
        assert get_response.json()["manual_context"] == ""
