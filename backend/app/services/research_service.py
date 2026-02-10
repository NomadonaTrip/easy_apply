"""Research service for orchestrating company research with progress streaming."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from app.llm.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.llm.rate_pacer import RatePacer
from app.models.application import ApplicationUpdate, ApplicationStatus
from app.models.research import ResearchStatus, ResearchCategory, ResearchResult, ResearchSourceResult
from app.services.sse_manager import sse_manager
from app.services import application_service

logger = logging.getLogger(__name__)

# Map categories to their registered prompt names
CATEGORY_PROMPT_NAMES = {
    ResearchCategory.STRATEGIC_INITIATIVES: "research_strategic_initiatives",
    ResearchCategory.COMPETITIVE_LANDSCAPE: "research_competitive_landscape",
    ResearchCategory.NEWS_MOMENTUM: "research_news_momentum",
    ResearchCategory.INDUSTRY_CONTEXT: "research_industry_context",
    ResearchCategory.CULTURE_VALUES: "research_culture_values",
    ResearchCategory.LEADERSHIP_DIRECTION: "research_leadership_direction",
}

CATEGORY_MESSAGES = {
    ResearchCategory.STRATEGIC_INITIATIVES: "Investigating strategic initiatives...",
    ResearchCategory.COMPETITIVE_LANDSCAPE: "Analyzing competitive landscape...",
    ResearchCategory.NEWS_MOMENTUM: "Searching recent news and momentum...",
    ResearchCategory.INDUSTRY_CONTEXT: "Researching industry context...",
    ResearchCategory.CULTURE_VALUES: "Researching company culture and values...",
    ResearchCategory.LEADERSHIP_DIRECTION: "Analyzing leadership direction...",
}

# Static mapping of which prompt kwargs each category needs.
# Avoids inspecting template strings at runtime (H3 fix).
CATEGORY_PROMPT_KWARGS = {
    ResearchCategory.STRATEGIC_INITIATIVES: ["company_name", "job_posting_summary"],
    ResearchCategory.COMPETITIVE_LANDSCAPE: ["company_name", "job_posting_summary"],
    ResearchCategory.NEWS_MOMENTUM: ["company_name"],
    ResearchCategory.INDUSTRY_CONTEXT: ["company_name", "job_posting_summary"],
    ResearchCategory.CULTURE_VALUES: ["company_name"],
    ResearchCategory.LEADERSHIP_DIRECTION: ["company_name", "job_posting_summary"],
}

# Max concurrent LLM calls during research (rate pacer still applies)
_RESEARCH_CONCURRENCY = 3

# Not-found detection: response must be SHORT and dominated by not-found language.
# Long responses containing these phrases incidentally are clearly real content (H4 fix).
_NOT_FOUND_MAX_LENGTH = 500

# Human-readable labels for research categories (used in partial notes and gap reasons)
CATEGORY_LABELS = {
    ResearchCategory.STRATEGIC_INITIATIVES: "Strategic Initiatives",
    ResearchCategory.COMPETITIVE_LANDSCAPE: "Competitive Landscape",
    ResearchCategory.NEWS_MOMENTUM: "Recent News & Momentum",
    ResearchCategory.INDUSTRY_CONTEXT: "Industry Context",
    ResearchCategory.CULTURE_VALUES: "Culture & Values",
    ResearchCategory.LEADERSHIP_DIRECTION: "Leadership Direction",
}

# Standardized gap reason constants for predictable frontend consumption
GAP_REASON_TIMEOUT = "Research timed out"
GAP_REASON_CIRCUIT_OPEN = "Too many recent failures — research paused"
GAP_REASON_NO_RESULTS = "No results returned from research"
GAP_REASON_ERROR_PREFIX = "Research error"
GAP_REASON_TASK_FAILED = "Category research failed unexpectedly"
NOT_FOUND_INDICATORS = [
    "no information found",
    "could not find",
    "no public information",
    "not found",
    "unavailable",
    "no results",
    "unable to find",
    "no relevant information",
]

# Partial detection: higher threshold than not-found (2000 chars) since partial
# content is expected to be longer, but guards against very long content that
# incidentally contains partial phrases (Code Review fix M1).
_PARTIAL_MAX_LENGTH = 2000

PARTIAL_INDICATORS = [
    "limited information available",
    "only limited information",
    "information is incomplete",
    "incomplete data",
    "partial results",
    "could only find limited",
    "limited public information",
    "only found limited",
]


def _is_not_found(content: str) -> bool:
    """Determine if LLM response indicates no useful content was found.

    Only flags short responses dominated by not-found language.
    Long detailed responses that incidentally contain these phrases are real content.
    """
    if len(content) > _NOT_FOUND_MAX_LENGTH:
        return False
    content_lower = content.lower()
    return any(indicator in content_lower for indicator in NOT_FOUND_INDICATORS)


def _is_partial(content: str) -> bool:
    """Determine if LLM response indicates partial/incomplete information.

    Uses a length guard (_PARTIAL_MAX_LENGTH) to avoid false positives on very
    long content that incidentally contains partial phrases. The threshold is
    higher than not-found detection because partial responses can be more
    detailed while still explicitly flagging incompleteness.
    """
    if not content:
        return False
    if len(content) > _PARTIAL_MAX_LENGTH:
        return False
    content_lower = content.lower()
    return any(indicator in content_lower for indicator in PARTIAL_INDICATORS)


class ResearchService:
    """Orchestrates strategic company research with LLM Provider and tools."""

    def __init__(self):
        self._research_state: dict[int, ResearchStatus] = {}
        self._category_timeout = 180  # 3 minutes per category
        self._rate_pacer = RatePacer(min_interval_seconds=1.0)

    def get_status(self, application_id: int) -> Optional[ResearchStatus]:
        """Get current research status for an application."""
        return self._research_state.get(application_id)

    def is_running(self, application_id: int) -> bool:
        """Check if research is currently running."""
        return self._research_state.get(application_id) == ResearchStatus.RUNNING

    async def cancel_research(self, application_id: int) -> bool:
        """Cancel running research for an application.

        Returns True if research was running and cancelled, False otherwise.
        Designed to be called when an application is deleted or user cancels.
        """
        if not self.is_running(application_id):
            return False

        self._research_state[application_id] = ResearchStatus.FAILED
        await sse_manager.send_event(
            application_id,
            "error",
            {"message": "Research cancelled", "recoverable": False},
        )
        sse_manager.close_stream(application_id)
        self._research_state.pop(application_id, None)
        return True

    async def start_research(
        self,
        application_id: int,
        role_id: int,
        company_name: str,
        job_posting: str,
    ) -> None:
        """Start research process with progress streaming.

        This method is designed to run as a background task.
        It streams progress events via SSE and persists results to the database.
        Categories execute concurrently (bounded by semaphore) for faster results.
        """
        self._research_state[application_id] = ResearchStatus.RUNNING

        # Per-session circuit breaker so transient failures don't cascade
        # across all categories within a single research run (M3 fix).
        circuit_breaker = CircuitBreaker(failure_threshold=3, reset_timeout=60.0)
        semaphore = asyncio.Semaphore(_RESEARCH_CONCURRENCY)

        try:
            # Launch all categories concurrently with bounded concurrency (M1 fix)
            async def _run_category(category: ResearchCategory) -> tuple[ResearchCategory, ResearchSourceResult]:
                async with semaphore:
                    return await self._execute_category(
                        application_id, category, company_name, job_posting, circuit_breaker
                    )

            category_results = await asyncio.gather(
                *[_run_category(cat) for cat in ResearchCategory],
                return_exceptions=True,
            )

            # Collect results, handling any unexpected exceptions from gather
            results: dict[str, ResearchSourceResult] = {}
            gaps: list[str] = []

            for item in category_results:
                if isinstance(item, Exception):
                    logger.error("Unexpected error in category task: %s", item)
                    continue
                category, result = item
                results[category.value] = result
                if not result.found:
                    gaps.append(category.value)

            # Fill in any categories that were lost to exceptions
            for cat in ResearchCategory:
                if cat.value not in results:
                    results[cat.value] = ResearchSourceResult(
                        found=False, reason=GAP_REASON_TASK_FAILED
                    )
                    gaps.append(cat.value)

            # Synthesize strategic narrative from all findings
            synthesis = None
            found_results = {
                k: v for k, v in results.items() if v.found and v.content
            }
            if found_results:
                try:
                    synthesis = await asyncio.wait_for(
                        self._synthesize_findings(
                            company_name, job_posting, found_results, circuit_breaker
                        ),
                        timeout=self._category_timeout,
                    )
                except Exception as e:
                    logger.error(
                        "Error synthesizing research for application %d: %s",
                        application_id, e,
                    )

            # Build research result
            research_result = ResearchResult(
                gaps=gaps,
                synthesis=synthesis,
                completed_at=datetime.now(timezone.utc).isoformat(),
                **{cat.value: results[cat.value] for cat in ResearchCategory if cat.value in results},
            )

            # Persist research data to application
            try:
                await self._save_research_results(
                    application_id, role_id, research_result
                )
                # Advance status so frontend knows research is done
                await application_service.update_application(
                    application_id, role_id,
                    ApplicationUpdate(status=ApplicationStatus.REVIEWED),
                )
            except Exception as db_err:
                logger.error(
                    "Failed to persist research results for application %d: %s",
                    application_id, db_err,
                )

            self._research_state[application_id] = ResearchStatus.COMPLETE

            await sse_manager.send_event(
                application_id,
                "complete",
                {
                    "research_data": {k: v.model_dump() for k, v in results.items()},
                    "synthesis": synthesis,
                    "gaps": gaps,
                    "categories_found": len(ResearchCategory) - len(gaps),
                    "categories_total": len(ResearchCategory),
                },
            )

        except Exception as e:
            self._research_state[application_id] = ResearchStatus.FAILED
            await sse_manager.send_event(
                application_id,
                "error",
                {"message": str(e), "recoverable": False},
            )

        finally:
            self._research_state.pop(application_id, None)

    async def _execute_category(
        self,
        application_id: int,
        category: ResearchCategory,
        company_name: str,
        job_posting: str,
        circuit_breaker: CircuitBreaker,
    ) -> tuple[ResearchCategory, ResearchSourceResult]:
        """Execute a single category with SSE events, timeout, and error handling."""
        # Send progress event
        await sse_manager.send_event(
            application_id,
            "progress",
            {
                "source": category.value,
                "status": "searching",
                "message": f"{CATEGORY_MESSAGES[category]} ({company_name})",
            },
        )

        try:
            result = await asyncio.wait_for(
                self._research_category(category, company_name, job_posting, circuit_breaker),
                timeout=self._category_timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Timeout researching %s for application %d",
                category.value, application_id,
            )
            result = ResearchSourceResult(
                found=False,
                reason=f"{GAP_REASON_TIMEOUT} after {self._category_timeout}s",
            )
        except Exception as e:
            logger.error(
                "Error researching %s for application %d: %s",
                category.value, application_id, e,
            )
            result = ResearchSourceResult(
                found=False,
                reason=f"{GAP_REASON_ERROR_PREFIX}: {str(e)}",
            )

        # Send category completion
        await sse_manager.send_event(
            application_id,
            "progress",
            {
                "source": category.value,
                "status": "complete" if result.found else "gap",
                "message": f"Completed {category.value}",
                "found": result.found,
            },
        )

        return category, result

    async def _research_category(
        self,
        category: ResearchCategory,
        company_name: str,
        job_posting: str,
        circuit_breaker: CircuitBreaker,
    ) -> ResearchSourceResult:
        """Research a single strategic category using LLM Provider with tools."""
        from app.llm import get_llm_provider, Message, Role
        from app.llm.prompts import PromptRegistry
        from app.llm.tools import ToolRegistry
        from app.llm.types import GenerationConfig
        from app.config import settings
        from app.utils.llm_helpers import generate_with_tools_with_retry

        # Circuit breaker check
        if not circuit_breaker.can_proceed():
            return ResearchSourceResult(
                found=False,
                reason=GAP_REASON_CIRCUIT_OPEN,
            )

        # Rate pacing
        await self._rate_pacer.pace()

        prompt_name = CATEGORY_PROMPT_NAMES[category]

        # Build prompt via registry using static kwargs mapping (H3 fix)
        available_kwargs = {
            "company_name": company_name,
            "job_posting_summary": job_posting[:500],
        }
        needed_kwargs = CATEGORY_PROMPT_KWARGS[category]
        prompt_kwargs = {k: available_kwargs[k] for k in needed_kwargs}
        prompt = PromptRegistry.get(prompt_name, **prompt_kwargs)

        # GenerationConfig with prompt_name for observability (H2 fix)
        gen_config = GenerationConfig(prompt_name=prompt_name)

        try:
            provider = get_llm_provider()
            registry = ToolRegistry(config=settings.tool_config)
            tools = registry.get_all()

            messages = [Message(role=Role.USER, content=prompt)]

            # Tool-use loop (max 5 iterations)
            result_content = ""
            for _ in range(5):
                # Use retry wrapper for 429 handling (H1 fix)
                response, tool_calls = await generate_with_tools_with_retry(
                    provider, messages, tools, gen_config
                )

                if not tool_calls:
                    result_content = response.content
                    break

                # Execute tool calls and add results to messages
                messages.append(response)
                for tc in tool_calls:
                    tool = registry.get(tc.name)
                    tool_result = await tool.execute(**tc.arguments)
                    messages.append(Message(
                        role=Role.TOOL,
                        content=tool_result.content if tool_result.success else (tool_result.error or "Tool execution failed"),
                        tool_call_id=tc.name,
                    ))
            else:
                # Exhausted iterations, use last response
                result_content = response.content

            circuit_breaker.record_success()

            if not result_content:
                return ResearchSourceResult(
                    found=False,
                    reason=GAP_REASON_NO_RESULTS,
                )

            # Robust not-found detection (H4 fix)
            is_found = not _is_not_found(result_content)

            if not is_found:
                return ResearchSourceResult(
                    found=False,
                    content=None,
                    reason=result_content,
                )

            # Partial content detection (Story 4-5)
            is_partial_content = _is_partial(result_content)

            return ResearchSourceResult(
                found=True,
                content=result_content,
                partial=is_partial_content,
                partial_note=(
                    f"{CATEGORY_LABELS[category]}: Some information may be incomplete or outdated"
                    if is_partial_content else None
                ),
            )

        except CircuitOpenError:
            return ResearchSourceResult(
                found=False,
                reason=GAP_REASON_CIRCUIT_OPEN,
            )
        except Exception as e:
            circuit_breaker.record_failure()
            logger.error("LLM Provider error for %s: %s", category.value, e)
            return ResearchSourceResult(
                found=False,
                reason=f"{GAP_REASON_ERROR_PREFIX}: {str(e)}",
            )

    async def _synthesize_findings(
        self,
        company_name: str,
        job_posting: str,
        found_results: dict[str, ResearchSourceResult],
        circuit_breaker: CircuitBreaker,
    ) -> Optional[str]:
        """Synthesize all research findings into a strategic narrative."""
        from app.llm import get_llm_provider, Message, Role
        from app.llm.prompts import PromptRegistry
        from app.llm.types import GenerationConfig
        from app.utils.llm_helpers import generate_with_retry

        # Circuit breaker check for synthesis too (L2 fix)
        if not circuit_breaker.can_proceed():
            logger.warning("Circuit breaker open, skipping synthesis")
            return None

        # Build research findings summary for the synthesis prompt
        findings_parts = []
        for category_name, result in found_results.items():
            label = category_name.replace("_", " ").title()
            findings_parts.append(f"## {label}\n{result.content}")

        research_findings = "\n\n".join(findings_parts)

        await self._rate_pacer.pace()

        prompt = PromptRegistry.get(
            "research_synthesis",
            company_name=company_name,
            research_findings=research_findings,
            job_posting_summary=job_posting[:500],
        )

        # GenerationConfig with prompt_name for observability (H2 fix)
        gen_config = GenerationConfig(prompt_name="research_synthesis")

        try:
            provider = get_llm_provider()
            messages = [Message(role=Role.USER, content=prompt)]
            # Use retry wrapper for 429 handling (H1 fix)
            response = await generate_with_retry(provider, messages, gen_config)
            circuit_breaker.record_success()
            return response.content if response.content else None
        except Exception as e:
            circuit_breaker.record_failure()
            logger.error("Synthesis LLM error: %s", e)
            return None

    async def _save_research_results(
        self,
        application_id: int,
        role_id: int,
        research_result: ResearchResult,
    ) -> None:
        """Persist research results to the application record."""
        update_data = ApplicationUpdate(
            research_data=json.dumps(research_result.model_dump()),
        )
        await application_service.update_application(application_id, role_id, update_data)


# Global singleton instance
research_service = ResearchService()
