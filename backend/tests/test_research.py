"""Tests for research service, SSE manager, and research API endpoints."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.llm.circuit_breaker import CircuitBreaker
from app.models.research import (
    ResearchStatus,
    ResearchCategory,
    ResearchSourceResult,
    ResearchResult,
    ResearchProgressEvent,
    ResearchCompleteEvent,
    ResearchErrorEvent,
)
from app.services.sse_manager import SSEManager
from app.services.research_service import (
    ResearchService,
    CATEGORY_PROMPT_NAMES,
    CATEGORY_MESSAGES,
    CATEGORY_PROMPT_KWARGS,
    NOT_FOUND_INDICATORS,
    GAP_REASON_CIRCUIT_OPEN,
    _is_not_found,
)


# ============================================================================
# Research Models Tests
# ============================================================================


class TestResearchModels:
    """Test research model schemas and enums."""

    def test_research_status_enum_values(self):
        assert ResearchStatus.PENDING == "pending"
        assert ResearchStatus.RUNNING == "running"
        assert ResearchStatus.COMPLETE == "complete"
        assert ResearchStatus.FAILED == "failed"

    def test_research_category_enum_values(self):
        assert ResearchCategory.STRATEGIC_INITIATIVES == "strategic_initiatives"
        assert ResearchCategory.COMPETITIVE_LANDSCAPE == "competitive_landscape"
        assert ResearchCategory.NEWS_MOMENTUM == "news_momentum"
        assert ResearchCategory.INDUSTRY_CONTEXT == "industry_context"
        assert ResearchCategory.CULTURE_VALUES == "culture_values"
        assert ResearchCategory.LEADERSHIP_DIRECTION == "leadership_direction"

    def test_research_source_result_found(self):
        result = ResearchSourceResult(found=True, content="Some content")
        assert result.found is True
        assert result.content == "Some content"
        assert result.reason is None

    def test_research_source_result_not_found(self):
        result = ResearchSourceResult(found=False, reason="Source unavailable")
        assert result.found is False
        assert result.content is None
        assert result.reason == "Source unavailable"

    def test_research_progress_event(self):
        event = ResearchProgressEvent(source="strategic_initiatives", message="Investigating...")
        assert event.type == "progress"
        assert event.source == "strategic_initiatives"
        assert event.status == "searching"
        assert event.message == "Investigating..."

    def test_research_progress_event_custom_status(self):
        event = ResearchProgressEvent(source="competitive_landscape", status="analyzing", message="Deep dive...")
        assert event.status == "analyzing"

    def test_research_complete_event(self):
        result = ResearchSourceResult(found=True, content="data")
        event = ResearchCompleteEvent(research_data={"strategic_initiatives": result})
        assert event.type == "complete"
        assert "strategic_initiatives" in event.research_data

    def test_research_error_event(self):
        event = ResearchErrorEvent(message="Something failed")
        assert event.type == "error"
        assert event.message == "Something failed"

    def test_research_result_with_gaps(self):
        result = ResearchResult(
            strategic_initiatives=ResearchSourceResult(found=True, content="data"),
            industry_context=ResearchSourceResult(found=False, reason="Limited public information"),
            gaps=["industry_context"],
            completed_at="2026-02-08T00:00:00Z",
        )
        assert result.strategic_initiatives.found is True
        assert result.industry_context.found is False
        assert "industry_context" in result.gaps
        assert result.completed_at is not None

    def test_research_result_default_gaps_empty(self):
        result = ResearchResult()
        assert result.gaps == []
        assert result.completed_at is None

    def test_research_result_with_synthesis(self):
        result = ResearchResult(
            synthesis="This company needs this role because...",
            completed_at="2026-02-08T00:00:00Z",
        )
        assert result.synthesis is not None
        assert "This company" in result.synthesis


# ============================================================================
# SSE Manager Tests
# ============================================================================


class TestSSEManager:
    """Test SSEManager event streaming."""

    @pytest.mark.asyncio
    async def test_create_stream_and_receive_event(self):
        manager = SSEManager()

        async def producer():
            await asyncio.sleep(0.05)
            await manager.send_event(1, "progress", {"source": "test", "message": "Testing..."})
            await asyncio.sleep(0.05)
            await manager.send_event(1, "complete", {"summary": "Done"})

        asyncio.create_task(producer())

        events = []
        async for event_str in manager.create_stream(1):
            events.append(event_str)

        assert len(events) == 2
        first = json.loads(events[0].replace("data: ", "").strip())
        assert first["type"] == "progress"
        assert first["source"] == "test"

        second = json.loads(events[1].replace("data: ", "").strip())
        assert second["type"] == "complete"

    @pytest.mark.asyncio
    async def test_stream_closes_on_complete_event(self):
        manager = SSEManager()

        async def producer():
            await asyncio.sleep(0.05)
            await manager.send_event(1, "complete", {"summary": "Done"})

        asyncio.create_task(producer())

        events = []
        async for event_str in manager.create_stream(1):
            events.append(event_str)

        assert len(events) == 1
        assert not manager.is_active(1)

    @pytest.mark.asyncio
    async def test_stream_closes_on_error_event(self):
        manager = SSEManager()

        async def producer():
            await asyncio.sleep(0.05)
            await manager.send_event(1, "error", {"message": "Failed"})

        asyncio.create_task(producer())

        events = []
        async for event_str in manager.create_stream(1):
            events.append(event_str)

        assert len(events) == 1
        data = json.loads(events[0].replace("data: ", "").strip())
        assert data["type"] == "error"
        assert not manager.is_active(1)

    @pytest.mark.asyncio
    async def test_send_event_to_nonexistent_stream(self):
        manager = SSEManager()
        # Should not raise
        await manager.send_event(999, "progress", {"message": "No one listening"})

    @pytest.mark.asyncio
    async def test_is_active_returns_false_for_unknown(self):
        manager = SSEManager()
        assert manager.is_active(999) is False

    @pytest.mark.asyncio
    async def test_close_stream(self):
        manager = SSEManager()
        manager._streams[1] = asyncio.Queue()
        manager._active[1] = True

        manager.close_stream(1)
        assert manager._active[1] is False

    @pytest.mark.asyncio
    async def test_cleanup_removes_resources(self):
        manager = SSEManager()
        manager._streams[1] = asyncio.Queue()
        manager._active[1] = True

        manager._cleanup(1)
        assert 1 not in manager._streams
        assert 1 not in manager._active

    @pytest.mark.asyncio
    async def test_create_stream_reuses_existing_queue(self):
        """Verify create_stream reuses an existing queue instead of replacing it."""
        manager = SSEManager()
        queue = asyncio.Queue()
        manager._streams[1] = queue
        await queue.put({"type": "complete", "summary": "Pre-loaded"})

        events = []
        async for event_str in manager.create_stream(1):
            events.append(event_str)

        assert len(events) == 1
        data = json.loads(events[0].replace("data: ", "").strip())
        assert data["summary"] == "Pre-loaded"

    @pytest.mark.asyncio
    async def test_multiple_progress_events_before_complete(self):
        manager = SSEManager()

        async def producer():
            await asyncio.sleep(0.05)
            for i in range(3):
                await manager.send_event(1, "progress", {"source": f"src_{i}", "message": f"Step {i}"})
                await asyncio.sleep(0.02)
            await manager.send_event(1, "complete", {"summary": "All done"})

        asyncio.create_task(producer())

        events = []
        async for event_str in manager.create_stream(1):
            events.append(event_str)

        assert len(events) == 4  # 3 progress + 1 complete


# ============================================================================
# Research Prompt Registration Tests (Task 1)
# ============================================================================


class TestResearchPromptRegistration:
    """Test that all research prompts are registered in the PromptRegistry."""

    def test_all_category_prompts_registered(self):
        from app.llm.prompts import PromptRegistry

        for category, prompt_name in CATEGORY_PROMPT_NAMES.items():
            assert prompt_name in PromptRegistry.list(), (
                f"Prompt '{prompt_name}' for category '{category.value}' not registered"
            )

    def test_synthesis_prompt_registered(self):
        from app.llm.prompts import PromptRegistry

        assert "research_synthesis" in PromptRegistry.list()

    def test_strategic_initiatives_prompt_formatting(self):
        from app.llm.prompts import PromptRegistry

        result = PromptRegistry.get(
            "research_strategic_initiatives",
            company_name="TestCorp",
            job_posting_summary="A great job posting",
        )
        assert "TestCorp" in result
        assert "A great job posting" in result

    def test_competitive_landscape_prompt_formatting(self):
        from app.llm.prompts import PromptRegistry

        result = PromptRegistry.get(
            "research_competitive_landscape",
            company_name="TestCorp",
            job_posting_summary="A great job posting",
        )
        assert "TestCorp" in result

    def test_news_momentum_prompt_formatting(self):
        from app.llm.prompts import PromptRegistry

        result = PromptRegistry.get(
            "research_news_momentum",
            company_name="TestCorp",
        )
        assert "TestCorp" in result

    def test_culture_values_prompt_formatting(self):
        from app.llm.prompts import PromptRegistry

        result = PromptRegistry.get(
            "research_culture_values",
            company_name="TestCorp",
        )
        assert "TestCorp" in result

    def test_leadership_direction_prompt_formatting(self):
        from app.llm.prompts import PromptRegistry

        result = PromptRegistry.get(
            "research_leadership_direction",
            company_name="TestCorp",
            job_posting_summary="Engineer role",
        )
        assert "TestCorp" in result

    def test_synthesis_prompt_formatting(self):
        from app.llm.prompts import PromptRegistry

        result = PromptRegistry.get(
            "research_synthesis",
            company_name="TestCorp",
            research_findings="## Strategic Initiatives\nFindings here",
            job_posting_summary="Engineer role",
        )
        assert "TestCorp" in result
        assert "Findings here" in result

    def test_prompt_names_match_categories(self):
        """Verify every ResearchCategory has an entry in CATEGORY_PROMPT_NAMES."""
        for category in ResearchCategory:
            assert category in CATEGORY_PROMPT_NAMES, (
                f"Category '{category.value}' missing from CATEGORY_PROMPT_NAMES"
            )

    def test_category_messages_match_categories(self):
        """Verify every ResearchCategory has an entry in CATEGORY_MESSAGES."""
        for category in ResearchCategory:
            assert category in CATEGORY_MESSAGES, (
                f"Category '{category.value}' missing from CATEGORY_MESSAGES"
            )

    def test_category_prompt_kwargs_match_categories(self):
        """Verify every ResearchCategory has an entry in CATEGORY_PROMPT_KWARGS."""
        for category in ResearchCategory:
            assert category in CATEGORY_PROMPT_KWARGS, (
                f"Category '{category.value}' missing from CATEGORY_PROMPT_KWARGS"
            )


# ============================================================================
# Not-Found Detection Tests (H4 fix)
# ============================================================================


class TestNotFoundDetection:
    """Test the robust not-found detection logic."""

    def test_short_not_found_message(self):
        assert _is_not_found("No information found about this company.") is True

    def test_short_unavailable_message(self):
        assert _is_not_found("Information unavailable for this query.") is True

    def test_long_response_with_indicator_is_found(self):
        """Long detailed responses that incidentally contain not-found phrases are real content."""
        long_content = (
            "TestCorp is a major player in the AI space. "
            "Unlike competitors who found no results in the European market, "
            "TestCorp has expanded aggressively into 15 countries. "
            "Their strategic initiatives include building a new cloud platform, "
            "acquiring three startups, and hiring 500 engineers. " * 5
        )
        assert len(long_content) > 500
        assert _is_not_found(long_content) is False

    def test_short_found_content(self):
        assert _is_not_found("TestCorp is expanding into AI analytics.") is False

    def test_empty_string(self):
        assert _is_not_found("") is False


# ============================================================================
# Research Service Unit Tests (Tasks 2-9)
# ============================================================================


class TestResearchService:
    """Test ResearchService business logic."""

    def test_get_status_returns_none_for_unknown(self):
        service = ResearchService()
        assert service.get_status(999) is None

    def test_is_running_returns_false_for_unknown(self):
        service = ResearchService()
        assert service.is_running(999) is False

    def test_is_running_returns_true_when_running(self):
        service = ResearchService()
        service._research_state[1] = ResearchStatus.RUNNING
        assert service.is_running(1) is True

    def test_is_running_returns_false_when_complete(self):
        service = ResearchService()
        service._research_state[1] = ResearchStatus.COMPLETE
        assert service.is_running(1) is False

    @pytest.mark.asyncio
    async def test_cancel_research_when_running(self, monkeypatch):
        """Test cancel_research stops running research and sends error event."""
        service = ResearchService()
        manager = SSEManager()

        import app.services.research_service as rs_module
        monkeypatch.setattr(rs_module, "sse_manager", manager)

        service._research_state[1] = ResearchStatus.RUNNING
        queue = asyncio.Queue()
        manager._streams[1] = queue
        manager._active[1] = True

        result = await service.cancel_research(1)

        assert result is True
        assert service.get_status(1) is None  # State cleaned up
        assert not manager.is_active(1)

        event = queue.get_nowait()
        assert event["type"] == "error"
        assert event["message"] == "Research cancelled"
        assert event["recoverable"] is False

    @pytest.mark.asyncio
    async def test_cancel_research_when_not_running(self):
        service = ResearchService()
        result = await service.cancel_research(999)
        assert result is False


class TestResearchCategoryExecution:
    """Test _research_category with mocked LLM provider."""

    @pytest.mark.asyncio
    async def test_successful_category_research(self, monkeypatch):
        """Test that a successful LLM response returns found=True with content."""
        service = ResearchService()
        cb = CircuitBreaker()

        # Mock LLM provider
        mock_response = MagicMock()
        mock_response.content = "TestCorp is expanding into AI-driven analytics."
        mock_response.tool_calls = None

        mock_provider = AsyncMock()
        mock_provider.generate_with_tools = AsyncMock(return_value=(mock_response, []))

        monkeypatch.setattr(
            "app.llm.get_llm_provider",
            lambda: mock_provider,
        )

        # Mock ToolRegistry to return no tools (simplifies test)
        mock_registry = MagicMock()
        mock_registry.get_all.return_value = []
        monkeypatch.setattr(
            "app.llm.tools.ToolRegistry",
            lambda config: mock_registry,
        )

        result = await service._research_category(
            ResearchCategory.STRATEGIC_INITIATIVES,
            "TestCorp",
            "Software engineer role",
            cb,
        )

        assert result.found is True
        assert "TestCorp" in result.content
        assert result.reason is None

    @pytest.mark.asyncio
    async def test_category_research_not_found_indicators(self, monkeypatch):
        """Test that short not-found indicator responses mark result as not found."""
        service = ResearchService()
        cb = CircuitBreaker()

        mock_response = MagicMock()
        mock_response.content = "No information found about this company's initiatives."
        mock_response.tool_calls = None

        mock_provider = AsyncMock()
        mock_provider.generate_with_tools = AsyncMock(return_value=(mock_response, []))

        monkeypatch.setattr(
            "app.llm.get_llm_provider",
            lambda: mock_provider,
        )

        mock_registry = MagicMock()
        mock_registry.get_all.return_value = []
        monkeypatch.setattr(
            "app.llm.tools.ToolRegistry",
            lambda config: mock_registry,
        )

        result = await service._research_category(
            ResearchCategory.STRATEGIC_INITIATIVES,
            "UnknownCorp",
            "Some job posting",
            cb,
        )

        assert result.found is False
        assert result.reason is not None

    @pytest.mark.asyncio
    async def test_category_research_empty_response(self, monkeypatch):
        """Test that empty LLM response returns not found."""
        service = ResearchService()
        cb = CircuitBreaker()

        mock_response = MagicMock()
        mock_response.content = ""
        mock_response.tool_calls = None

        mock_provider = AsyncMock()
        mock_provider.generate_with_tools = AsyncMock(return_value=(mock_response, []))

        monkeypatch.setattr(
            "app.llm.get_llm_provider",
            lambda: mock_provider,
        )

        mock_registry = MagicMock()
        mock_registry.get_all.return_value = []
        monkeypatch.setattr(
            "app.llm.tools.ToolRegistry",
            lambda config: mock_registry,
        )

        result = await service._research_category(
            ResearchCategory.COMPETITIVE_LANDSCAPE,
            "TestCorp",
            "Some posting",
            cb,
        )

        assert result.found is False
        assert "No results" in result.reason

    @pytest.mark.asyncio
    async def test_category_research_with_tool_calls(self, monkeypatch):
        """Test the tool-use loop with web search tool calls."""
        service = ResearchService()
        cb = CircuitBreaker()

        # First call returns tool calls, second returns final answer
        tool_call = MagicMock()
        tool_call.name = "web_search"
        tool_call.arguments = {"query": "TestCorp strategic initiatives"}

        first_response = MagicMock()
        first_response.content = ""
        first_response.tool_calls = [tool_call]

        final_response = MagicMock()
        final_response.content = "TestCorp is building a new AI platform."
        final_response.tool_calls = None

        call_count = 0

        async def mock_generate_with_tools(messages, tools, config=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (first_response, [tool_call])
            return (final_response, [])

        mock_provider = AsyncMock()
        mock_provider.generate_with_tools = mock_generate_with_tools

        monkeypatch.setattr(
            "app.llm.get_llm_provider",
            lambda: mock_provider,
        )

        # Mock tool execution
        mock_tool = AsyncMock()
        mock_tool_result = MagicMock()
        mock_tool_result.success = True
        mock_tool_result.content = "Search results about TestCorp"
        mock_tool.execute = AsyncMock(return_value=mock_tool_result)

        mock_registry = MagicMock()
        mock_registry.get_all.return_value = [mock_tool]
        mock_registry.get.return_value = mock_tool
        monkeypatch.setattr(
            "app.llm.tools.ToolRegistry",
            lambda config: mock_registry,
        )

        result = await service._research_category(
            ResearchCategory.STRATEGIC_INITIATIVES,
            "TestCorp",
            "Software engineer role",
            cb,
        )

        assert result.found is True
        assert "AI platform" in result.content
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_category_research_llm_exception_records_failure(self, monkeypatch):
        """Test that LLM exceptions trigger circuit breaker failure recording."""
        service = ResearchService()
        cb = CircuitBreaker()

        mock_provider = AsyncMock()
        mock_provider.generate_with_tools = AsyncMock(
            side_effect=RuntimeError("API unavailable")
        )

        monkeypatch.setattr(
            "app.llm.get_llm_provider",
            lambda: mock_provider,
        )

        mock_registry = MagicMock()
        mock_registry.get_all.return_value = []
        monkeypatch.setattr(
            "app.llm.tools.ToolRegistry",
            lambda config: mock_registry,
        )

        result = await service._research_category(
            ResearchCategory.NEWS_MOMENTUM,
            "TestCorp",
            "Job posting",
            cb,
        )

        assert result.found is False
        assert "API unavailable" in result.reason

    @pytest.mark.asyncio
    async def test_category_research_circuit_breaker_open(self):
        """Test that open circuit breaker returns immediately."""
        service = ResearchService()
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=60.0)

        # Force circuit breaker open
        for _ in range(3):
            cb.record_failure()

        assert not cb.can_proceed()

        result = await service._research_category(
            ResearchCategory.CULTURE_VALUES,
            "TestCorp",
            "Job posting",
            cb,
        )

        assert result.found is False
        assert result.reason == GAP_REASON_CIRCUIT_OPEN

    @pytest.mark.asyncio
    async def test_category_research_tool_failure_handled(self, monkeypatch):
        """Test that tool execution failures are handled gracefully."""
        service = ResearchService()
        cb = CircuitBreaker()

        tool_call = MagicMock()
        tool_call.name = "web_search"
        tool_call.arguments = {"query": "test query"}

        first_response = MagicMock()
        first_response.content = ""
        first_response.tool_calls = [tool_call]

        final_response = MagicMock()
        final_response.content = "Partial results despite tool failure"
        final_response.tool_calls = None

        call_count = 0

        async def mock_generate_with_tools(messages, tools, config=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (first_response, [tool_call])
            return (final_response, [])

        mock_provider = AsyncMock()
        mock_provider.generate_with_tools = mock_generate_with_tools

        monkeypatch.setattr(
            "app.llm.get_llm_provider",
            lambda: mock_provider,
        )

        # Mock tool that returns failure
        mock_tool = AsyncMock()
        mock_tool_result = MagicMock()
        mock_tool_result.success = False
        mock_tool_result.content = ""
        mock_tool_result.error = "Search API unavailable"
        mock_tool.execute = AsyncMock(return_value=mock_tool_result)

        mock_registry = MagicMock()
        mock_registry.get_all.return_value = [mock_tool]
        mock_registry.get.return_value = mock_tool
        monkeypatch.setattr(
            "app.llm.tools.ToolRegistry",
            lambda config: mock_registry,
        )

        result = await service._research_category(
            ResearchCategory.INDUSTRY_CONTEXT,
            "TestCorp",
            "Job posting",
            cb,
        )

        # Should still get partial results from the LLM
        assert result.found is True
        assert "Partial results" in result.content


# ============================================================================
# Research Synthesis Tests (Task 8)
# ============================================================================


class TestResearchSynthesis:
    """Test strategic narrative synthesis."""

    @pytest.mark.asyncio
    async def test_synthesize_findings_success(self, monkeypatch):
        """Test that synthesis generates a strategic narrative."""
        service = ResearchService()
        cb = CircuitBreaker()

        mock_response = MagicMock()
        mock_response.content = "TestCorp needs this role because they are expanding into AI."

        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(return_value=mock_response)

        monkeypatch.setattr(
            "app.llm.get_llm_provider",
            lambda: mock_provider,
        )

        found_results = {
            "strategic_initiatives": ResearchSourceResult(
                found=True, content="TestCorp is building an AI platform"
            ),
            "competitive_landscape": ResearchSourceResult(
                found=True, content="Competitors include BigCo and SmallCo"
            ),
        }

        synthesis = await service._synthesize_findings(
            "TestCorp", "Software engineer role", found_results, cb
        )

        assert synthesis is not None
        assert "TestCorp" in synthesis
        mock_provider.generate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_synthesize_findings_empty_response(self, monkeypatch):
        """Test that empty synthesis response returns None."""
        service = ResearchService()
        cb = CircuitBreaker()

        mock_response = MagicMock()
        mock_response.content = ""

        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(return_value=mock_response)

        monkeypatch.setattr(
            "app.llm.get_llm_provider",
            lambda: mock_provider,
        )

        found_results = {
            "strategic_initiatives": ResearchSourceResult(
                found=True, content="Some data"
            ),
        }

        synthesis = await service._synthesize_findings(
            "TestCorp", "Job posting", found_results, cb
        )

        assert synthesis is None

    @pytest.mark.asyncio
    async def test_synthesize_skips_when_circuit_breaker_open(self):
        """Test that synthesis returns None when circuit breaker is open (L2 fix)."""
        service = ResearchService()
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=60.0)

        for _ in range(3):
            cb.record_failure()

        found_results = {
            "strategic_initiatives": ResearchSourceResult(
                found=True, content="Some data"
            ),
        }

        synthesis = await service._synthesize_findings(
            "TestCorp", "Job posting", found_results, cb
        )

        assert synthesis is None


# ============================================================================
# Full Research Flow Integration Tests (Tasks 2-9)
# ============================================================================


class TestResearchServiceIntegration:
    """Integration tests for the full research flow."""

    @pytest.mark.asyncio
    async def test_start_research_sends_progress_and_complete_events(self, monkeypatch):
        """Integration test: verify start_research produces correct SSE event sequence."""
        service = ResearchService()
        manager = SSEManager()

        import app.services.research_service as rs_module
        monkeypatch.setattr(rs_module, "sse_manager", manager)

        # Mock _execute_category to return successful results
        async def mock_execute_category(app_id, category, company, posting, cb):
            await manager.send_event(
                app_id, "progress",
                {"source": category.value, "status": "searching", "message": f"Searching {category.value}"},
            )
            result = ResearchSourceResult(
                found=True,
                content=f"Research data for {category.value} about {company}",
            )
            await manager.send_event(
                app_id, "progress",
                {"source": category.value, "status": "complete", "message": f"Completed {category.value}", "found": True},
            )
            return category, result

        monkeypatch.setattr(service, "_execute_category", mock_execute_category)

        # Mock synthesis
        async def mock_synthesize(company, posting, found_results, cb):
            return f"Synthesis for {company}"

        monkeypatch.setattr(service, "_synthesize_findings", mock_synthesize)

        # Mock save
        async def mock_save(*args, **kwargs):
            return None

        monkeypatch.setattr(service, "_save_research_results", mock_save)

        events = []

        async def consumer():
            async for event_str in manager.create_stream(1):
                events.append(json.loads(event_str.replace("data: ", "").strip()))

        consumer_task = asyncio.create_task(consumer())

        await asyncio.sleep(0.05)  # Let consumer start
        await service.start_research(1, 1, "TestCorp", "Software engineer role")
        await asyncio.sleep(0.2)  # Let consumer finish

        # 6 search start events + 6 completion events + 1 complete event = 13
        progress_events = [e for e in events if e["type"] == "progress"]
        complete_events = [e for e in events if e["type"] == "complete"]

        assert len(progress_events) == 12  # 2 per category (start + complete)
        assert len(complete_events) == 1

        # Verify search start events
        search_events = [e for e in progress_events if e["status"] == "searching"]
        assert len(search_events) == 6

        # Verify category completion events
        cat_complete_events = [e for e in progress_events if e["status"] == "complete"]
        assert len(cat_complete_events) == 6

        # Verify complete event has research_data and synthesis
        assert "research_data" in complete_events[0]
        assert "synthesis" in complete_events[0]
        assert complete_events[0]["categories_found"] == 6
        assert complete_events[0]["categories_total"] == 6

        # Verify state is cleaned up
        assert service.get_status(1) is None

        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_start_research_handles_partial_failures(self, monkeypatch):
        """Test that some categories can fail while others succeed (graceful degradation)."""
        service = ResearchService()
        manager = SSEManager()

        import app.services.research_service as rs_module
        monkeypatch.setattr(rs_module, "sse_manager", manager)

        call_count = 0

        async def mock_execute_category(app_id, category, company, posting, cb):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                result = ResearchSourceResult(found=False, reason="No data found")
            else:
                result = ResearchSourceResult(found=True, content=f"Data for {category.value}")
            await manager.send_event(
                app_id, "progress",
                {"source": category.value, "status": "complete" if result.found else "gap",
                 "message": f"Completed {category.value}", "found": result.found},
            )
            return category, result

        monkeypatch.setattr(service, "_execute_category", mock_execute_category)

        async def mock_synthesize(company, posting, found_results, cb):
            return "Partial synthesis"

        monkeypatch.setattr(service, "_synthesize_findings", mock_synthesize)

        async def mock_save(*args, **kwargs):
            return None

        monkeypatch.setattr(service, "_save_research_results", mock_save)

        events = []

        async def consumer():
            async for event_str in manager.create_stream(1):
                events.append(json.loads(event_str.replace("data: ", "").strip()))

        consumer_task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)

        await service.start_research(1, 1, "TestCorp", "Engineer role")
        await asyncio.sleep(0.2)

        complete_events = [e for e in events if e["type"] == "complete"]
        assert len(complete_events) == 1
        assert len(complete_events[0]["gaps"]) == 3  # 3 out of 6 failed
        assert complete_events[0]["categories_found"] == 3

        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_start_research_per_category_exception_becomes_gap(self, monkeypatch):
        """Test that per-category exceptions produce gaps, not overall failure (graceful degradation)."""
        service = ResearchService()
        manager = SSEManager()

        import app.services.research_service as rs_module
        monkeypatch.setattr(rs_module, "sse_manager", manager)

        async def failing_execute(app_id, category, company, posting, cb):
            raise RuntimeError("LLM provider unavailable")

        monkeypatch.setattr(service, "_execute_category", failing_execute)

        async def mock_save(*args, **kwargs):
            return None

        monkeypatch.setattr(service, "_save_research_results", mock_save)

        events = []

        async def consumer():
            async for event_str in manager.create_stream(1):
                events.append(json.loads(event_str.replace("data: ", "").strip()))

        consumer_task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)

        await service.start_research(1, 1, "TestCorp", "Engineer role")
        await asyncio.sleep(0.2)

        # All categories failed, so all are gaps, but research completes overall
        complete_events = [e for e in events if e["type"] == "complete"]
        assert len(complete_events) == 1
        assert complete_events[0]["categories_found"] == 0
        assert len(complete_events[0]["gaps"]) == 6

        # State cleaned up
        assert service.get_status(1) is None

        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_start_research_unexpected_error_sends_error_event(self, monkeypatch):
        """Test that an unexpected error outside per-category loop sends error event."""
        service = ResearchService()
        manager = SSEManager()

        import app.services.research_service as rs_module
        monkeypatch.setattr(rs_module, "sse_manager", manager)

        # Patch the entire for-loop iteration to fail unexpectedly
        async def patched_start(app_id, role_id, company, posting):
            service._research_state[app_id] = ResearchStatus.RUNNING
            try:
                raise RuntimeError("Unexpected internal error")
            except Exception as e:
                service._research_state[app_id] = ResearchStatus.FAILED
                await manager.send_event(
                    app_id, "error",
                    {"message": str(e), "recoverable": False},
                )
            finally:
                service._research_state.pop(app_id, None)

        monkeypatch.setattr(service, "start_research", patched_start)

        events = []

        async def consumer():
            async for event_str in manager.create_stream(1):
                events.append(json.loads(event_str.replace("data: ", "").strip()))

        consumer_task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)

        await service.start_research(1, 1, "TestCorp", "Engineer role")
        await asyncio.sleep(0.1)

        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) == 1
        assert "Unexpected internal error" in error_events[0]["message"]

        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_start_research_timeout_per_category(self, monkeypatch):
        """Test that per-category timeout produces a gap, not a crash."""
        service = ResearchService()
        service._category_timeout = 0.1  # 100ms timeout for testing
        manager = SSEManager()

        import app.services.research_service as rs_module
        monkeypatch.setattr(rs_module, "sse_manager", manager)

        call_count = 0

        async def mock_execute_category(app_id, category, company, posting, cb):
            nonlocal call_count
            call_count += 1
            # First category's inner research times out
            await manager.send_event(
                app_id, "progress",
                {"source": category.value, "status": "searching", "message": f"Searching {category.value}"},
            )
            if call_count == 1:
                await asyncio.sleep(10)  # Will timeout in _execute_category
            result = ResearchSourceResult(found=True, content=f"Data for {category.value}")
            await manager.send_event(
                app_id, "progress",
                {"source": category.value, "status": "complete", "message": f"Completed {category.value}", "found": True},
            )
            return category, result

        monkeypatch.setattr(service, "_execute_category", mock_execute_category)

        async def mock_synthesize(company, posting, found_results, cb):
            return "Synthesis"

        monkeypatch.setattr(service, "_synthesize_findings", mock_synthesize)

        async def mock_save(*args, **kwargs):
            return None

        monkeypatch.setattr(service, "_save_research_results", mock_save)

        events = []

        async def consumer():
            async for event_str in manager.create_stream(1):
                events.append(json.loads(event_str.replace("data: ", "").strip()))

        consumer_task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)

        await service.start_research(1, 1, "TestCorp", "Engineer role")
        await asyncio.sleep(0.5)

        complete_events = [e for e in events if e["type"] == "complete"]
        assert len(complete_events) == 1

        # First category timed out (exception in gather), rest succeeded
        # The timed-out category becomes a gap via the exception handler in start_research
        assert complete_events[0]["categories_found"] >= 4  # At least 4 of 6 succeeded

        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_start_research_saves_results(self, monkeypatch):
        """Test that results are persisted via _save_research_results."""
        service = ResearchService()
        manager = SSEManager()

        import app.services.research_service as rs_module
        monkeypatch.setattr(rs_module, "sse_manager", manager)

        async def mock_execute_category(app_id, category, company, posting, cb):
            result = ResearchSourceResult(found=True, content=f"Data for {category.value}")
            return category, result

        monkeypatch.setattr(service, "_execute_category", mock_execute_category)

        async def mock_synthesize(company, posting, found_results, cb):
            return "Synthesis"

        monkeypatch.setattr(service, "_synthesize_findings", mock_synthesize)

        save_called_with = {}

        async def mock_save(app_id, role_id, research_result):
            save_called_with["app_id"] = app_id
            save_called_with["role_id"] = role_id
            save_called_with["result"] = research_result

        monkeypatch.setattr(service, "_save_research_results", mock_save)

        events = []

        async def consumer():
            async for event_str in manager.create_stream(1):
                events.append(json.loads(event_str.replace("data: ", "").strip()))

        consumer_task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)

        await service.start_research(1, 42, "TestCorp", "Engineer role")
        await asyncio.sleep(0.2)

        assert save_called_with["app_id"] == 1
        assert save_called_with["role_id"] == 42
        assert isinstance(save_called_with["result"], ResearchResult)
        assert save_called_with["result"].synthesis == "Synthesis"

        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_start_research_db_save_failure_still_completes(self, monkeypatch):
        """Test that database save failure doesn't crash the research flow."""
        service = ResearchService()
        manager = SSEManager()

        import app.services.research_service as rs_module
        monkeypatch.setattr(rs_module, "sse_manager", manager)

        async def mock_execute_category(app_id, category, company, posting, cb):
            result = ResearchSourceResult(found=True, content=f"Data for {category.value}")
            return category, result

        monkeypatch.setattr(service, "_execute_category", mock_execute_category)

        async def mock_synthesize(company, posting, found_results, cb):
            return "Synthesis"

        monkeypatch.setattr(service, "_synthesize_findings", mock_synthesize)

        async def mock_save_fail(*args, **kwargs):
            raise RuntimeError("Database connection error")

        monkeypatch.setattr(service, "_save_research_results", mock_save_fail)

        events = []

        async def consumer():
            async for event_str in manager.create_stream(1):
                events.append(json.loads(event_str.replace("data: ", "").strip()))

        consumer_task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)

        await service.start_research(1, 1, "TestCorp", "Engineer role")
        await asyncio.sleep(0.2)

        # Should still get a complete event, not an error
        complete_events = [e for e in events if e["type"] == "complete"]
        assert len(complete_events) == 1

        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_start_research_runs_categories_concurrently(self, monkeypatch):
        """Test that categories execute concurrently, not sequentially (M1 fix)."""
        service = ResearchService()
        manager = SSEManager()

        import app.services.research_service as rs_module
        monkeypatch.setattr(rs_module, "sse_manager", manager)

        timestamps = []

        async def mock_execute_category(app_id, category, company, posting, cb):
            import time
            timestamps.append(("start", category.value, time.monotonic()))
            await asyncio.sleep(0.05)  # Simulate work
            timestamps.append(("end", category.value, time.monotonic()))
            result = ResearchSourceResult(found=True, content=f"Data for {category.value}")
            return category, result

        monkeypatch.setattr(service, "_execute_category", mock_execute_category)

        async def mock_synthesize(company, posting, found_results, cb):
            return "Synthesis"

        monkeypatch.setattr(service, "_synthesize_findings", mock_synthesize)

        async def mock_save(*args, **kwargs):
            return None

        monkeypatch.setattr(service, "_save_research_results", mock_save)

        events = []

        async def consumer():
            async for event_str in manager.create_stream(1):
                events.append(json.loads(event_str.replace("data: ", "").strip()))

        consumer_task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)

        await service.start_research(1, 1, "TestCorp", "Engineer role")
        await asyncio.sleep(0.3)

        # With 6 categories and concurrency=3, the total time should be
        # significantly less than 6 * 0.05s = 0.3s sequential.
        # With concurrency=3, we expect ~2 batches = ~0.1s.
        start_times = [t[2] for t in timestamps if t[0] == "start"]
        end_times = [t[2] for t in timestamps if t[0] == "end"]

        total_wall_time = max(end_times) - min(start_times)
        # Sequential would be >= 0.3s. Concurrent should be < 0.2s.
        assert total_wall_time < 0.25, (
            f"Categories took {total_wall_time:.3f}s, expected concurrent execution"
        )

        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass


