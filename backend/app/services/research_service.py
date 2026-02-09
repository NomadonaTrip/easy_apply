"""Research service for orchestrating company research with progress streaming."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from app.models.application import ApplicationUpdate
from app.models.research import ResearchStatus, ResearchCategory, ResearchResult, ResearchSourceResult
from app.services.sse_manager import sse_manager
from app.services import application_service

logger = logging.getLogger(__name__)


class ResearchService:
    """Orchestrates strategic company research with progress streaming."""

    def __init__(self):
        self._research_state: dict[int, ResearchStatus] = {}

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
        """
        self._research_state[application_id] = ResearchStatus.RUNNING

        try:
            categories = [
                (ResearchCategory.STRATEGIC_INITIATIVES, f"Investigating {company_name} strategic initiatives..."),
                (ResearchCategory.COMPETITIVE_LANDSCAPE, f"Analyzing {company_name} competitive landscape..."),
                (ResearchCategory.NEWS_MOMENTUM, f"Searching recent news and momentum for {company_name}..."),
                (ResearchCategory.INDUSTRY_CONTEXT, f"Researching industry context for {company_name}..."),
                (ResearchCategory.CULTURE_VALUES, f"Researching {company_name} culture and values..."),
                (ResearchCategory.LEADERSHIP_DIRECTION, f"Analyzing {company_name} leadership direction..."),
            ]

            results = {}
            gaps = []

            for category, message in categories:
                await sse_manager.send_event(
                    application_id,
                    "progress",
                    {"source": category.value, "status": "searching", "message": message},
                )

                # Execute research for this category (Story 4-2 implements actual LLM research)
                result = await self._research_category(category, company_name, job_posting)
                results[category.value] = result

                if not result.found:
                    gaps.append(category.value)

                await asyncio.sleep(0.5)

            # Build research result
            research_result = ResearchResult(
                gaps=gaps,
                completed_at=datetime.now(timezone.utc).isoformat(),
                **{cat.value: results[cat.value] for cat in ResearchCategory if cat.value in results},
            )

            # Persist research data to application (H2: no redundant status set)
            try:
                await self._save_research_results(
                    application_id, role_id, research_result
                )
            except Exception as db_err:
                logger.error(
                    "Failed to persist research results for application %d: %s",
                    application_id, db_err,
                )
                # Research data still sent in complete event below

            self._research_state[application_id] = ResearchStatus.COMPLETE

            await sse_manager.send_event(
                application_id,
                "complete",
                {"research_data": {k: v.model_dump() for k, v in results.items()}},
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

    async def _research_category(
        self,
        category: ResearchCategory,
        company_name: str,
        job_posting: str,
    ) -> ResearchSourceResult:
        """Research a single strategic category. Placeholder for Story 4-2 LLM integration."""
        return ResearchSourceResult(
            found=True,
            content=f"Placeholder research data for {category.value} about {company_name}",
        )

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
