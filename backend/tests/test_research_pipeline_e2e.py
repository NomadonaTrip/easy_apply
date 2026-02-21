"""End-to-end tests for the research pipeline (Epic 4 Retro Item 10).

Two critical path automated tests:
1. Happy path through research pipeline (all categories succeed)
2. Degradation path with failed categories producing gap flagging

These tests verify the full pipeline at the API level with mocked LLM calls.
Research execution is invoked directly (rather than via background task) for
deterministic test behavior while still exercising the full service layer.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.keyword import Keyword, KeywordCategory, KeywordList
from app.models.research import ResearchCategory, ResearchSourceResult


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def async_client():
    """Async test client for FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def pipeline_client(async_client):
    """Authenticated client with a role, ready for pipeline testing."""
    await async_client.post(
        "/api/v1/auth/register",
        json={"username": "pipelineuser", "password": "password123"},
    )
    login = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "pipelineuser", "password": "password123"},
    )
    async_client.cookies = login.cookies

    role_resp = await async_client.post(
        "/api/v1/roles", json={"name": "Software Engineer"}
    )
    role_id = role_resp.json()["id"]
    async_client.headers["X-Role-Id"] = str(role_id)
    return async_client, role_id


# ============================================================================
# Shared test data
# ============================================================================

MOCK_JOB_POSTING = (
    "Senior Python developer with FastAPI and React experience. "
    "Must have 5+ years experience in backend development. "
    "Knowledge of cloud infrastructure and CI/CD pipelines preferred."
)

MOCK_KEYWORDS = KeywordList(
    keywords=[
        Keyword(text="Python", priority=10, category=KeywordCategory.TECHNICAL_SKILL),
        Keyword(text="FastAPI", priority=9, category=KeywordCategory.TOOL),
        Keyword(text="React", priority=8, category=KeywordCategory.TECHNICAL_SKILL),
        Keyword(
            text="5+ years experience",
            priority=7,
            category=KeywordCategory.EXPERIENCE,
        ),
    ]
)

# Categories that will fail in the degradation test
FAILING_CATEGORIES = {
    ResearchCategory.NEWS_MOMENTUM,
    ResearchCategory.CULTURE_VALUES,
    ResearchCategory.LEADERSHIP_DIRECTION,
}


# ============================================================================
# E2E Test 1: Happy Path
# ============================================================================