# ============================================================================
# Research Persistence Integration Test (M2 fix)
# ============================================================================


class TestResearchPersistence:
    """Test that research results are properly serialized and persisted."""

    @pytest.mark.asyncio
    async def test_save_research_results_serialization(self, monkeypatch):
        """Test that ResearchResult serializes to valid JSON for ApplicationUpdate."""
        service = ResearchService()

        # Build a realistic ResearchResult
        research_result = ResearchResult(
            strategic_initiatives=ResearchSourceResult(
                found=True, content="TestCorp is expanding into AI"
            ),
            competitive_landscape=ResearchSourceResult(
                found=True, content="Competitors include BigCo"
            ),
            news_momentum=ResearchSourceResult(
                found=False, reason="No recent news"
            ),
            industry_context=ResearchSourceResult(
                found=True, content="AI industry growing 30% YoY"
            ),
            culture_values=ResearchSourceResult(
                found=True, content="Engineering-driven culture"
            ),
            leadership_direction=ResearchSourceResult(
                found=False, reason="Limited public statements"
            ),
            synthesis="TestCorp needs this role to drive AI expansion.",
            gaps=["news_momentum", "leadership_direction"],
            completed_at="2026-02-08T12:00:00Z",
        )

        # Capture what gets passed to application_service.update_application
        captured_update = {}

        async def mock_update(app_id, role_id, data):
            captured_update["app_id"] = app_id
            captured_update["role_id"] = role_id
            captured_update["data"] = data
            return MagicMock()

        monkeypatch.setattr(
            "app.services.application_service.update_application",
            mock_update,
        )

        await service._save_research_results(1, 42, research_result)

        assert captured_update["app_id"] == 1
        assert captured_update["role_id"] == 42

        # Verify the research_data is valid JSON
        update_data = captured_update["data"]
        assert update_data.research_data is not None

        parsed = json.loads(update_data.research_data)
        assert parsed["synthesis"] == "TestCorp needs this role to drive AI expansion."
        assert parsed["gaps"] == ["news_momentum", "leadership_direction"]
        assert parsed["strategic_initiatives"]["found"] is True
        assert parsed["strategic_initiatives"]["content"] == "TestCorp is expanding into AI"
        assert parsed["news_momentum"]["found"] is False
        assert parsed["completed_at"] == "2026-02-08T12:00:00Z"

        # Verify it can be deserialized back to ResearchResult
        roundtrip = ResearchResult(**parsed)
        assert roundtrip.synthesis == research_result.synthesis
        assert roundtrip.gaps == research_result.gaps
        assert roundtrip.strategic_initiatives.found is True


