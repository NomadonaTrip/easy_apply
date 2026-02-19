"""Application API endpoints."""

import json
from datetime import datetime, timezone
from html import escape
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_current_role
from app.models.role import Role
from app.models.application import (
    Application, ApplicationCreate, ApplicationRead, ApplicationUpdate, ApplicationStatus
)
from app.models.research import ResearchCategory
from app.models.keyword import Keyword, KeywordList, KeywordExtractionResponse
from app.services import application_service, enrichment_service
from app.services.keyword_service import extract_keywords, keywords_to_json
from app.services import learning_service


class StatusUpdate(BaseModel):
    """Request body for updating application status."""
    status: ApplicationStatus


# Valid status transitions per the Application Status State Machine
VALID_TRANSITIONS: dict[ApplicationStatus, list[ApplicationStatus]] = {
    ApplicationStatus.CREATED: [ApplicationStatus.KEYWORDS],
    ApplicationStatus.KEYWORDS: [ApplicationStatus.RESEARCHING],
    ApplicationStatus.RESEARCHING: [ApplicationStatus.REVIEWED],
    ApplicationStatus.REVIEWED: [ApplicationStatus.GENERATING],
    ApplicationStatus.GENERATING: [ApplicationStatus.EXPORTED],
    ApplicationStatus.EXPORTED: [ApplicationStatus.SENT],
    ApplicationStatus.SENT: [
        ApplicationStatus.CALLBACK,
        ApplicationStatus.OFFER,
        ApplicationStatus.CLOSED,
    ],
    ApplicationStatus.CALLBACK: [ApplicationStatus.OFFER, ApplicationStatus.CLOSED],
    ApplicationStatus.OFFER: [ApplicationStatus.CLOSED],
    ApplicationStatus.CLOSED: [],
}


class KeywordOrderUpdate(BaseModel):
    """Request body for updating keyword order."""
    keywords: list[Keyword]

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationRead])
async def list_applications(
    role: Role = Depends(get_current_role),
):
    return await application_service.get_applications(role.id)


@router.post("", response_model=ApplicationRead, status_code=201)
async def create_application(
    data: ApplicationCreate,
    role: Role = Depends(get_current_role),
):
    return await application_service.create_application(role.id, data)


