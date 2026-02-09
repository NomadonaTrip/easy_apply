"""Tests for LLM helper utilities (Story 4-5: gap-aware generation context)."""

from app.models.research import ResearchResult, ResearchSourceResult
from app.utils.llm_helpers import build_research_context


class TestBuildResearchContext:
    """Test build_research_context for generation prompt injection."""

    def test_full_research_no_gaps(self):
        research = ResearchResult(
            strategic_initiatives=ResearchSourceResult(found=True, content="Expanding into AI"),
            competitive_landscape=ResearchSourceResult(found=True, content="Ahead of BigCo"),
            news_momentum=ResearchSourceResult(found=True, content="Series C raised"),
            industry_context=ResearchSourceResult(found=True, content="AI growing 30% YoY"),
            culture_values=ResearchSourceResult(found=True, content="Innovation first"),
            leadership_direction=ResearchSourceResult(found=True, content="CEO pushing AI"),
            gaps=[],
        )
        context, gap_note = build_research_context(research)

        assert "Expanding into AI" in context
        assert "Ahead of BigCo" in context
        assert "Series C raised" in context
        assert gap_note is None

    def test_research_with_gaps(self):
        research = ResearchResult(
            strategic_initiatives=ResearchSourceResult(found=True, content="Expanding into AI"),
            competitive_landscape=ResearchSourceResult(found=False, reason="Not found"),
            industry_context=ResearchSourceResult(found=False, reason="Timed out"),
            gaps=["competitive_landscape", "industry_context"],
        )
        context, gap_note = build_research_context(research)

        assert "Expanding into AI" in context
        assert "Not found" not in context  # Gap content should not be in context
        assert gap_note is not None
        assert "Competitive Landscape" in gap_note
        assert "Industry Context" in gap_note
        assert "Proceed with available information" in gap_note

    def test_research_with_partial_data(self):
        research = ResearchResult(
            culture_values=ResearchSourceResult(
                found=True, content="Some culture info", partial=True,
                partial_note="Only careers page found",
            ),
            gaps=[],
        )
        context, gap_note = build_research_context(research)

        assert "Some culture info" in context
        assert "(Note: this information may be incomplete)" in context
        assert gap_note is None

    def test_empty_research(self):
        research = ResearchResult(gaps=[])
        context, gap_note = build_research_context(research)

        assert context == "No research data available."
        assert gap_note is None

    def test_all_gaps(self):
        research = ResearchResult(
            strategic_initiatives=ResearchSourceResult(found=False, reason="Error"),
            competitive_landscape=ResearchSourceResult(found=False, reason="Error"),
            news_momentum=ResearchSourceResult(found=False, reason="Error"),
            industry_context=ResearchSourceResult(found=False, reason="Error"),
            culture_values=ResearchSourceResult(found=False, reason="Error"),
            leadership_direction=ResearchSourceResult(found=False, reason="Error"),
            gaps=[
                "strategic_initiatives", "competitive_landscape",
                "news_momentum", "industry_context",
                "culture_values", "leadership_direction",
            ],
        )
        context, gap_note = build_research_context(research)

        assert context == "No research data available."
        assert gap_note is not None
        assert "6" not in gap_note  # Shouldn't show count, just labels
        assert "Strategic Initiatives" in gap_note