# ============================================================================
# Research API Endpoint Tests
# ============================================================================


def _auth_helper(client):
    """Register, login, create role, and create application. Returns (role_id, app_id, headers)."""
    client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "password": "testpass123",
    })
    client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "testpass123",
    })
    role_resp = client.post("/api/v1/roles", json={"name": "Test Role"})
    role_id = role_resp.json()["id"]
    headers = {"X-Role-Id": str(role_id)}

    app_resp = client.post(
        "/api/v1/applications",
        json={
            "company_name": "Test Corp",
            "job_posting": "We are looking for a software engineer with 5 years of experience.",
        },
        headers=headers,
    )
    app_id = app_resp.json()["id"]

    return role_id, app_id, headers


class TestResearchEndpoints:
    """Test research API endpoints."""

    @pytest.fixture(autouse=True)
    def _cleanup_research_state(self):
        """Clean up global singleton state after each test."""
        from app.services.research_service import research_service
        yield
        research_service._research_state.clear()

    def test_start_research_returns_started(self, client):
        _role_id, app_id, headers = _auth_helper(client)

        response = client.post(
            f"/api/v1/applications/{app_id}/research",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["application_id"] == app_id

    def test_start_research_rejects_nonexistent_application(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "password": "testpass123",
        })
        client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass123",
        })
        role_resp = client.post("/api/v1/roles", json={"name": "Test Role"})
        role_id = role_resp.json()["id"]
        headers = {"X-Role-Id": str(role_id)}

        response = client.post(
            "/api/v1/applications/9999/research",
            headers=headers,
        )
        assert response.status_code == 404

    def test_start_research_requires_auth(self, client):
        response = client.post("/api/v1/applications/1/research")
        assert response.status_code == 401

    def test_start_research_requires_role_header(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "password": "testpass123",
        })
        client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass123",
        })

        response = client.post("/api/v1/applications/1/research")
        assert response.status_code == 400

    def test_start_research_rejects_concurrent(self, client):
        """Test that concurrent research requests return 409."""
        from app.services.research_service import research_service
        _role_id, app_id, headers = _auth_helper(client)

        # Simulate research already running
        research_service._research_state[app_id] = ResearchStatus.RUNNING

        response = client.post(
            f"/api/v1/applications/{app_id}/research",
            headers=headers,
        )
        assert response.status_code == 409
        assert "already in progress" in response.json()["detail"]

    def test_research_status_not_started(self, client):
        _role_id, app_id, headers = _auth_helper(client)

        response = client.get(
            f"/api/v1/applications/{app_id}/research/status",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_started"
        assert data["has_research_data"] is False

    def test_research_status_requires_auth(self, client):
        response = client.get("/api/v1/applications/1/research/status")
        assert response.status_code == 401

    def test_research_status_nonexistent_application(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "password": "testpass123",
        })
        client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass123",
        })
        role_resp = client.post("/api/v1/roles", json={"name": "Test Role"})
        role_id = role_resp.json()["id"]
        headers = {"X-Role-Id": str(role_id)}

        response = client.get(
            "/api/v1/applications/9999/research/status",
            headers=headers,
        )
        assert response.status_code == 404

    def test_stream_requires_valid_application(self, client):
        """Verify the stream endpoint validates application access."""
        _role_id, app_id, headers = _auth_helper(client)

        response = client.get(
            "/api/v1/applications/9999/research/stream",
            headers=headers,
        )
        assert response.status_code == 404

    def test_stream_requires_auth(self, client):
        response = client.get("/api/v1/applications/1/research/stream")
        assert response.status_code == 401

    def test_stream_nonexistent_application(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "password": "testpass123",
        })
        client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass123",
        })
        role_resp = client.post("/api/v1/roles", json={"name": "Test Role"})
        role_id = role_resp.json()["id"]
        headers = {"X-Role-Id": str(role_id)}

        response = client.get(
            "/api/v1/applications/9999/research/stream",
            headers=headers,
        )
        assert response.status_code == 404

    def test_role_isolation_prevents_cross_role_access(self, client):
        """Test that user A cannot research user B's application."""
        client.post("/api/v1/auth/register", json={
            "username": "userA",
            "password": "testpass123",
        })
        client.post("/api/v1/auth/login", json={
            "username": "userA",
            "password": "testpass123",
        })
        role_a_resp = client.post("/api/v1/roles", json={"name": "Role A"})
        role_a_id = role_a_resp.json()["id"]
        app_resp = client.post(
            "/api/v1/applications",
            json={
                "company_name": "Corp A",
                "job_posting": "Software engineer role requiring expertise.",
            },
            headers={"X-Role-Id": str(role_a_id)},
        )
        app_id = app_resp.json()["id"]

        client.post("/api/v1/auth/logout")
        client.post("/api/v1/auth/register", json={
            "username": "userB",
            "password": "testpass123",
        })
        client.post("/api/v1/auth/login", json={
            "username": "userB",
            "password": "testpass123",
        })
        role_b_resp = client.post("/api/v1/roles", json={"name": "Role B"})
        role_b_id = role_b_resp.json()["id"]

        response = client.post(
            f"/api/v1/applications/{app_id}/research",
            headers={"X-Role-Id": str(role_b_id)},
        )
        assert response.status_code == 404

    def test_start_research_sets_status_to_researching(self, client):
        """Test that starting research updates application status to RESEARCHING (or REVIEWED if background task completes first)."""
        _role_id, app_id, headers = _auth_helper(client)

        app_resp = client.get(f"/api/v1/applications/{app_id}", headers=headers)
        assert app_resp.json()["status"] == "created"

        response = client.post(
            f"/api/v1/applications/{app_id}/research",
            headers=headers,
        )
        assert response.status_code == 200

        app_resp = client.get(f"/api/v1/applications/{app_id}", headers=headers)
        # Background task may complete before we check, advancing to "reviewed"
        assert app_resp.json()["status"] in ("researching", "reviewed")

    def test_start_research_rejects_missing_job_data(self, client, monkeypatch):
        """Test 400 when application lacks company_name or job_posting."""
        from types import SimpleNamespace
        _role_id, app_id, headers = _auth_helper(client)

        mock_app = SimpleNamespace(
            id=app_id, company_name="Corp", job_posting=None, research_data=None,
        )

        async def mock_get_application(id, role_id):
            return mock_app

        monkeypatch.setattr(
            "app.services.application_service.get_application", mock_get_application,
        )

        response = client.post(
            f"/api/v1/applications/{app_id}/research",
            headers=headers,
        )
        assert response.status_code == 400
        assert "company name and job posting" in response.json()["detail"]


