"""Application API endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_role
from app.models.role import Role
from app.models.application import (
    ApplicationCreate, ApplicationRead, ApplicationUpdate, ApplicationStatus
)
from app.models.keyword import KeywordExtractionResponse
from app.services import application_service
from app.services.keyword_service import extract_keywords, keywords_to_json

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
    role: Role = Depends(get_current_role),
):
    application = await application_service.update_application(id, role.id, data)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.post("/{id}/keywords/extract", response_model=KeywordExtractionResponse)
async def extract_application_keywords(
    id: int,
    role: Role = Depends(get_current_role),
):
    """Extract and store keywords for an application."""
    application = await application_service.get_application(id, role.id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if not application.job_posting:
        raise HTTPException(status_code=400, detail="No job posting to analyze")

    keyword_list = await extract_keywords(application.job_posting)

    update_data = ApplicationUpdate(
        keywords=keywords_to_json(keyword_list),
        status=ApplicationStatus.KEYWORDS,
    )
    updated_app = await application_service.update_application(id, role.id, update_data)

    return KeywordExtractionResponse(
        application_id=updated_app.id,
        keywords=keyword_list.keywords,
        status=updated_app.status,
    )
