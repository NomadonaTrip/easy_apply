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
        "app.services.keyword_service.extract_keywords",
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


class TestBuildGenerationContextStructure:
    """Validate build_generation_context produces correct structural format."""

    @pytest.mark.asyncio
    async def test_accomplishments_grouped_by_role(self, generation_ready_client):
        """Accomplishments must be grouped by their context (role) field."""
        client, role_id, app_id = generation_ready_client

        from app.services import application_service
        from app.services.generation_service import build_generation_context

        application = await application_service.get_application(app_id, role_id)
        with patch(
            "app.services.generation_service._get_candidate_header",
            new_callable=AsyncMock,
            return_value="Jane Doe\njane@example.com",
        ):
            context = await build_generation_context(application, role_id)

        # Accomplishments should contain role headings (### context)
        acc_text = context["accomplishments"]
        assert "### TechCo, 2024" in acc_text
        assert "### StartupX, 2023" in acc_text
        # Accomplishments under their respective roles
        assert "Led migration" in acc_text
        assert "Built real-time dashboard" in acc_text

    @pytest.mark.asyncio
    async def test_certifications_separated_from_skills(self, generation_ready_client):
        """Skills with certification category are separated into certifications field."""
        client, role_id, app_id = generation_ready_client

        # Add a certification skill
        await client.post(
            "/api/v1/experience/skills",
            json={"name": "AWS Solutions Architect", "category": "Certification"},
        )

        from app.services import application_service
        from app.services.generation_service import build_generation_context

        application = await application_service.get_application(app_id, role_id)
        with patch(
            "app.services.generation_service._get_candidate_header",
            new_callable=AsyncMock,
            return_value="Jane Doe\njane@example.com",
        ):
            context = await build_generation_context(application, role_id)

        # Certifications should be in separate field
        assert "AWS Solutions Architect" in context["certifications"]
        # And NOT in the regular skills field
        assert "AWS Solutions Architect" not in context["skills"]
        # Regular skills still present
        assert "Python" in context["skills"]

    @pytest.mark.asyncio
    async def test_candidate_header_included_in_context(self, generation_ready_client):
        """Context must include candidate_header for identity preservation."""
        client, role_id, app_id = generation_ready_client

        from app.services import application_service
        from app.services.generation_service import build_generation_context

        application = await application_service.get_application(app_id, role_id)
        with patch(
            "app.services.generation_service._get_candidate_header",
            new_callable=AsyncMock,
            return_value="Jane Doe\njane@example.com\n555-0100",
        ):
            context = await build_generation_context(application, role_id)

        assert context["candidate_header"] == "Jane Doe\njane@example.com\n555-0100"

    @pytest.mark.asyncio
    async def test_context_has_all_required_keys(self, generation_ready_client):
        """Context dict must have all keys needed by generation prompts."""
        client, role_id, app_id = generation_ready_client

        from app.services import application_service
        from app.services.generation_service import build_generation_context

        application = await application_service.get_application(app_id, role_id)
        with patch(
            "app.services.generation_service._get_candidate_header",
            new_callable=AsyncMock,
            return_value="",
        ):
            context = await build_generation_context(application, role_id)

        required_keys = {
            "skills", "certifications", "accomplishments", "candidate_header",
            "company_name", "job_posting", "research_context",
            "gap_note", "gap_categories", "manual_context", "keywords",
            "keywords_raw",
        }
        assert set(context.keys()) >= required_keys

    @pytest.mark.asyncio
    async def test_no_duplicate_role_headings(self, generation_ready_client):
        """Each role context should appear as a heading exactly once."""
        client, role_id, app_id = generation_ready_client

        # Add another accomplishment under same role context
        await client.post(
            "/api/v1/experience/accomplishments",
            json={
                "description": "Reduced infrastructure costs by 30%",
                "context": "TechCo, 2024",
            },
        )

        from app.services import application_service
        from app.services.generation_service import build_generation_context

        application = await application_service.get_application(app_id, role_id)
        with patch(
            "app.services.generation_service._get_candidate_header",
            new_callable=AsyncMock,
            return_value="",
        ):
            context = await build_generation_context(application, role_id)

        acc_text = context["accomplishments"]
        # TechCo heading should appear exactly once
        assert acc_text.count("### TechCo, 2024") == 1
        # But both accomplishments should be listed under it
        assert "Led migration" in acc_text
        assert "Reduced infrastructure costs" in acc_text


