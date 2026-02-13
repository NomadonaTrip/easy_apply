"""Tests for Story 5-1: Generation Service.

Covers:
- Application model generation_status field (Task 4)
- Generation service (Task 1, 5)
- Generation API endpoints (Task 3)
- Text processing output constraints (Task 2)
- Error handling and gap-aware generation (Task 5, 6)
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.models.application import Application, ApplicationStatus
from app.models.keyword import Keyword, KeywordCategory, KeywordList
from app.models.research import ResearchCategory, ResearchResult, ResearchSourceResult


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def client_with_role(async_client):
    """Authenticated client with role."""
    await async_client.post(
        "/api/v1/auth/register",
        json={"username": "gentest", "password": "password123"},
    )
    login = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "gentest", "password": "password123"},
    )
    async_client.cookies = login.cookies

    role_resp = await async_client.post(
        "/api/v1/roles", json={"name": "Developer"}
    )
    role_id = role_resp.json()["id"]
    async_client.headers["X-Role-Id"] = str(role_id)
    return async_client, role_id


@pytest_asyncio.fixture
async def reviewed_application(client_with_role):
    """Application in 'reviewed' status with full pipeline data, ready for generation."""
    client, role_id = client_with_role

    # Add experience data
    await client.post(
        "/api/v1/experience/skills",
        json={"name": "Python", "category": "Languages"},
    )
    await client.post(
        "/api/v1/experience/skills",
        json={"name": "FastAPI", "category": "Frameworks"},
    )
    await client.post(
        "/api/v1/experience/accomplishments",
        json={
            "description": "Led API migration reducing latency by 40%",
            "context": "TechCo, 2024",
        },
    )

    # Create application
    job_posting = (
        "Senior Python developer with FastAPI and React experience. "
        "Must have 5+ years backend development experience."
    )
    resp = await client.post(
        "/api/v1/applications",
        json={"company_name": "TestCorp", "job_posting": job_posting},
    )
    app_id = resp.json()["id"]

    # Extract keywords
    mock_keywords = KeywordList(
        keywords=[
            Keyword(text="Python", priority=10, category=KeywordCategory.TECHNICAL_SKILL),
            Keyword(text="FastAPI", priority=9, category=KeywordCategory.TOOL),
        ]
    )
    with patch(
        "app.api.v1.applications.extract_keywords",
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
        return "Synthesis of findings."

    with patch.object(research_service, "_research_category", mock_cat), \
         patch.object(research_service, "_synthesize_findings", mock_synth), \
         patch.object(research_service._rate_pacer, "pace", AsyncMock()):
        await research_service.start_research(app_id, role_id, "TestCorp", job_posting)

    research_service._research_state.clear()

    # Add manual context
    await client.patch(
        f"/api/v1/applications/{app_id}/context",
        json={"manual_context": "Extra context for generation."},
    )

    # Approve
    await client.post(f"/api/v1/applications/{app_id}/research/approve")

    return client, role_id, app_id


# ============================================================================
# Task 4: Application Model - generation_status field
# ============================================================================


class TestApplicationModelGeneration:
    """Test generation_status field and GENERATING status."""

    def test_generating_status_exists_in_enum(self):
        """ApplicationStatus must include GENERATING."""
        assert hasattr(ApplicationStatus, "GENERATING")
        assert ApplicationStatus.GENERATING.value == "generating"

    def test_application_model_has_generation_status_field(self):
        """Application model must have generation_status field."""
        app_obj = Application(
            role_id=1,
            company_name="Test",
            job_posting="Looking for developer",
        )
        assert hasattr(app_obj, "generation_status")
        assert app_obj.generation_status == "idle"

    def test_generation_status_default_idle(self):
        """generation_status defaults to idle."""
        app_obj = Application(
            role_id=1,
            company_name="Test",
            job_posting="Looking for developer",
        )
        assert app_obj.generation_status == "idle"

    @pytest.mark.asyncio
    async def test_reviewed_to_generating_transition_allowed(self, client_with_role):
        """State machine must allow REVIEWED -> GENERATING transition."""
        client, role_id = client_with_role

        resp = await client.post(
            "/api/v1/applications",
            json={"company_name": "Corp", "job_posting": "Job description with enough text."},
        )
        app_id = resp.json()["id"]

        # Move through states to REVIEWED
        # created -> keywords
        await client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "keywords"},
        )
        # keywords -> researching
        await client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "researching"},
        )
        # researching -> reviewed
        await client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "reviewed"},
        )

        # reviewed -> generating (NEW transition)
        resp = await client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "generating"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "generating"

    @pytest.mark.asyncio
    async def test_generating_to_exported_transition_allowed(self, client_with_role):
        """State machine must allow GENERATING -> EXPORTED transition."""
        client, role_id = client_with_role

        resp = await client.post(
            "/api/v1/applications",
            json={"company_name": "Corp", "job_posting": "Job description with enough text."},
        )
        app_id = resp.json()["id"]

        # Fast-track to generating
        for status in ["keywords", "researching", "reviewed", "generating"]:
            await client.patch(
                f"/api/v1/applications/{app_id}/status",
                json={"status": status},
            )

        # generating -> exported
        resp = await client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "exported"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "exported"

    @pytest.mark.asyncio
    async def test_generation_status_in_api_response(self, client_with_role):
        """generation_status should be included in API response."""
        client, role_id = client_with_role

        resp = await client.post(
            "/api/v1/applications",
            json={"company_name": "Corp", "job_posting": "Job description with enough text."},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "generation_status" in data
        assert data["generation_status"] == "idle"


# ============================================================================
# Task 2: Text Processing Output Constraints
# ============================================================================


class TestTextProcessingConstraints:
    """Test output constraint enforcement."""

    def test_em_dash_replacement(self):
        from app.utils.text_processing import enforce_output_constraints

        result = enforce_output_constraints("This — is a test")
        assert "—" not in result
        assert "This - is a test" == result

    def test_en_dash_replacement(self):
        from app.utils.text_processing import enforce_output_constraints

        result = enforce_output_constraints("2020 – 2024")
        assert "–" not in result
        assert "2020 - 2024" == result

    def test_smart_quote_replacement(self):
        from app.utils.text_processing import enforce_output_constraints

        result = enforce_output_constraints('\u201cHello\u201d \u2018world\u2019')
        assert "\u201c" not in result
        assert "\u201d" not in result
        assert '"Hello" \'world\'' == result

    def test_excessive_whitespace_cleaned(self):
        from app.utils.text_processing import enforce_output_constraints

        result = enforce_output_constraints("Line 1\n\n\n\nLine 2")
        assert "Line 1\n\nLine 2" == result

    def test_empty_input_returns_empty(self):
        from app.utils.text_processing import enforce_output_constraints

        assert enforce_output_constraints("") == ""
        assert enforce_output_constraints(None) == ""


# ============================================================================
# Task 3: Generation API Endpoints
# ============================================================================


class TestGenerationEndpoints:
    """Test generation API endpoints."""

    @pytest.mark.asyncio
    async def test_generate_resume_endpoint(self, reviewed_application):
        """POST /applications/{id}/generate/resume should generate resume."""
        client, role_id, app_id = reviewed_application

        mock_message = MagicMock()
        mock_message.content = "# John Doe\n\n## Professional Summary\n\nExperienced developer."

        with patch(
            "app.services.generation_service.generate_with_retry",
            new_callable=AsyncMock,
            return_value=mock_message,
        ):
            resp = await client.post(f"/api/v1/applications/{app_id}/generate/resume")

        assert resp.status_code == 200
        data = resp.json()
        assert "resume_content" in data
        assert data["resume_content"] is not None
        assert len(data["resume_content"]) > 0

    @pytest.mark.asyncio
    async def test_generate_cover_letter_endpoint(self, reviewed_application):
        """POST /applications/{id}/generate/cover-letter should generate cover letter."""
        client, role_id, app_id = reviewed_application

        mock_message = MagicMock()
        mock_message.content = "Dear Hiring Manager,\n\nI am excited about..."

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
        assert "cover_letter_content" in data
        assert data["cover_letter_content"] is not None

    @pytest.mark.asyncio
    async def test_generation_status_endpoint(self, reviewed_application):
        """GET /applications/{id}/generation/status should return status."""
        client, role_id, app_id = reviewed_application

        resp = await client.get(f"/api/v1/applications/{app_id}/generation/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "generation_status" in data
        assert "has_resume" in data
        assert "has_cover_letter" in data
        assert data["generation_status"] == "idle"
        assert data["has_resume"] is False
        assert data["has_cover_letter"] is False

    @pytest.mark.asyncio
    async def test_generate_resume_not_found(self, client_with_role):
        """POST /applications/99999/generate/resume returns 404."""
        client, role_id = client_with_role
        resp = await client.post("/api/v1/applications/99999/generate/resume")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_resume_requires_reviewed_status(self, client_with_role):
        """Generate resume should require application in reviewed/generating status."""
        client, role_id = client_with_role

        resp = await client.post(
            "/api/v1/applications",
            json={"company_name": "Corp", "job_posting": "Job description with enough text."},
        )
        app_id = resp.json()["id"]

        resp = await client.post(f"/api/v1/applications/{app_id}/generate/resume")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_generate_resume_stores_content(self, reviewed_application):
        """Generated resume content must be persisted to application record."""
        client, role_id, app_id = reviewed_application

        mock_message = MagicMock()
        mock_message.content = "# Resume Content\n\nGenerated resume text."

        with patch(
            "app.services.generation_service.generate_with_retry",
            new_callable=AsyncMock,
            return_value=mock_message,
        ):
            await client.post(f"/api/v1/applications/{app_id}/generate/resume")

        # Verify content persisted
        resp = await client.get(f"/api/v1/applications/{app_id}")
        assert resp.json()["resume_content"] is not None
        assert "Resume Content" in resp.json()["resume_content"]

    @pytest.mark.asyncio
    async def test_generation_error_updates_status(self, reviewed_application):
        """When generation fails, generation_status should be 'failed'."""
        client, role_id, app_id = reviewed_application

        with patch(
            "app.services.generation_service.generate_with_retry",
            new_callable=AsyncMock,
            side_effect=Exception("LLM API error"),
        ):
            resp = await client.post(f"/api/v1/applications/{app_id}/generate/resume")

        assert resp.status_code == 500

        # Verify status updated to failed
        resp = await client.get(f"/api/v1/applications/{app_id}/generation/status")
        assert resp.json()["generation_status"] == "failed"


# ============================================================================
# Task 5: Generation Context Builder - Gap Handling
# ============================================================================


class TestGenerationGapHandling:
    """Test gap-aware generation (AC #6, #8, #9, #10)."""

    @pytest.mark.asyncio
    async def test_generation_with_gaps_succeeds(self, reviewed_application):
        """Generation must succeed even when research has gaps (AC #8)."""
        client, role_id, app_id = reviewed_application

        # Patch research data to have gaps
        research_with_gaps = ResearchResult(
            strategic_initiatives=ResearchSourceResult(found=True, content="Strategic data"),
            competitive_landscape=ResearchSourceResult(found=True, content="Competitive data"),
            news_momentum=ResearchSourceResult(found=False, reason="Not found"),
            industry_context=ResearchSourceResult(found=False, reason="Not found"),
            culture_values=ResearchSourceResult(found=False, reason="Not found"),
            leadership_direction=ResearchSourceResult(found=False, reason="Not found"),
            synthesis="Partial synthesis.",
            gaps=["news_momentum", "industry_context", "culture_values", "leadership_direction"],
        )

        from app.services import application_service
        from app.models.application import ApplicationUpdate

        await application_service.update_application(
            app_id, role_id,
            ApplicationUpdate(research_data=json.dumps(research_with_gaps.model_dump())),
        )

        mock_message = MagicMock()
        mock_message.content = "# Resume\n\nGenerated with available data."

        with patch(
            "app.services.generation_service.generate_with_retry",
            new_callable=AsyncMock,
            return_value=mock_message,
        ):
            resp = await client.post(f"/api/v1/applications/{app_id}/generate/resume")

        assert resp.status_code == 200
        assert resp.json()["resume_content"] is not None


# ============================================================================
# Issue #8: Unit tests for _log_gap_impact structured logging (AC #10)
# ============================================================================


class TestLogGapImpact:
    """Test _log_gap_impact structured logging (AC #10)."""

    def test_log_gap_impact_logs_structured_entry(self):
        """_log_gap_impact should emit structured log with gap categories and outcome."""
        from app.services.generation_service import _log_gap_impact

        with patch("app.services.generation_service.logger") as mock_logger:
            _log_gap_impact(
                prompt_name="generation_resume",
                gap_categories=["news_momentum", "culture_values"],
                gap_note="Note: The following research categories were unavailable: Recent News & Momentum, Culture & Values.",
                outcome="success",
            )

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args

            # Verify log message
            assert call_args[0][0] == "Generation with research gaps"

            # Verify structured extra fields
            extra = call_args[1]["extra"]
            assert extra["prompt_name"] == "generation_resume"
            assert extra["gap_categories"] == ["news_momentum", "culture_values"]
            assert "unavailable" in extra["gap_note"]
            assert extra["outcome"] == "success"

    def test_log_gap_impact_with_failed_outcome(self):
        """_log_gap_impact should log failed outcome when generation fails."""
        from app.services.generation_service import _log_gap_impact

        with patch("app.services.generation_service.logger") as mock_logger:
            _log_gap_impact(
                prompt_name="generation_cover_letter",
                gap_categories=["industry_context"],
                gap_note="Note: The following research categories were unavailable: Industry Context.",
                outcome="failed",
            )

            mock_logger.info.assert_called_once()
            extra = mock_logger.info.call_args[1]["extra"]
            assert extra["outcome"] == "failed"
            assert extra["prompt_name"] == "generation_cover_letter"
