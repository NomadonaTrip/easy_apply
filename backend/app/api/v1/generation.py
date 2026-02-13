"""Generation API endpoints for resume and cover letter creation."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_role
from app.models.application import ApplicationStatus, ApplicationUpdate, GenerationStatus
from app.models.role import Role
from app.services import application_service, generation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["generation"])


class GenerateResumeResponse(BaseModel):
    message: str
    resume_content: str
    status: str
    violations_fixed: int = 0
    violations_remaining: int = 0
    warnings: list[str] = []


class GenerateCoverLetterRequest(BaseModel):
    tone: str = "formal"


class GenerateCoverLetterResponse(BaseModel):
    message: str
    cover_letter_content: str
    status: str
    violations_fixed: int = 0
    violations_remaining: int = 0
    warnings: list[str] = []


class GenerationStatusResponse(BaseModel):
    generation_status: GenerationStatus
    has_resume: bool
    has_cover_letter: bool


# Valid statuses from which generation can be triggered
_GENERATION_ALLOWED_STATUSES = {
    ApplicationStatus.REVIEWED.value,
    ApplicationStatus.GENERATING.value,
}


@router.post("/{application_id}/generate/resume", response_model=GenerateResumeResponse)
async def generate_resume(
    application_id: int,
    role: Role = Depends(get_current_role),
):
    """Generate a tailored resume for the application."""
    application = await application_service.get_application(application_id, role.id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if application.status not in _GENERATION_ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot generate from status '{application.status}'. "
                   f"Application must be in 'reviewed' or 'generating' status.",
        )

    # Transition application status to GENERATING (AC #4)
    if application.status == ApplicationStatus.REVIEWED.value:
        await application_service.update_application(
            application_id, role.id,
            ApplicationUpdate(status=ApplicationStatus.GENERATING),
        )

    try:
        result = await generation_service.generate_resume(application_id, role.id)
        return GenerateResumeResponse(
            message="Resume generated successfully",
            resume_content=result["content"],
            status="complete",
            violations_fixed=result["violations_fixed"],
            violations_remaining=result["violations_remaining"],
            warnings=result["warnings"],
        )
    except Exception as e:
        logger.error("Resume generation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{application_id}/generate/cover-letter", response_model=GenerateCoverLetterResponse)
async def generate_cover_letter(
    application_id: int,
    request: GenerateCoverLetterRequest = GenerateCoverLetterRequest(),
    role: Role = Depends(get_current_role),
):
    """Generate a tailored cover letter for the application."""
    application = await application_service.get_application(application_id, role.id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if application.status not in _GENERATION_ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot generate from status '{application.status}'. "
                   f"Application must be in 'reviewed' or 'generating' status.",
        )

    # Transition application status to GENERATING (AC #4)
    if application.status == ApplicationStatus.REVIEWED.value:
        await application_service.update_application(
            application_id, role.id,
            ApplicationUpdate(status=ApplicationStatus.GENERATING),
        )

    try:
        result = await generation_service.generate_cover_letter(
            application_id, role.id, request.tone,
        )
        return GenerateCoverLetterResponse(
            message="Cover letter generated successfully",
            cover_letter_content=result["content"],
            status="complete",
            violations_fixed=result["violations_fixed"],
            violations_remaining=result["violations_remaining"],
            warnings=result["warnings"],
        )
    except Exception as e:
        logger.error("Cover letter generation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{application_id}/generation/status", response_model=GenerationStatusResponse)
async def get_generation_status(
    application_id: int,
    role: Role = Depends(get_current_role),
):
    """Get the current generation status for an application."""
    application = await application_service.get_application(application_id, role.id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    return GenerationStatusResponse(
        generation_status=application.generation_status,
        has_resume=bool(application.resume_content),
        has_cover_letter=bool(application.cover_letter_content),
    )