class TestResearchPipelineHappyPath:
    """Full happy path: create > keywords > research > context > approve."""

    @pytest.fixture(autouse=True)
    def _cleanup_research_state(self):
        from app.services.research_service import research_service

        yield
        research_service._research_state.clear()

    @pytest.mark.asyncio
    async def test_full_pipeline_create_to_approval(self, pipeline_client, monkeypatch):
        """Create > keywords > research (all succeed) > manual context > approve.

        Verifies:
        - Correct status transitions at each pipeline stage
        - Keywords stored after extraction
        - Research data persisted with all 6 categories found
        - Synthesis generated from findings
        - Manual context persisted and reflected in approval summary
        - Approval response includes complete research summary
        """
        client, role_id = pipeline_client
        from app.services.research_service import research_service

        # ── Step 1: Create application ──────────────────────────────────
        resp = await client.post(
            "/api/v1/applications",
            json={"company_name": "TechCorp", "job_posting": MOCK_JOB_POSTING},
        )
        assert resp.status_code == 201
        app_id = resp.json()["id"]
        assert resp.json()["status"] == "created"

        # ── Step 2: Extract keywords (mock LLM) ────────────────────────
        with patch(
            "app.services.keyword_service.extract_keywords",
            new_callable=AsyncMock,
            return_value=MOCK_KEYWORDS,
        ):
            resp = await client.post(
                f"/api/v1/applications/{app_id}/keywords/extract"
            )
        assert resp.status_code == 200
        kw_data = resp.json()
        assert kw_data["status"] == "keywords"
        assert len(kw_data["keywords"]) == 4
        assert kw_data["keywords"][0]["text"] == "Python"

        # Verify keywords persisted
        resp = await client.get(f"/api/v1/applications/{app_id}")
        assert resp.json()["status"] == "keywords"
        assert resp.json()["keywords"] is not None

        # ── Step 3: Transition to researching ───────────────────────────
        resp = await client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "researching"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "researching"

        # ── Step 4: Execute research with mocked LLM ───────────────────
        async def mock_research_category(
            category, company_name, job_posting, circuit_breaker
        ):
            return ResearchSourceResult(
                found=True,
                content=(
                    f"Comprehensive analysis of {category.value}: "
                    f"TechCorp demonstrates strong positioning in the market."
                ),
            )

        async def mock_synthesize(
            company_name, job_posting, found_results, circuit_breaker
        ):
            return (
                "TechCorp is a fast-growing technology company leading "
                "AI-driven innovation in the enterprise space."
            )

        monkeypatch.setattr(
            research_service, "_research_category", mock_research_category
        )
        monkeypatch.setattr(
            research_service, "_synthesize_findings", mock_synthesize
        )
        monkeypatch.setattr(
            research_service._rate_pacer, "pace", AsyncMock()
        )

        await research_service.start_research(
            app_id, role_id, "TechCorp", MOCK_JOB_POSTING
        )

        # ── Step 5: Verify research data persisted ──────────────────────
        resp = await client.get(f"/api/v1/applications/{app_id}")
        app_data = resp.json()
        assert app_data["status"] == "reviewed"
        assert app_data["research_data"] is not None

        research = json.loads(app_data["research_data"])
        assert len(research["gaps"]) == 0
        assert research["synthesis"] is not None
        for cat in ResearchCategory:
            assert cat.value in research
            assert research[cat.value]["found"] is True

        # ── Step 6: Add manual context ──────────────────────────────────
        resp = await client.patch(
            f"/api/v1/applications/{app_id}/context",
            json={
                "manual_context": (
                    "TechCorp recently won the Industry Innovation Award 2026."
                )
            },
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Context saved successfully"

        # ── Step 7: Approve research ────────────────────────────────────
        resp = await client.post(
            f"/api/v1/applications/{app_id}/research/approve"
        )
        assert resp.status_code == 200
        approval = resp.json()
        assert approval["application_id"] == app_id
        assert approval["status"] == "reviewed"
        assert "approved_at" in approval

        summary = approval["research_summary"]
        assert summary["sources_found"] == 6
        assert summary["gaps"] == []
        assert summary["has_manual_context"] is True

        # ── Verify final application state ──────────────────────────────
        resp = await client.get(f"/api/v1/applications/{app_id}")
        final = resp.json()
        assert final["status"] == "reviewed"
        assert final["keywords"] is not None
        assert final["research_data"] is not None
        assert final["manual_context"] is not None


# ============================================================================
# E2E Test 2: Degradation Path
# ============================================================================


class TestResearchPipelineDegradation:
    """Degradation path: research with failed categories producing gap flagging."""

    @pytest.fixture(autouse=True)
    def _cleanup_research_state(self):
        from app.services.research_service import research_service

        yield
        research_service._research_state.clear()

    @pytest.mark.asyncio
    async def test_degradation_with_failed_categories(
        self, pipeline_client, monkeypatch
    ):
        """Create > research (3 of 6 categories fail) > gap flagging > approve.

        Verifies:
        - Research completes even with category failures (graceful degradation)
        - Failed categories produce gaps in research data
        - Successful categories retain their content
        - Synthesis is generated from partial findings
        - Gap flagging visible via context endpoint
        - Approval succeeds with gaps present
        - Approval summary accurately reflects partial coverage
        """
        client, role_id = pipeline_client
        from app.services.research_service import research_service

        # ── Step 1: Create application ──────────────────────────────────
        resp = await client.post(
            "/api/v1/applications",
            json={"company_name": "SmallStartup", "job_posting": MOCK_JOB_POSTING},
        )
        assert resp.status_code == 201
        app_id = resp.json()["id"]

        # ── Step 2: Extract keywords ────────────────────────────────────
        with patch(
            "app.services.keyword_service.extract_keywords",
            new_callable=AsyncMock,
            return_value=MOCK_KEYWORDS,
        ):
            resp = await client.post(
                f"/api/v1/applications/{app_id}/keywords/extract"
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "keywords"

        # ── Step 3: Transition to researching ───────────────────────────
        resp = await client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "researching"},
        )
        assert resp.status_code == 200

        # ── Step 4: Execute research with partial failures ──────────────
        async def mock_research_category(
            category, company_name, job_posting, circuit_breaker
        ):
            if category in FAILING_CATEGORIES:
                return ResearchSourceResult(
                    found=False,
                    reason=f"No public information found for {category.value}",
                )
            return ResearchSourceResult(
                found=True,
                content=(
                    f"Research findings for {category.value}: "
                    f"relevant data about SmallStartup."
                ),
            )

        async def mock_synthesize(
            company_name, job_posting, found_results, circuit_breaker
        ):
            return (
                "SmallStartup has limited public presence but shows "
                "promise in strategic initiatives and competitive positioning."
            )

        monkeypatch.setattr(
            research_service, "_research_category", mock_research_category
        )
        monkeypatch.setattr(
            research_service, "_synthesize_findings", mock_synthesize
        )
        monkeypatch.setattr(
            research_service._rate_pacer, "pace", AsyncMock()
        )

        await research_service.start_research(
            app_id, role_id, "SmallStartup", MOCK_JOB_POSTING
        )

        # ── Step 5: Verify gap flagging in research data ────────────────
        resp = await client.get(f"/api/v1/applications/{app_id}")
        app_data = resp.json()
        assert app_data["status"] == "reviewed"
        assert app_data["research_data"] is not None

        research = json.loads(app_data["research_data"])

        # 3 categories should be gaps
        assert len(research["gaps"]) == 3
        for cat in FAILING_CATEGORIES:
            assert cat.value in research["gaps"]

        # 3 categories should have found data
        found_count = sum(
            1
            for cat in ResearchCategory
            if research.get(cat.value, {}).get("found", False)
        )
        assert found_count == 3

        # Failed categories should have found=False with reason
        for cat in FAILING_CATEGORIES:
            cat_data = research[cat.value]
            assert cat_data["found"] is False
            assert cat_data["reason"] is not None

        # Synthesis should still exist (partial data was found)
        assert research["synthesis"] is not None

        # ── Step 6: Verify gaps visible via context endpoint ────────────
        resp = await client.get(f"/api/v1/applications/{app_id}/context")
        assert resp.status_code == 200
        context_data = resp.json()
        assert len(context_data["gaps"]) == 3
        for cat in FAILING_CATEGORIES:
            assert cat.value in context_data["gaps"]

        # ── Step 7: Approve research with gaps ──────────────────────────
        resp = await client.post(
            f"/api/v1/applications/{app_id}/research/approve"
        )
        assert resp.status_code == 200
        approval = resp.json()
        assert approval["status"] == "reviewed"

        summary = approval["research_summary"]
        assert summary["sources_found"] == 3  # Only 3 of 6 found
        assert len(summary["gaps"]) == 3
        assert summary["has_manual_context"] is False