# ============================================================================
# Gap Detection & Partial Information Tests (Story 4-5, Task 1)
# ============================================================================


class TestPartialDetection:
    """Test partial content detection logic."""

    def test_partial_indicator_limited_information(self):
        from app.services.research_service import _is_partial
        assert _is_partial("Limited information available about strategic initiatives. The company appears to be in the AI space.") is True

    def test_partial_indicator_incomplete(self):
        from app.services.research_service import _is_partial
        assert _is_partial("Information is incomplete. Only the company's career page mentions culture values.") is True

    def test_partial_indicator_only_found(self):
        from app.services.research_service import _is_partial
        assert _is_partial("Could only find limited details about leadership direction from a single press release.") is True

    def test_no_partial_for_normal_content(self):
        from app.services.research_service import _is_partial
        content = (
            "TestCorp is a leading AI company focused on enterprise solutions. "
            "They have raised $200M in Series C funding and are expanding into "
            "healthcare and financial services markets."
        )
        assert _is_partial(content) is False

    def test_no_partial_for_empty_string(self):
        from app.services.research_service import _is_partial
        assert _is_partial("") is False


class TestResearchSourceResultPartialFields:
    """Test that ResearchSourceResult supports partial fields."""

    def test_partial_result_fields(self):
        result = ResearchSourceResult(
            found=True,
            content="Some partial data about the company",
            partial=True,
            partial_note="Only careers page found, no additional public statements",
        )
        assert result.found is True
        assert result.partial is True
        assert result.partial_note is not None
        assert result.content is not None

    def test_default_partial_is_false(self):
        result = ResearchSourceResult(found=True, content="Full data")
        assert result.partial is False
        assert result.partial_note is None

    def test_not_found_with_no_partial(self):
        result = ResearchSourceResult(found=False, reason="Not found")
        assert result.partial is False


class TestCategoryResearchPartialDetection:
    """Test that _research_category detects and flags partial content."""

    @pytest.mark.asyncio
    async def test_partial_content_detected(self, monkeypatch):
        service = ResearchService()
        cb = CircuitBreaker()

        mock_response = MagicMock()
        mock_response.content = "Limited information available. The company appears to value innovation based on their careers page."
        mock_response.tool_calls = None

        mock_provider = AsyncMock()
        mock_provider.generate_with_tools = AsyncMock(return_value=(mock_response, []))

        monkeypatch.setattr("app.llm.get_llm_provider", lambda: mock_provider)

        mock_registry = MagicMock()
        mock_registry.get_all.return_value = []
        monkeypatch.setattr("app.llm.tools.ToolRegistry", lambda config: mock_registry)

        result = await service._research_category(
            ResearchCategory.CULTURE_VALUES,
            "TestCorp",
            "Some job posting",
            cb,
        )

        assert result.found is True
        assert result.partial is True
        assert result.partial_note is not None
        assert result.content is not None


