"""Tests for research approval endpoint (Story 4-7)."""

import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.application import ApplicationStatus


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
        json={"username": "approvaluser", "password": "password123"}
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "approvaluser", "password": "password123"}
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
async def client_with_researched_app(client_with_role):
    """Create client with an application in 'researching' status with research data."""
    client, role_id = client_with_role

    # Create application
    response = await client.post(
        "/api/v1/applications",
        json={
            "company_name": "Acme Corp",
            "job_posting": "We are looking for a software engineer with Python experience."
        }
    )
    app_data = response.json()
    app_id = app_data["id"]

    # Transition: created -> keywords
    await client.patch(
        f"/api/v1/applications/{app_id}/status",
        json={"status": "keywords"}
    )

    # Transition: keywords -> researching
    await client.patch(
        f"/api/v1/applications/{app_id}/status",
        json={"status": "researching"}
    )

    # Add research data
    research_data = json.dumps({
        "strategic_initiatives": {"found": True, "content": "AI-first strategy"},
        "competitive_landscape": {"found": True, "content": "Competing with BigCo"},
        "news_momentum": {"found": False, "reason": "No recent news found"},
        "industry_context": {"found": True, "content": "SaaS industry growing"},
        "culture_values": {"found": True, "content": "Remote-first culture"},
        "leadership_direction": {"found": True, "content": "Expanding into EU"},
        "gaps": ["news_momentum"],
    })
    await client.patch(
        f"/api/v1/applications/{app_id}",
        json={"research_data": research_data}
    )

    return client, role_id, app_id


# ============================================================
# POST /api/v1/applications/{id}/research/approve
# ============================================================


class TestApproveResearch:
    """Test research approval endpoint."""

    @pytest.mark.asyncio
    async def test_approve_research_updates_status(self, client_with_researched_app):
        """Test POST /applications/{id}/research/approve transitions to 'reviewed'."""
        client, role_id, app_id = client_with_researched_app

        response = await client.post(
            f"/api/v1/applications/{app_id}/research/approve"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["application_id"] == app_id
        assert data["status"] == "reviewed"
        assert "approved_at" in data
        assert data["message"] == "Research approved. Ready for document generation."

    @pytest.mark.asyncio
    async def test_approve_research_returns_summary(self, client_with_researched_app):
        """Test approval response includes research summary."""
        client, role_id, app_id = client_with_researched_app

        response = await client.post(
            f"/api/v1/applications/{app_id}/research/approve"
        )
        assert response.status_code == 200

        data = response.json()
        summary = data["research_summary"]
        assert summary["sources_found"] == 5
        assert summary["gaps"] == ["news_momentum"]

    @pytest.mark.asyncio
    async def test_approve_without_research_data_fails(self, client_with_role):
        """Test approval fails when no research data exists."""
        client, role_id = client_with_role

        # Create app and transition to researching but don't add research data
        response = await client.post(
            "/api/v1/applications",
            json={
                "company_name": "Test Corp",
                "job_posting": "Looking for a developer to join our team."
            }
        )
        app_id = response.json()["id"]

        # Transition to researching
        await client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "keywords"}
        )
        await client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "researching"}
        )

        response = await client.post(
            f"/api/v1/applications/{app_id}/research/approve"
        )
        assert response.status_code == 400
        assert "No research data" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_approve_from_wrong_status_fails(self, client_with_role):
        """Test approval fails from non-researching status."""
        client, role_id = client_with_role

        # Create app (status: created)
        response = await client.post(
            "/api/v1/applications",
            json={
                "company_name": "Test Corp",
                "job_posting": "Looking for a developer to join our team."
            }
        )
        app_id = response.json()["id"]

        response = await client.post(
            f"/api/v1/applications/{app_id}/research/approve"
        )
        assert response.status_code == 400
        assert "Cannot approve research from status" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_approve_from_keywords_status_fails(self, client_with_role):
        """Test approval from 'keywords' status fails - research must run first."""
        client, role_id = client_with_role

        response = await client.post(
            "/api/v1/applications",
            json={
                "company_name": "Test Corp",
                "job_posting": "Looking for a developer to join our team."
            }
        )
        app_id = response.json()["id"]

        # Transition to keywords only
        await client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "keywords"}
        )

        response = await client.post(
            f"/api/v1/applications/{app_id}/research/approve"
        )
        assert response.status_code == 400
        assert "Cannot approve research from status" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_double_approval_is_idempotent(self, client_with_researched_app):
        """Test approving twice returns success without error."""
        client, role_id, app_id = client_with_researched_app

        # First approval
        response1 = await client.post(
            f"/api/v1/applications/{app_id}/research/approve"
        )
        assert response1.status_code == 200
        assert response1.json()["status"] == "reviewed"

        # Second approval - should be idempotent
        response2 = await client.post(
            f"/api/v1/applications/{app_id}/research/approve"
        )
        assert response2.status_code == 200
        assert response2.json()["status"] == "reviewed"
        assert response2.json()["message"] == "Research already approved"

    @pytest.mark.asyncio
    async def test_approve_with_gaps_succeeds(self, client_with_researched_app):
        """Test approval succeeds even with research gaps."""
        client, role_id, app_id = client_with_researched_app

        response = await client.post(
            f"/api/v1/applications/{app_id}/research/approve"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "reviewed"
        # Gaps should be listed but not blocking
        assert len(data["research_summary"]["gaps"]) > 0

    @pytest.mark.asyncio
    async def test_approve_nonexistent_application(self, client_with_role):
        """Test approval returns 404 for nonexistent application."""
        client, role_id = client_with_role

        response = await client.post(
            "/api/v1/applications/99999/research/approve"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_approve_requires_auth(self, client):
        """Test approval endpoint requires authentication."""
        response = await client.post(
            "/api/v1/applications/1/research/approve"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_approve_past_reviewed_returns_current(self, client_with_researched_app):
        """Test approval from exported/sent status returns current state."""
        client, role_id, app_id = client_with_researched_app

        # Approve first
        await client.post(
            f"/api/v1/applications/{app_id}/research/approve"
        )

        # Transition to exported
        await client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "exported"}
        )

        # Try to approve again from exported
        response = await client.post(
            f"/api/v1/applications/{app_id}/research/approve"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "exported"
        assert "already past" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_approve_with_manual_context(self, client_with_researched_app):
        """Test approval includes manual context status in summary."""
        client, role_id, app_id = client_with_researched_app

        # Add manual context
        await client.patch(
            f"/api/v1/applications/{app_id}/context",
            json={"manual_context": "The company recently won an award."}
        )

        response = await client.post(
            f"/api/v1/applications/{app_id}/research/approve"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["research_summary"]["has_manual_context"] is True