class TestCompanyBasedGrouping:
    """Validate build_generation_context groups by company+dates."""

    @pytest.mark.asyncio
    async def test_structured_fields_group_by_company(self, generation_ready_client):
        """Accomplishments with company_name group by company, not context."""
        client, role_id, app_id = generation_ready_client

        # Add accomplishments with structured fields for same company, different titles
        await client.post(
            "/api/v1/experience/accomplishments",
            json={
                "description": "Designed API gateway handling 50K requests per second",
                "context": "Senior Developer at MegaCorp",
                "company_name": "MegaCorp",
                "role_title": "Senior Developer",
                "dates": "2020-2024",
            },
        )
        await client.post(
            "/api/v1/experience/accomplishments",
            json={
                "description": "Mentored 5 junior engineers on microservices best practices",
                "context": "Lead Engineer at MegaCorp",
                "company_name": "MegaCorp",
                "role_title": "Lead Engineer",
                "dates": "2020-2024",
            },
        )

        from app.services import application_service
        from app.services.generation_service import build_generation_context

        application = await application_service.get_application(app_id, role_id)
        with patch(
            "app.services.generation_service._get_candidate_header",
            new_callable=AsyncMock,
            return_value="",
        ):
            context = await build_generation_context(application, role_id)

        acc_text = context["accomplishments"]
        # MegaCorp should appear as a single heading with both titles
        assert "MegaCorp" in acc_text
        assert acc_text.count("MegaCorp") == 1  # one heading only
        assert "Senior Developer" in acc_text
        assert "Lead Engineer" in acc_text
        # Both accomplishments present
        assert "Designed API gateway" in acc_text
        assert "Mentored 5 junior engineers" in acc_text

    @pytest.mark.asyncio
    async def test_same_company_different_dates_stay_separate(self, generation_ready_client):
        """Same company with different date ranges produces separate headings."""
        client, role_id, app_id = generation_ready_client

        await client.post(
            "/api/v1/experience/accomplishments",
            json={
                "description": "Built initial product from scratch",
                "context": "Developer at LoopCo",
                "company_name": "LoopCo",
                "role_title": "Developer",
                "dates": "2015-2018",
            },
        )
        await client.post(
            "/api/v1/experience/accomplishments",
            json={
                "description": "Led platform migration to cloud",
                "context": "Senior Developer at LoopCo",
                "company_name": "LoopCo",
                "role_title": "Senior Developer",
                "dates": "2021-2024",
            },
        )

        from app.services import application_service
        from app.services.generation_service import build_generation_context

        application = await application_service.get_application(app_id, role_id)
        with patch(
            "app.services.generation_service._get_candidate_header",
            new_callable=AsyncMock,
            return_value="",
        ):
            context = await build_generation_context(application, role_id)

        acc_text = context["accomplishments"]
        # LoopCo should appear twice (different date ranges)
        assert acc_text.count("LoopCo") == 2
        assert "2015-2018" in acc_text
        assert "2021-2024" in acc_text

    @pytest.mark.asyncio
    async def test_legacy_accomplishments_fallback_to_context(self, generation_ready_client):
        """Accomplishments without structured fields use context as grouping key."""
        client, role_id, app_id = generation_ready_client

        # The fixture already created accomplishments with only context (no structured fields)
        from app.services import application_service
        from app.services.generation_service import build_generation_context

        application = await application_service.get_application(app_id, role_id)
        with patch(
            "app.services.generation_service._get_candidate_header",
            new_callable=AsyncMock,
            return_value="",
        ):
            context = await build_generation_context(application, role_id)

        acc_text = context["accomplishments"]
        # Legacy context strings should still work as headings
        assert "### TechCo, 2024" in acc_text
        assert "### StartupX, 2023" in acc_text


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


