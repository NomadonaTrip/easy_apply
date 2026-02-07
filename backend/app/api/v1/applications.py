"""Application API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_role
from app.models.role import Role
from app.models.application import (
    ApplicationCreate, ApplicationRead, ApplicationUpdate, ApplicationStatus
)
from app.models.keyword import Keyword, KeywordList, KeywordExtractionResponse
from app.services import application_service
from app.services.keyword_service import extract_keywords, keywords_to_json


class StatusUpdate(BaseModel):
    """Request body for updating application status."""
    status: ApplicationStatus


# Valid status transitions per the Application Status State Machine
VALID_TRANSITIONS: dict[ApplicationStatus, list[ApplicationStatus]] = {
    ApplicationStatus.CREATED: [ApplicationStatus.KEYWORDS],
    ApplicationStatus.KEYWORDS: [ApplicationStatus.RESEARCHING],
    ApplicationStatus.RESEARCHING: [ApplicationStatus.REVIEWED],
    ApplicationStatus.REVIEWED: [ApplicationStatus.EXPORTED],
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
    role: Role = Depends(get_current_role),
):
    application = await application_service.update_application(id, role.id, data)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.patch("/{id}/status", response_model=ApplicationRead)
async def update_application_status(
    id: int,
    data: StatusUpdate,
    role: Role = Depends(get_current_role),
):
    """Update application status."""
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

    return updated_app


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
