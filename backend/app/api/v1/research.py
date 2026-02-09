"""Research API endpoints for company research with SSE streaming."""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_role
from app.models.application import ApplicationUpdate, ApplicationStatus
from app.models.role import Role
from app.services import application_service
from app.services.research_service import research_service
from app.services.sse_manager import sse_manager

router = APIRouter(prefix="/applications", tags=["research"])


@router.post("/{id}/research")
async def start_research(
    id: int,
    background_tasks: BackgroundTasks,
    role: Role = Depends(get_current_role),
):
    """Start company research for an application."""
    application = await application_service.get_application(id, role.id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if research_service.is_running(id):
        raise HTTPException(
            status_code=409,
            detail="Research already in progress for this application",
        )

    if not application.company_name or not application.job_posting:
        raise HTTPException(
            status_code=400,
            detail="Application must have company name and job posting",
        )

    # Update application status to researching
    await application_service.update_application(
        id, role.id, ApplicationUpdate(status=ApplicationStatus.RESEARCHING)
    )

    background_tasks.add_task(
        research_service.start_research,
        id,
        role.id,
        application.company_name,
        application.job_posting,
    )

    return {
        "status": "started",
        "application_id": id,
        "message": "Research started. Connect to /research/stream for progress.",
    }


@router.get("/{id}/research/stream")
async def stream_research(
    id: int,
    role: Role = Depends(get_current_role),
):
    """Stream research progress via Server-Sent Events."""
    application = await application_service.get_application(id, role.id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    async def event_generator():
        async for event in sse_manager.create_stream(id):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{id}/research/status")
async def get_research_status(
    id: int,
    role: Role = Depends(get_current_role),
):
    """Get current research status for an application."""
    application = await application_service.get_application(id, role.id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    status = research_service.get_status(id)

    return {
        "application_id": id,
        "status": status.value if status else "not_started",
        "has_research_data": bool(application.research_data),
    }