# ============================================================================
# Enriched Keyword Formatting Tests
# ============================================================================


class TestEnrichedKeywordFormatting:
    """Validate _format_keywords_tiered produces priority-tiered output."""

    def test_keywords_grouped_by_priority_tier(self):
        """Keywords are grouped into MUST-HAVE, IMPORTANT, NICE-TO-HAVE."""
        from app.services.generation_service import _format_keywords_tiered

        keywords = [
            {"text": "Python", "priority": 10, "category": "technical_skill", "pattern_boosted": True},
            {"text": "FastAPI", "priority": 9, "category": "tool", "pattern_boosted": False},
            {"text": "CI/CD", "priority": 7, "category": "tool", "pattern_boosted": False},
            {"text": "Agile", "priority": 3, "category": "general", "pattern_boosted": False},
        ]

        result = _format_keywords_tiered(keywords)

        assert "MUST-HAVE" in result
        assert "IMPORTANT" in result
        assert "NICE-TO-HAVE" in result
        # Python should be in MUST-HAVE section
        assert "Python" in result
        # Agile in NICE-TO-HAVE
        assert "Agile" in result

    def test_keywords_show_category_and_priority(self):
        """Each keyword line includes category and priority metadata."""
        from app.services.generation_service import _format_keywords_tiered

        keywords = [
            {"text": "Python", "priority": 10, "category": "technical_skill", "pattern_boosted": False},
        ]

        result = _format_keywords_tiered(keywords)
        assert "[technical_skill, priority: 10]" in result

    def test_pattern_boosted_marker(self):
        """Pattern-boosted keywords get a * marker and legend."""
        from app.services.generation_service import _format_keywords_tiered

        keywords = [
            {"text": "Python", "priority": 10, "category": "technical_skill", "pattern_boosted": True},
            {"text": "React", "priority": 8, "category": "technical_skill", "pattern_boosted": False},
        ]

        result = _format_keywords_tiered(keywords)
        # Python line should have * marker
        python_line = [l for l in result.split("\n") if "Python" in l][0]
        assert python_line.endswith("*")
        # React line should NOT have * marker
        react_line = [l for l in result.split("\n") if "React" in l][0]
        assert not react_line.endswith("*")
        # Legend present
        assert "pattern-boosted" in result

    def test_empty_keywords_returns_fallback(self):
        """Empty keywords list returns fallback text."""
        from app.services.generation_service import _format_keywords_tiered

        assert _format_keywords_tiered([]) == "No keywords specified"

    def test_single_tier_only(self):
        """Keywords in only one tier don't produce empty tier headers."""
        from app.services.generation_service import _format_keywords_tiered

        keywords = [
            {"text": "Python", "priority": 10, "category": "technical_skill", "pattern_boosted": False},
        ]

        result = _format_keywords_tiered(keywords)
        assert "MUST-HAVE" in result
        assert "IMPORTANT" not in result
        assert "NICE-TO-HAVE" not in result

    @pytest.mark.asyncio
    async def test_context_keywords_are_tiered(self, generation_ready_client):
        """build_generation_context produces tiered keyword text."""
        client, role_id, app_id = generation_ready_client

        from app.services import application_service
        from app.services.generation_service import build_generation_context

        application = await application_service.get_application(app_id, role_id)
        with patch(
            "app.services.generation_service._get_candidate_header",
            new_callable=AsyncMock,
            return_value="",
        ):
            context = await build_generation_context(application, role_id)

        # Fixture keywords are all priority 8-10, so only MUST-HAVE tier
        assert "MUST-HAVE" in context["keywords"]
        assert isinstance(context["keywords_raw"], list)
        assert len(context["keywords_raw"]) == 3

    @pytest.mark.asyncio
    async def test_context_keywords_raw_preserves_metadata(self, generation_ready_client):
        """keywords_raw preserves priority, category, and pattern_boosted."""
        client, role_id, app_id = generation_ready_client

        from app.services import application_service
        from app.services.generation_service import build_generation_context

        application = await application_service.get_application(app_id, role_id)
        with patch(
            "app.services.generation_service._get_candidate_header",
            new_callable=AsyncMock,
            return_value="",
        ):
            context = await build_generation_context(application, role_id)

        python_kw = next(kw for kw in context["keywords_raw"] if kw["text"] == "Python")
        assert python_kw["priority"] == 10
        assert python_kw["category"] == "technical_skill"


