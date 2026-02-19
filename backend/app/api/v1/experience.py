"""Experience API endpoints with role scoping."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

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
from app.models.enrichment import EnrichmentCandidateRead
from app.services import experience_service, enrichment_service, application_service


router = APIRouter(prefix="/experience", tags=["experience"])


# Combined experience endpoint

@router.get("")
async def get_experience(
    current_role: Role = Depends(get_current_role)
):
    """Get all experience data (skills + accomplishments) for the current role."""
    skills = await experience_service.get_skills(current_role.id)
    accomplishments = await experience_service.get_accomplishments(current_role.id)

    return {
        "skills": [SkillRead.model_validate(s) for s in skills],
        "accomplishments": [AccomplishmentRead.model_validate(a) for a in accomplishments],
        "skills_count": len(skills),
        "accomplishments_count": len(accomplishments)
    }


@router.get("/stats")
async def get_experience_stats(
    current_role: Role = Depends(get_current_role)
):
    """Get experience statistics for the current role."""
    skills = await experience_service.get_skills(current_role.id)
    accomplishments = await experience_service.get_accomplishments(current_role.id)

    # Group skills by category
    categories: dict[str, int] = {}
    for skill in skills:
        cat = skill.category or "Uncategorized"
        if cat not in categories:
            categories[cat] = 0
        categories[cat] += 1

    return {
        "total_skills": len(skills),
        "total_accomplishments": len(accomplishments),
        "skills_by_category": categories
    }


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


# Enrichment endpoints


class BulkResolveRequest(BaseModel):
    """Request body for bulk accept/dismiss."""
    candidate_ids: list[int]
    action: Literal["accept", "dismiss"]


@router.get("/enrichment")
async def get_enrichment_candidates(
    current_role: Role = Depends(get_current_role),
):
    """Get all pending enrichment candidates for the current role, grouped by application."""
    candidates = await enrichment_service.get_pending_candidates(current_role.id)

    # Group by application_id
    by_app: dict[int, list[dict]] = {}
    for c in candidates:
        if c.application_id not in by_app:
            by_app[c.application_id] = []
        by_app[c.application_id].append(
            EnrichmentCandidateRead.model_validate(c).model_dump()
        )

    # Batch-fetch application metadata (avoids N+1 queries)
    app_ids = list(by_app.keys())
    apps = await application_service.get_applications_by_ids(app_ids, current_role.id)
    app_lookup = {a.id: a for a in apps}

    grouped: dict[str, dict] = {}
    for app_id, app_candidates in by_app.items():
        app = app_lookup.get(app_id)
        company_name = app.company_name if app else f"Application #{app_id}"
        grouped[str(app_id)] = {
            "company_name": company_name,
            "candidates": app_candidates,
        }

    return {
        "candidates": grouped,
        "total_pending": len(candidates),
    }


@router.get("/enrichment/stats")
async def get_enrichment_stats(
    current_role: Role = Depends(get_current_role),
):
    """Get count of pending enrichment candidates."""
    count = await enrichment_service.get_pending_count(current_role.id)
    return {"pending_count": count}


@router.post("/enrichment/{candidate_id}/accept")
async def accept_enrichment_candidate(
    candidate_id: int,
    current_role: Role = Depends(get_current_role),
):
    """Accept an enrichment candidate — adds it to the experience database."""
    success = await enrichment_service.accept_candidate(candidate_id, current_role.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found or already resolved",
        )
    return {"status": "accepted", "candidate_id": candidate_id}


@router.post("/enrichment/{candidate_id}/dismiss")
async def dismiss_enrichment_candidate(
    candidate_id: int,
    current_role: Role = Depends(get_current_role),
):
    """Dismiss an enrichment candidate — removes it from suggestions."""
    success = await enrichment_service.dismiss_candidate(candidate_id, current_role.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found or already resolved",
        )
    return {"status": "dismissed", "candidate_id": candidate_id}


@router.post("/enrichment/bulk")
async def bulk_resolve_enrichment(
    data: BulkResolveRequest,
    current_role: Role = Depends(get_current_role),
):
    """Bulk accept or dismiss enrichment candidates."""
    result = await enrichment_service.bulk_resolve(
        data.candidate_ids, current_role.id, data.action
    )
    return result
