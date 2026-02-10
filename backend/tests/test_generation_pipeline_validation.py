"""Pipeline validation tests for Story 5-1: Generation Service.

Task 0: Verify the existing pipeline (create > keywords > research > approve)
produces data in the correct shape for the generation service to consume.

These tests validate:
- build_research_context() returns correct (research_str, gap_note) tuple
- application.manual_context is accessible after context page workflow
- Research approval state machine allows generation to proceed (status = "reviewed")
- Keywords, research data, and experience data are in expected formats
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.models.keyword import Keyword, KeywordCategory, KeywordList
from app.models.research import (
    ResearchCategory,
    ResearchResult,
    ResearchSourceResult,
)
from app.utils.llm_helpers import build_research_context


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def generation_ready_client(async_client):
    """Client with a fully pipeline-processed application ready for generation.

    Creates: user > role > skills > accomplishments > application >
    keywords > research (all succeed) > manual context > approve
    """
    # Register and login
    await async_client.post(
        "/api/v1/auth/register",
        json={"username": "genuser", "password": "password123"},
    )
    login = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "genuser", "password": "password123"},
    )
    async_client.cookies = login.cookies

    # Create role
    role_resp = await async_client.post(
        "/api/v1/roles", json={"name": "Software Engineer"}
    )
    role_id = role_resp.json()["id"]
    async_client.headers["X-Role-Id"] = str(role_id)

    # Add skills to experience database
    await async_client.post(
        "/api/v1/experience/skills",
        json={"name": "Python", "category": "Programming Languages"},
    )
    await async_client.post(
        "/api/v1/experience/skills",
        json={"name": "FastAPI", "category": "Frameworks"},
    )
    await async_client.post(
        "/api/v1/experience/skills",
        json={"name": "React", "category": "Frontend"},
    )

    # Add accomplishments
    await async_client.post(
        "/api/v1/experience/accomplishments",
        json={
            "description": "Led migration of monolithic API to FastAPI microservices, reducing latency by 40%",
            "context": "TechCo, 2024",
        },
    )
    await async_client.post(
        "/api/v1/experience/accomplishments",
        json={
            "description": "Built real-time dashboard with React serving 10K daily users",
            "context": "StartupX, 2023",
        },
    )

    # Create application
    job_posting = (
        "Senior Python developer with FastAPI and React experience. "
        "Must have 5+ years experience in backend development. "
        "Knowledge of cloud infrastructure and CI/CD pipelines preferred."
    )
    app_resp = await async_client.post(
        "/api/v1/applications",
        json={"company_name": "TechCorp", "job_posting": job_posting},
    )
    app_id = app_resp.json()["id"]

    # Extract keywords (mocked)
    mock_keywords = KeywordList(
        keywords=[
            Keyword(text="Python", priority=10, category=KeywordCategory.TECHNICAL_SKILL),
            Keyword(text="FastAPI", priority=9, category=KeywordCategory.TOOL),
            Keyword(text="React", priority=8, category=KeywordCategory.TECHNICAL_SKILL),
        ]
    )
    with patch(
        "app.api.v1.applications.extract_keywords",
        new_callable=AsyncMock,
        return_value=mock_keywords,
    ):
        await async_client.post(f"/api/v1/applications/{app_id}/keywords/extract")

    # Transition to researching
    await async_client.patch(
        f"/api/v1/applications/{app_id}/status",
        json={"status": "researching"},
    )

    # Execute research (mocked)
    from app.services.research_service import research_service

    async def mock_research_category(category, company_name, job_posting, circuit_breaker):
        return ResearchSourceResult(
            found=True,
            content=f"Research findings for {category.value}: TechCorp analysis.",
        )

    async def mock_synthesize(company_name, job_posting, found_results, circuit_breaker):
        return "TechCorp is hiring for strategic growth in AI infrastructure."

    with patch.object(research_service, "_research_category", mock_research_category), \
         patch.object(research_service, "_synthesize_findings", mock_synthesize), \
         patch.object(research_service._rate_pacer, "pace", AsyncMock()):
        await research_service.start_research(app_id, role_id, "TechCorp", job_posting)

    # Add manual context
    await async_client.patch(
        f"/api/v1/applications/{app_id}/context",
        json={"manual_context": "I met their CTO at PyCon 2025 and discussed their platform."},
    )

    # Approve research (idempotent since research_service already transitions to reviewed)
    await async_client.post(f"/api/v1/applications/{app_id}/research/approve")

    # Cleanup research state
    research_service._research_state.clear()

    return async_client, role_id, app_id


# ============================================================================
# Task 0 Validation Tests
# ============================================================================


class TestPipelineDataShapesForGeneration:
    """Validate pipeline output is in correct shape for generation service."""

    @pytest.mark.asyncio
    async def test_application_in_reviewed_status(self, generation_ready_client):
        """Status must be 'reviewed' to allow generation to proceed."""
        client, role_id, app_id = generation_ready_client

        resp = await client.get(f"/api/v1/applications/{app_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "reviewed"

    @pytest.mark.asyncio
    async def test_keywords_accessible_and_parseable(self, generation_ready_client):
        """Keywords must be stored as valid JSON array and parseable."""
        client, role_id, app_id = generation_ready_client

        resp = await client.get(f"/api/v1/applications/{app_id}")
        data = resp.json()
        assert data["keywords"] is not None

        keywords = json.loads(data["keywords"])
        # Keywords are stored as a JSON array of keyword objects
        assert isinstance(keywords, list)
        assert len(keywords) == 3
        assert keywords[0]["text"] == "Python"
        assert "priority" in keywords[0]
        assert "category" in keywords[0]

    @pytest.mark.asyncio
    async def test_research_data_parseable_to_research_result(self, generation_ready_client):
        """Research data must be parseable into ResearchResult model."""
        client, role_id, app_id = generation_ready_client

        resp = await client.get(f"/api/v1/applications/{app_id}")
        data = resp.json()
        assert data["research_data"] is not None

        research_dict = json.loads(data["research_data"])
        research = ResearchResult(**research_dict)

        # All 6 categories should be present and found
        for cat in ResearchCategory:
            source = getattr(research, cat.value)
            assert source is not None
            assert source.found is True
            assert source.content is not None

        # Synthesis should exist
        assert research.synthesis is not None

        # No gaps in happy path
        assert research.gaps == []

    @pytest.mark.asyncio
    async def test_build_research_context_returns_correct_format(self, generation_ready_client):
        """build_research_context() must return (str, Optional[str]) tuple."""
        client, role_id, app_id = generation_ready_client

        resp = await client.get(f"/api/v1/applications/{app_id}")
        research_dict = json.loads(resp.json()["research_data"])
        research = ResearchResult(**research_dict)

        research_context, gap_note = build_research_context(research)

        # Research context should be a non-empty string
        assert isinstance(research_context, str)
        assert len(research_context) > 0
        assert "No research data available" not in research_context

        # No gaps means gap_note should be None
        assert gap_note is None

    @pytest.mark.asyncio
    async def test_manual_context_accessible(self, generation_ready_client):
        """manual_context must be accessible on the application."""
        client, role_id, app_id = generation_ready_client

        resp = await client.get(f"/api/v1/applications/{app_id}")
        data = resp.json()
        assert data["manual_context"] is not None
        assert "PyCon" in data["manual_context"]

    @pytest.mark.asyncio
    async def test_experience_data_available(self, generation_ready_client):
        """Skills and accomplishments must be available for context building."""
        client, role_id, app_id = generation_ready_client

        skills_resp = await client.get("/api/v1/experience/skills")
        assert skills_resp.status_code == 200
        skills = skills_resp.json()
        assert len(skills) == 3

        acc_resp = await client.get("/api/v1/experience/accomplishments")
        assert acc_resp.status_code == 200
        accomplishments = acc_resp.json()
        assert len(accomplishments) == 2


class TestBuildResearchContextWithGaps:
    """Validate build_research_context() handles gaps correctly."""

    def test_gaps_produce_gap_note(self):
        """When research has gaps, gap_note is returned."""
        research = ResearchResult(
            strategic_initiatives=ResearchSourceResult(
                found=True, content="Strategic findings"
            ),
            competitive_landscape=ResearchSourceResult(
                found=True, content="Competitive findings"
            ),
            news_momentum=ResearchSourceResult(found=False, reason="Not found"),
            industry_context=ResearchSourceResult(found=False, reason="Not found"),
            culture_values=ResearchSourceResult(found=False, reason="Not found"),
            leadership_direction=ResearchSourceResult(found=False, reason="Not found"),
            gaps=["news_momentum", "industry_context", "culture_values", "leadership_direction"],
        )

        research_context, gap_note = build_research_context(research)

        assert isinstance(research_context, str)
        assert "Strategic Initiatives" in research_context
        assert "Competitive Landscape" in research_context

        assert gap_note is not None
        assert "unavailable" in gap_note
        assert "Recent News" in gap_note or "News" in gap_note

    def test_all_gaps_returns_no_data_string(self):
        """When all categories are gaps, research context says no data available."""
        research = ResearchResult(
            gaps=[cat.value for cat in ResearchCategory],
        )

        research_context, gap_note = build_research_context(research)

        assert "No research data available" in research_context
        assert gap_note is not None

    def test_no_gaps_returns_none_gap_note(self):
        """When no gaps, gap_note is None."""
        research = ResearchResult(
            strategic_initiatives=ResearchSourceResult(found=True, content="Content"),
            competitive_landscape=ResearchSourceResult(found=True, content="Content"),
            news_momentum=ResearchSourceResult(found=True, content="Content"),
            industry_context=ResearchSourceResult(found=True, content="Content"),
            culture_values=ResearchSourceResult(found=True, content="Content"),
            leadership_direction=ResearchSourceResult(found=True, content="Content"),
            gaps=[],
        )

        _, gap_note = build_research_context(research)
        assert gap_note is None