# ============================================================================
# Accomplishment Annotation Tests
# ============================================================================


class TestAccomplishmentAnnotations:
    """Validate _annotate_accomplishments adds relevance tags."""

    def test_annotations_added_for_matching_keywords(self):
        """Headings get [Relevant to: ...] when bullets mention high-priority keywords."""
        from app.services.generation_service import _annotate_accomplishments

        accomplishments = (
            "### Senior Engineer | Google | 2020-2023\n"
            "- Built distributed cache layer using Python and FastAPI\n"
            "- Reduced API latency by 40%\n"
            "\n"
            "### Junior Dev | Startup | 2018-2020\n"
            "- Maintained legacy PHP application\n"
        )

        keywords = [
            {"text": "Python", "priority": 10, "category": "technical_skill"},
            {"text": "FastAPI", "priority": 9, "category": "tool"},
            {"text": "React", "priority": 8, "category": "technical_skill"},
        ]

        result = _annotate_accomplishments(accomplishments, keywords)

        # Google heading should have Python and FastAPI annotations
        assert "[Relevant to: Python, FastAPI]" in result
        # Startup heading should NOT have annotations (no keyword matches)
        startup_heading = [l for l in result.split("\n") if "Startup" in l][0]
        assert "[Relevant to:" not in startup_heading

    def test_no_annotations_when_no_high_priority_keywords(self):
        """No annotations when all keywords are below priority 7."""
        from app.services.generation_service import _annotate_accomplishments

        accomplishments = "### Engineer | Co | 2020\n- Did Python stuff\n"
        keywords = [{"text": "Python", "priority": 3, "category": "general"}]

        result = _annotate_accomplishments(accomplishments, keywords)
        assert "[Relevant to:" not in result


# ============================================================================
# Keyword Coverage Check Tests
# ============================================================================


