"""Cross-layer contract tests for generation API boundaries.

These tests validate the exact JSON shape that the frontend expects.
If either the backend response shape or the frontend interface changes,
these tests MUST break to prevent silent contract drift.

Frontend contracts (from frontend/src/api/generation.ts):
  GenerateResumeResponse: { message: string, resume_content: string, status: string }
  GenerateCoverLetterResponse: { message: string, cover_letter_content: string, status: string }
  GenerationStatusResponse: { generation_status: string, has_resume: boolean, has_cover_letter: boolean }
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.models.keyword import Keyword, KeywordCategory, KeywordList
from app.models.research import ResearchSourceResult


# --- Contract Shape Constants ---
# These mirror the frontend TypeScript interfaces exactly.

RESUME_RESPONSE_FIELDS = {"message", "resume_content", "status"}
COVER_LETTER_RESPONSE_FIELDS = {"message", "cover_letter_content", "status"}
GENERATION_STATUS_FIELDS = {"generation_status", "has_resume", "has_cover_letter"}


@pytest_asyncio.fixture
async def client_with_role(async_client):
    """Authenticated client with role."""
    await async_client.post(
        "/api/v1/auth/register",
        json={"username": "contractgen", "password": "password123"},
    )
    login = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "contractgen", "password": "password123"},
    )
    async_client.cookies = login.cookies

    role_resp = await async_client.post(
        "/api/v1/roles", json={"name": "Contract Gen Role"}
    )
    role_id = role_resp.json()["id"]
    async_client.headers["X-Role-Id"] = str(role_id)
    return async_client, role_id


@pytest_asyncio.fixture
async def reviewed_application(client_with_role):
    """Application in 'reviewed' status ready for generation."""
    client, role_id = client_with_role

    # Add experience data
    await client.post(
        "/api/v1/experience/skills",
        json={"name": "Python", "category": "Languages"},
    )
    await client.post(
        "/api/v1/experience/accomplishments",
        json={"description": "Built API platform", "context": "Acme Corp"},
    )

    # Create application
    resp = await client.post(
        "/api/v1/applications",
        json={
            "company_name": "ContractCorp",
            "job_posting": "Senior Python developer needed.",
        },
    )
    app_id = resp.json()["id"]

    # Extract keywords (mocked)
    mock_keywords = KeywordList(
        keywords=[
            Keyword(text="Python", priority=10, category=KeywordCategory.TECHNICAL_SKILL),
        ]
    )
    with patch(
        "app.services.keyword_service.extract_keywords",
        new_callable=AsyncMock,
        return_value=mock_keywords,
    ):
        await client.post(f"/api/v1/applications/{app_id}/keywords/extract")

    # Research
    await client.patch(
        f"/api/v1/applications/{app_id}/status",
        json={"status": "researching"},
    )

    from app.services.research_service import research_service

    async def mock_cat(cat, cn, jp, cb):
        return ResearchSourceResult(found=True, content=f"Research for {cat.value}")

    async def mock_synth(cn, jp, fr, cb):
        return "Synthesis."

    with patch.object(research_service, "_research_category", mock_cat), \
         patch.object(research_service, "_synthesize_findings", mock_synth), \
         patch.object(research_service._rate_pacer, "pace", AsyncMock()):
        await research_service.start_research(app_id, role_id, "ContractCorp", "Senior Python developer needed.")

    research_service._research_state.clear()
    await client.post(f"/api/v1/applications/{app_id}/research/approve")

    return client, role_id, app_id


class TestResumeGenerationResponseContract:
    """Verify resume generation endpoint response matches frontend contract."""

    @pytest.mark.asyncio
    async def test_resume_response_shape(self, reviewed_application):
        """Response must contain exactly the fields frontend expects."""
        client, role_id, app_id = reviewed_application

        mock_message = MagicMock()
        mock_message.content = "# John Doe\n\njohn@email.com\n\n## Professional Summary\n\nExperienced developer."

        with patch(
            "app.services.generation_service.generate_with_retry",
            new_callable=AsyncMock,
            return_value=mock_message,
        ):
            resp = await client.post(f"/api/v1/applications/{app_id}/generate/resume")

        assert resp.status_code == 200
        data = resp.json()

        # All contract fields present
        for field in RESUME_RESPONSE_FIELDS:
            assert field in data, f"Missing contract field: {field}"

        # Type validation
        assert isinstance(data["message"], str)
        assert isinstance(data["resume_content"], str)
        assert isinstance(data["status"], str)

        # Content validation
        assert len(data["resume_content"]) > 0
        assert data["status"] in ("generating", "complete", "failed")


class TestCoverLetterGenerationResponseContract:
    """Verify cover letter generation endpoint response matches frontend contract."""

    @pytest.mark.asyncio
    async def test_cover_letter_response_shape(self, reviewed_application):
        """Response must contain exactly the fields frontend expects."""
        client, role_id, app_id = reviewed_application

        mock_message = MagicMock()
        mock_message.content = "Dear Hiring Manager,\n\nI am excited about the opportunity."

        with patch(
            "app.services.generation_service.generate_with_retry",
            new_callable=AsyncMock,
            return_value=mock_message,
        ):
            resp = await client.post(
                f"/api/v1/applications/{app_id}/generate/cover-letter",
                json={"tone": "formal"},
            )

        assert resp.status_code == 200
        data = resp.json()

        # All contract fields present
        for field in COVER_LETTER_RESPONSE_FIELDS:
            assert field in data, f"Missing contract field: {field}"

        # Type validation
        assert isinstance(data["message"], str)
        assert isinstance(data["cover_letter_content"], str)
        assert isinstance(data["status"], str)

        # Content validation
        assert len(data["cover_letter_content"]) > 0


class TestGenerationStatusResponseContract:
    """Verify generation status endpoint response matches frontend contract."""

    @pytest.mark.asyncio
    async def test_status_response_shape(self, reviewed_application):
        """Response must contain exactly the fields frontend expects."""
        client, role_id, app_id = reviewed_application

        resp = await client.get(f"/api/v1/applications/{app_id}/generation/status")
        assert resp.status_code == 200
        data = resp.json()

        # All contract fields present
        for field in GENERATION_STATUS_FIELDS:
            assert field in data, f"Missing contract field: {field}"

        # Type validation
        assert isinstance(data["generation_status"], str)
        assert isinstance(data["has_resume"], bool)
        assert isinstance(data["has_cover_letter"], bool)

    @pytest.mark.asyncio
    async def test_status_response_after_resume_generation(self, reviewed_application):
        """After generating a resume, has_resume should be true."""
        client, role_id, app_id = reviewed_application

        mock_message = MagicMock()
        mock_message.content = "# Resume\n\nContent here."

        with patch(
            "app.services.generation_service.generate_with_retry",
            new_callable=AsyncMock,
            return_value=mock_message,
        ):
            await client.post(f"/api/v1/applications/{app_id}/generate/resume")

        resp = await client.get(f"/api/v1/applications/{app_id}/generation/status")
        data = resp.json()

        assert data["has_resume"] is True
        assert data["generation_status"] == "complete"
