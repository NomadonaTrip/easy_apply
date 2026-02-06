"""Application API endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_role
from app.models.role import Role
from app.models.application import (
    ApplicationCreate, ApplicationRead, ApplicationUpdate
)
from app.services import application_service

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
    return await application_service.update_application(id, role.id, data)