class TestKeywordCoverage:
    """Validate check_keyword_coverage returns correct metrics."""

    def test_full_coverage(self):
        """All keywords present yields 100% coverage."""
        from app.utils.text_processing import check_keyword_coverage

        text = "Experience with Python, FastAPI, and React for building web apps."
        keywords = [
            {"text": "Python", "priority": 10, "category": "technical_skill"},
            {"text": "FastAPI", "priority": 9, "category": "tool"},
            {"text": "React", "priority": 8, "category": "technical_skill"},
        ]

        result = check_keyword_coverage(text, keywords)
        assert result["must_have_coverage"] == 1.0
        assert result["must_have_missing"] == []
        assert result["below_threshold"] is False

    def test_partial_coverage(self):
        """Some keywords missing shows correct partial coverage."""
        from app.utils.text_processing import check_keyword_coverage

        text = "Experience with Python for building web apps."
        keywords = [
            {"text": "Python", "priority": 10, "category": "technical_skill"},
            {"text": "FastAPI", "priority": 9, "category": "tool"},
            {"text": "React", "priority": 8, "category": "technical_skill"},
        ]

        result = check_keyword_coverage(text, keywords)
        assert abs(result["must_have_coverage"] - 1 / 3) < 0.01
        assert "FastAPI" in result["must_have_missing"]
        assert "React" in result["must_have_missing"]
        assert result["below_threshold"] is True

    def test_below_threshold_flag(self):
        """below_threshold is True when must-have coverage < 60%."""
        from app.utils.text_processing import check_keyword_coverage

        text = "No relevant keywords here at all."
        keywords = [
            {"text": "Python", "priority": 10, "category": "technical_skill"},
            {"text": "FastAPI", "priority": 9, "category": "tool"},
        ]

        result = check_keyword_coverage(text, keywords)
        assert result["must_have_coverage"] == 0.0
        assert result["below_threshold"] is True

    def test_empty_keywords(self):
        """Empty keywords list returns zeroed metrics, no threshold flag."""
        from app.utils.text_processing import check_keyword_coverage

        result = check_keyword_coverage("Some text", [])
        assert result["must_have_coverage"] == 0.0
        assert result["below_threshold"] is False

    def test_empty_text(self):
        """Empty text returns zeroed metrics."""
        from app.utils.text_processing import check_keyword_coverage

        result = check_keyword_coverage("", [{"text": "Python", "priority": 10}])
        assert result["must_have_coverage"] == 0.0
        assert result["below_threshold"] is False

    def test_case_insensitive_matching(self):
        """Keyword matching is case-insensitive."""
        from app.utils.text_processing import check_keyword_coverage

        text = "Built applications with python and fastapi."
        keywords = [
            {"text": "Python", "priority": 10, "category": "technical_skill"},
            {"text": "FastAPI", "priority": 9, "category": "tool"},
        ]

        result = check_keyword_coverage(text, keywords)
        assert result["must_have_coverage"] == 1.0

    def test_important_tier_coverage(self):
        """Important tier (priority 5-7) is tracked separately."""
        from app.utils.text_processing import check_keyword_coverage

        text = "Used CI/CD pipelines and Agile methodology."
        keywords = [
            {"text": "Python", "priority": 10, "category": "technical_skill"},
            {"text": "CI/CD", "priority": 7, "category": "tool"},
            {"text": "Agile", "priority": 5, "category": "general"},
            {"text": "Docker", "priority": 6, "category": "tool"},
        ]

        result = check_keyword_coverage(text, keywords)
        # must-have: Python missing -> 0%
        assert result["must_have_coverage"] == 0.0
        # important: CI/CD and Agile found, Docker missing -> 2/3
        assert abs(result["important_coverage"] - 2 / 3) < 0.01

    def test_fuzzy_morphological_match(self):
        """'Cross-functional Collaboration' found via 'collaborated with cross-functional teams'."""
        from app.utils.text_processing import keyword_found

        text = "collaborated with cross-functional engineering and design teams"
        assert keyword_found("Cross-functional Collaboration", text.lower()) is True

    def test_fuzzy_all_words_required(self):
        """'Stakeholder Management' NOT found when only 'stakeholder' is present."""
        from app.utils.text_processing import keyword_found

        text = "presented to stakeholder groups"
        assert keyword_found("Stakeholder Management", text.lower()) is False

    def test_fuzzy_single_word_keyword(self):
        """Single word keyword 'Leadership' matched via exact substring."""
        from app.utils.text_processing import keyword_found

        text = "demonstrated strong leadership across multiple teams"
        assert keyword_found("Leadership", text.lower()) is True

    def test_fuzzy_does_not_false_positive_on_short_overlap(self):
        """Fuzzy match requires ALL content words, not just some."""
        from app.utils.text_processing import keyword_found

        text = "analyzed competitive market data"
        # "Customer Data/Insights" — slash step should match "customer data" or "insights"
        # but neither "customer data" nor "insights" appears
        assert keyword_found("Customer Data/Insights", text.lower()) is False

    def test_fuzzy_coverage_integration(self):
        """check_keyword_coverage counts fuzzy matches correctly."""
        from app.utils.text_processing import check_keyword_coverage

        text = (
            "collaborated with cross-functional engineering teams. "
            "managed key stakeholders across product and design. "
            "conducted competitive market analysis for product positioning."
        )
        keywords = [
            {"text": "Cross-functional Collaboration", "priority": 10, "category": "general"},
            {"text": "Stakeholder Management", "priority": 9, "category": "general"},
            {"text": "Competitive Analysis", "priority": 8, "category": "general"},
        ]

        result = check_keyword_coverage(text, keywords)
        assert result["must_have_coverage"] == 1.0
        assert result["must_have_missing"] == []

    def test_annotation_fuzzy_matching(self):
        """_annotate_accomplishments tags headings using fuzzy matching."""
        from app.services.generation_service import _annotate_accomplishments

        accomplishments = (
            "### Product Manager | Acme | 2022-2024\n"
            "- Collaborated with cross-functional engineering and design teams\n"
            "- Managed key stakeholders to align on product roadmap\n"
        )
        keywords = [
            {"text": "Cross-functional Collaboration", "priority": 10, "category": "general"},
            {"text": "Stakeholder Management", "priority": 9, "category": "general"},
            {"text": "React", "priority": 8, "category": "technical_skill"},
        ]

        result = _annotate_accomplishments(accomplishments, keywords)
        assert "Cross-functional Collaboration" in result
        assert "Stakeholder Management" in result
        assert "React" not in result.split("[Relevant to:")[1] if "[Relevant to:" in result else True