@router.get("/{id}", response_model=ApplicationRead)
async def get_application(
    id: int,
    role: Role = Depends(get_current_role),
):
    application = await application_service.get_application(id, role.id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.patch("/{id}", response_model=ApplicationRead)
async def update_application(
    id: int,
    data: ApplicationUpdate,
    background_tasks: BackgroundTasks,
    role: Role = Depends(get_current_role),
):
    # Check current state before update to detect approval transitions
    current = await application_service.get_application(id, role.id)
    if not current:
        raise HTTPException(status_code=404, detail="Application not found")

    application = await application_service.update_application(id, role.id, data)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Trigger enrichment as background task on document approval
    if data.resume_approved is True and not current.resume_approved:
        background_tasks.add_task(
            enrichment_service.analyze_document_for_enrichment,
            application_id=id,
            role_id=role.id,
            document_type="resume",
        )
    if data.cover_letter_approved is True and not current.cover_letter_approved:
        background_tasks.add_task(
            enrichment_service.analyze_document_for_enrichment,
            application_id=id,
            role_id=role.id,
            document_type="cover_letter",
        )

    return application


@router.patch("/{id}/status", response_model=ApplicationRead)
async def update_application_status(
    id: int,
    data: StatusUpdate,
    role: Role = Depends(get_current_role),
):
    """Update application status.

    When transitioning to callback or offer, records keyword success
    patterns for future application keyword boosting.
    """
    application = await application_service.get_application(id, role.id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    current_status = ApplicationStatus(application.status)
    allowed = VALID_TRANSITIONS.get(current_status, [])
    if data.status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid transition: {current_status.value} → {data.status.value}",
        )

    update_data = ApplicationUpdate(status=data.status)
    updated_app = await application_service.update_application(id, role.id, update_data)

    # Record success patterns when application reaches callback or offer
    if data.status.value in learning_service.SUCCESS_STATUSES and current_status.value not in learning_service.SUCCESS_STATUSES:
        await learning_service.record_application_success(application)

    return updated_app


@router.post("/{id}/keywords/extract", response_model=KeywordExtractionResponse)
async def extract_application_keywords(
    id: int,
    role: Role = Depends(get_current_role),
):
    """Extract and store keywords for an application.

    Integrates pattern-based boosting from successful past applications.
    Keywords from applications that led to callbacks/offers are ranked higher.
    """
    application = await application_service.get_application(id, role.id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if not application.job_posting:
        raise HTTPException(status_code=400, detail="No job posting to analyze")

    keyword_list = await extract_keywords(application.job_posting)

    # Fetch learned patterns and apply boosting
    patterns_applied = False
    pattern_count = 0
    patterns = await learning_service.get_keyword_patterns(role.id)

    if patterns:
        pattern_count = len(patterns)
        # Convert keywords to score-based format for boosting
        kw_dicts = [
            {"keyword": k.text, "score": k.priority / 10.0, "priority": k.priority, "category": k.category}
            for k in keyword_list.keywords
        ]
        boosted = learning_service.apply_pattern_boost(kw_dicts, patterns)
        # Convert back to Keyword objects with updated priorities and pattern_boosted flag
        keyword_list = KeywordList(keywords=[
            Keyword(
                text=kw["keyword"],
                priority=max(1, min(10, round(kw["score"] * 10))),
                category=kw.get("category", "general"),
                pattern_boosted=kw.get("pattern_boosted", False),
            )
            for kw in boosted
        ])
        # Only mark patterns as applied if at least one keyword was actually boosted
        patterns_applied = any(k.pattern_boosted for k in keyword_list.keywords)

    # Record keyword usage for future pattern learning
    await learning_service.record_keyword_usage(
        role.id, [k.text for k in keyword_list.keywords]
    )

    update_data = ApplicationUpdate(
        keywords=keywords_to_json(keyword_list),
        status=ApplicationStatus.KEYWORDS,
    )
    updated_app = await application_service.update_application(id, role.id, update_data)

    return KeywordExtractionResponse(
        application_id=updated_app.id,
        keywords=keyword_list.keywords,
        status=updated_app.status,
        patterns_applied=patterns_applied,
        pattern_count=pattern_count,
    )


@router.put("/{id}/keywords", response_model=ApplicationRead)
async def update_keywords(
    id: int,
    data: KeywordOrderUpdate,
    role: Role = Depends(get_current_role),
):
    """Update keyword order for an application."""
    application = await application_service.get_application(id, role.id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    keyword_list = KeywordList(keywords=data.keywords)
    update_data = ApplicationUpdate(keywords=keywords_to_json(keyword_list))
    updated_app = await application_service.update_application(id, role.id, update_data)
    if not updated_app:
        raise HTTPException(status_code=404, detail="Application not found")

    return updated_app


class ManualContextUpdate(BaseModel):
    """Request body for manual context update."""
    manual_context: str = Field(max_length=5000)


class ManualContextSaveResponse(BaseModel):
    """Response schema for saving manual context."""
    application_id: int
    manual_context: str
    message: str


class ManualContextGetResponse(BaseModel):
    """Response schema for retrieving manual context."""
    application_id: int
    manual_context: str
    gaps: list[str]


@router.patch("/{id}/context", response_model=ManualContextSaveResponse)
async def update_manual_context(
    id: int,
    body: ManualContextUpdate,
    role: Role = Depends(get_current_role),
):
    """Add or update manual context for an application."""
    application = await application_service.get_application(id, role.id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Sanitize input - escape ALL HTML entities and trim whitespace.
    # html.escape() converts <, >, &, " and ' to HTML entities,
    # neutralizing any HTML/script injection vectors.
    sanitized_context = escape(body.manual_context.strip())

    updated = await application_service.update_manual_context(
        id, role.id, sanitized_context
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Application not found")

    return ManualContextSaveResponse(
        application_id=updated.id,
        manual_context=updated.manual_context or "",
        message="Context saved successfully",
    )


@router.get("/{id}/context", response_model=ManualContextGetResponse)
async def get_manual_context(
    id: int,
    role: Role = Depends(get_current_role),
):
    """Get manual context for an application."""
    application = await application_service.get_application(id, role.id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    gaps: list[str] = []
    if application.research_data:
        try:
            research = json.loads(application.research_data)
            gaps = research.get("gaps", [])
        except (json.JSONDecodeError, TypeError):
            pass

    return ManualContextGetResponse(
        application_id=application.id,
        manual_context=application.manual_context or "",
        gaps=gaps,
    )


class ResearchSummaryResponse(BaseModel):
    """Response schema for research summary data."""
    sources_found: int
    gaps: list[str]
    has_manual_context: bool


class ApprovalResponse(BaseModel):
    """Response from research approval."""
    application_id: int
    status: str
    approved_at: str
    research_summary: ResearchSummaryResponse
    message: str


def _get_research_summary(application: Application) -> ResearchSummaryResponse:
    """Extract summary from research data."""
    if not application.research_data:
        return ResearchSummaryResponse(
            sources_found=0, gaps=[], has_manual_context=False
        )

    try:
        research = json.loads(application.research_data)
        gaps = research.get("gaps", [])
        return ResearchSummaryResponse(
            sources_found=len(ResearchCategory) - len(gaps),
            gaps=gaps,
            has_manual_context=bool(application.manual_context),
        )
    except (json.JSONDecodeError, TypeError):
        return ResearchSummaryResponse(
            sources_found=0, gaps=[], has_manual_context=False
        )


@router.post("/{id}/research/approve", response_model=ApprovalResponse)
async def approve_research(
    id: int,
    role: Role = Depends(get_current_role),
):
    """Approve research findings and proceed to generation.

    State Machine: researching -> reviewed (via this approval)

    Note: This endpoint intentionally uses custom validation instead of
    VALID_TRANSITIONS to support idempotent approval (returns success if
    already reviewed), research data existence checks, and graceful
    handling of past-approval statuses.
    """
    application = await application_service.get_application(id, role.id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Idempotent: already approved
    if application.status == ApplicationStatus.REVIEWED.value:
        return ApprovalResponse(
            application_id=application.id,
            status=application.status,
            approved_at=application.updated_at.isoformat() if application.updated_at else datetime.now(timezone.utc).isoformat(),
            research_summary=_get_research_summary(application),
            message="Research already approved",
        )

    # Past approval stage
    past_statuses = {
        ApplicationStatus.EXPORTED.value,
        ApplicationStatus.SENT.value,
        ApplicationStatus.CALLBACK.value,
        ApplicationStatus.OFFER.value,
        ApplicationStatus.CLOSED.value,
    }
    if application.status in past_statuses:
        return ApprovalResponse(
            application_id=application.id,
            status=application.status,
            approved_at=application.updated_at.isoformat() if application.updated_at else datetime.now(timezone.utc).isoformat(),
            research_summary=_get_research_summary(application),
            message="Application already past research approval stage",
        )

    # Only allow from researching status
    if application.status != ApplicationStatus.RESEARCHING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve research from status '{application.status}'. "
                   f"Application must be in 'researching' status.",
        )

    # Verify research data exists
    if not application.research_data:
        raise HTTPException(
            status_code=400,
            detail="No research data found. Run research first.",
        )

    # Transition to reviewed
    update_data = ApplicationUpdate(status=ApplicationStatus.REVIEWED)
    updated = await application_service.update_application(id, role.id, update_data)

    return ApprovalResponse(
        application_id=updated.id,
        status=updated.status,
        approved_at=updated.updated_at.isoformat(),
        research_summary=_get_research_summary(updated),
        message="Research approved. Ready for document generation.",
    )


class EnrichmentTriggerResponse(BaseModel):
    """Response from enrichment trigger."""
    application_id: int
    resume_result: Optional[dict] = None
    cover_letter_result: Optional[dict] = None
    message: str


@router.post("/{id}/enrich", response_model=EnrichmentTriggerResponse)
async def trigger_enrichment(
    id: int,
    role: Role = Depends(get_current_role),
):
    """Trigger or retry enrichment analysis for an application.

    Analyzes both resume and cover letter content (if available) for
    new skills and accomplishments not already in the experience database.
    """
    application = await application_service.get_application(id, role.id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    resume_result = None
    cover_letter_result = None

    if application.resume_content and application.resume_approved:
        resume_result = await enrichment_service.analyze_document_for_enrichment(
            id, role.id, "resume"
        )

    if application.cover_letter_content and application.cover_letter_approved:
        cover_letter_result = await enrichment_service.analyze_document_for_enrichment(
            id, role.id, "cover_letter"
        )

    total = (
        (resume_result.get("candidates_found", 0) if resume_result else 0)
        + (cover_letter_result.get("candidates_found", 0) if cover_letter_result else 0)
    )

    if not resume_result and not cover_letter_result:
        message = "No approved documents found. Approve a resume or cover letter first."
    else:
        message = f"Enrichment analysis complete. {total} new candidates found."

    return EnrichmentTriggerResponse(
        application_id=id,
        resume_result=resume_result,
        cover_letter_result=cover_letter_result,
        message=message,
    )
