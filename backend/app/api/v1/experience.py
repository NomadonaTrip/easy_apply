"""Experience API endpoints with role scoping."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_role
from app.models.role import Role
from app.models.experience import (
    SkillCreate,
    SkillRead,
    SkillUpdate,
    AccomplishmentCreate,
    AccomplishmentRead,
    AccomplishmentUpdate,
)
from app.services import experience_service


router = APIRouter(prefix="/experience", tags=["experience"])


# Skills endpoints

@router.get("/skills", response_model=list[SkillRead])
async def list_skills(
    current_role: Role = Depends(get_current_role)
):
    """Get all skills for the current role."""
    skills = await experience_service.get_skills(current_role.id)
    return [SkillRead.model_validate(skill) for skill in skills]


@router.post("/skills", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
async def create_skill(
    data: SkillCreate,
    current_role: Role = Depends(get_current_role)
):
    """Create a skill for the current role."""
    skill = await experience_service.create_skill(current_role.id, data)
    return SkillRead.model_validate(skill)


@router.get("/skills/{skill_id}", response_model=SkillRead)
async def get_skill(
    skill_id: int,
    current_role: Role = Depends(get_current_role)
):
    """Get a specific skill (ownership verified via role)."""
    skill = await experience_service.get_skill(skill_id, current_role.id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found"
        )
    return SkillRead.model_validate(skill)


@router.delete("/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: int,
    current_role: Role = Depends(get_current_role)
):
    """Delete a skill (ownership verified via role)."""
    deleted = await experience_service.delete_skill(skill_id, current_role.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found"
        )


@router.patch("/skills/{skill_id}", response_model=SkillRead)
async def update_skill(
    skill_id: int,
    data: SkillUpdate,
    current_role: Role = Depends(get_current_role)
):
    """Update a skill (ownership verified via role)."""
    skill = await experience_service.update_skill(skill_id, current_role.id, data)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found"
        )
    return SkillRead.model_validate(skill)


# Accomplishments endpoints

@router.get("/accomplishments", response_model=list[AccomplishmentRead])
async def list_accomplishments(
    current_role: Role = Depends(get_current_role)
):
    """Get all accomplishments for the current role."""
    accomplishments = await experience_service.get_accomplishments(current_role.id)
    return [AccomplishmentRead.model_validate(acc) for acc in accomplishments]


@router.post(
    "/accomplishments",
    response_model=AccomplishmentRead,
    status_code=status.HTTP_201_CREATED
)
async def create_accomplishment(
    data: AccomplishmentCreate,
    current_role: Role = Depends(get_current_role)
):
    """Create an accomplishment for the current role."""
    accomplishment = await experience_service.create_accomplishment(
        current_role.id, data
    )
    return AccomplishmentRead.model_validate(accomplishment)


@router.get("/accomplishments/{accomplishment_id}", response_model=AccomplishmentRead)
async def get_accomplishment(
    accomplishment_id: int,
    current_role: Role = Depends(get_current_role)
):
    """Get a specific accomplishment (ownership verified via role)."""
    accomplishment = await experience_service.get_accomplishment(
        accomplishment_id, current_role.id
    )
    if not accomplishment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accomplishment not found"
        )
    return AccomplishmentRead.model_validate(accomplishment)


@router.delete(
    "/accomplishments/{accomplishment_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_accomplishment(
    accomplishment_id: int,
    current_role: Role = Depends(get_current_role)
):
    """Delete an accomplishment (ownership verified via role)."""
    deleted = await experience_service.delete_accomplishment(
        accomplishment_id, current_role.id
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accomplishment not found"
        )


@router.patch("/accomplishments/{accomplishment_id}", response_model=AccomplishmentRead)
async def update_accomplishment(
    accomplishment_id: int,
    data: AccomplishmentUpdate,
    current_role: Role = Depends(get_current_role)
):
    """Update an accomplishment (ownership verified via role)."""
    accomplishment = await experience_service.update_accomplishment(
        accomplishment_id, current_role.id, data
    )
    if not accomplishment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accomplishment not found"
        )
    return AccomplishmentRead.model_validate(accomplishment)