# ============================================================================
# Skill Enrichment Feedback Loop Tests
# ============================================================================


class TestSkillEnrichment:
    """Validate enrich_skills_from_keywords feedback loop."""

    @pytest.mark.asyncio
    async def test_enrich_adds_keyword_as_skill(self, generation_ready_client):
        """Keyword that fuzzy-matches an accomplishment gets persisted as new skill."""
        client, role_id, app_id = generation_ready_client

        from app.services.extraction_service import enrich_skills_from_keywords
        from app.services import experience_service

        accomplishments = await experience_service.get_accomplishments(role_id)
        skills = await experience_service.get_skills(role_id)

        # "FastAPI" is already a skill AND appears in accomplishments,
        # but "API microservices" is not a skill — if we pass it as a keyword
        # and it fuzzy-matches "microservices" in accomplishments, it gets added
        keywords = [
            {"text": "API Development", "priority": 8, "category": "technical_skill"},
        ]

        # The accomplishment contains "API to FastAPI microservices" which has
        # both "api" and "devel" prefixes won't match... let's use a keyword
        # that we know will match accomplishment text
        # Accomplishment text: "Led migration of monolithic API to FastAPI microservices, reducing latency by 40%"
        keywords = [
            {"text": "API Migration", "priority": 8, "category": "technical_skill"},
        ]

        added = await enrich_skills_from_keywords(role_id, keywords, accomplishments, skills)
        assert added == 1

        # Verify skill was actually persisted
        updated_skills = await experience_service.get_skills(role_id)
        skill_names = [s.name.lower() for s in updated_skills]
        assert "api migration" in skill_names

    @pytest.mark.asyncio
    async def test_enrich_skips_exact_duplicate(self, generation_ready_client):
        """Keyword already in skills library (exact match) is not re-added."""
        client, role_id, app_id = generation_ready_client

        from app.services.extraction_service import enrich_skills_from_keywords
        from app.services import experience_service

        accomplishments = await experience_service.get_accomplishments(role_id)
        skills = await experience_service.get_skills(role_id)

        # "Python" is already a skill
        keywords = [
            {"text": "Python", "priority": 10, "category": "technical_skill"},
        ]

        added = await enrich_skills_from_keywords(role_id, keywords, accomplishments, skills)
        assert added == 0

    @pytest.mark.asyncio
    async def test_enrich_skips_low_priority(self, generation_ready_client):
        """Priority < 5 keywords are not added even if they match."""
        client, role_id, app_id = generation_ready_client

        from app.services.extraction_service import enrich_skills_from_keywords
        from app.services import experience_service

        accomplishments = await experience_service.get_accomplishments(role_id)
        skills = await experience_service.get_skills(role_id)

        keywords = [
            {"text": "API Migration", "priority": 3, "category": "technical_skill"},
        ]

        added = await enrich_skills_from_keywords(role_id, keywords, accomplishments, skills)
        assert added == 0
