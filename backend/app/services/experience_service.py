"""Experience service with CRUD operations for skills and accomplishments."""

from typing import Optional

from sqlmodel import select

from app.models.experience import (
    Skill,
    SkillCreate,
    SkillUpdate,
    Accomplishment,
    AccomplishmentCreate,
    AccomplishmentUpdate,
)
from app.database import async_session_maker


async def get_skills(role_id: int) -> list[Skill]:
    """
    Get all skills for a role.

    CRITICAL: Always filter by role_id - no exceptions!
    """
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    async with async_session_maker() as session:
        result = await session.execute(
            select(Skill).where(Skill.role_id == role_id)
        )
        skills = result.scalars().all()
        for skill in skills:
            session.expunge(skill)
        return list(skills)


async def get_skill(skill_id: int, role_id: int) -> Optional[Skill]:
    """
    Get a single skill with role ownership verification.
    """
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    async with async_session_maker() as session:
        result = await session.execute(
            select(Skill).where(
                Skill.id == skill_id,
                Skill.role_id == role_id  # ALWAYS include role filter!
            )
        )
        skill = result.scalar_one_or_none()
        if skill:
            session.expunge(skill)
        return skill


async def create_skill(role_id: int, data: SkillCreate) -> Skill:
    """
    Create a skill scoped to a specific role.
    """
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    async with async_session_maker() as session:
        skill = Skill(
            role_id=role_id,
            name=data.name,
            category=data.category,
            source=data.source,
        )
        session.add(skill)
        await session.commit()
        await session.refresh(skill)
        session.expunge(skill)
        return skill


async def delete_skill(skill_id: int, role_id: int) -> bool:
    """
    Delete a skill with role ownership verification.
    Returns True if deleted, False if not found.
    """
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    async with async_session_maker() as session:
        result = await session.execute(
            select(Skill).where(
                Skill.id == skill_id,
                Skill.role_id == role_id
            )
        )
        skill = result.scalar_one_or_none()

        if not skill:
            return False

        await session.delete(skill)
        await session.commit()
        return True


async def update_skill(
    skill_id: int, role_id: int, data: SkillUpdate
) -> Optional[Skill]:
    """
    Update a skill with role ownership verification.
    Returns updated Skill if found, None if not found.
    """
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    async with async_session_maker() as session:
        result = await session.execute(
            select(Skill).where(
                Skill.id == skill_id,
                Skill.role_id == role_id
            )
        )
        skill = result.scalar_one_or_none()

        if not skill:
            return None

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(skill, field, value)

        session.add(skill)
        await session.commit()
        await session.refresh(skill)
        session.expunge(skill)
        return skill


async def get_accomplishments(role_id: int) -> list[Accomplishment]:
    """
    Get all accomplishments for a role.

    CRITICAL: Always filter by role_id - no exceptions!
    """
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    async with async_session_maker() as session:
        result = await session.execute(
            select(Accomplishment).where(Accomplishment.role_id == role_id)
        )
        accomplishments = result.scalars().all()
        for acc in accomplishments:
            session.expunge(acc)
        return list(accomplishments)


async def get_accomplishment(
    accomplishment_id: int, role_id: int
) -> Optional[Accomplishment]:
    """
    Get a single accomplishment with role ownership verification.
    """
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    async with async_session_maker() as session:
        result = await session.execute(
            select(Accomplishment).where(
                Accomplishment.id == accomplishment_id,
                Accomplishment.role_id == role_id
            )
        )
        accomplishment = result.scalar_one_or_none()
        if accomplishment:
            session.expunge(accomplishment)
        return accomplishment


async def create_accomplishment(
    role_id: int, data: AccomplishmentCreate
) -> Accomplishment:
    """
    Create an accomplishment scoped to a specific role.
    """
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    async with async_session_maker() as session:
        accomplishment = Accomplishment(
            role_id=role_id,
            description=data.description,
            context=data.context,
            company_name=data.company_name,
            role_title=data.role_title,
            dates=data.dates,
            source=data.source,
        )
        session.add(accomplishment)
        await session.commit()
        await session.refresh(accomplishment)
        session.expunge(accomplishment)
        return accomplishment


async def delete_accomplishment(accomplishment_id: int, role_id: int) -> bool:
    """
    Delete an accomplishment with role ownership verification.
    Returns True if deleted, False if not found.
    """
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    async with async_session_maker() as session:
        result = await session.execute(
            select(Accomplishment).where(
                Accomplishment.id == accomplishment_id,
                Accomplishment.role_id == role_id
            )
        )
        accomplishment = result.scalar_one_or_none()

        if not accomplishment:
            return False

        await session.delete(accomplishment)
        await session.commit()
        return True


async def update_accomplishment(
    accomplishment_id: int, role_id: int, data: AccomplishmentUpdate
) -> Optional[Accomplishment]:
    """
    Update an accomplishment with role ownership verification.
    Returns updated Accomplishment if found, None if not found.
    """
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    async with async_session_maker() as session:
        result = await session.execute(
            select(Accomplishment).where(
                Accomplishment.id == accomplishment_id,
                Accomplishment.role_id == role_id
            )
        )
        accomplishment = result.scalar_one_or_none()

        if not accomplishment:
            return None

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(accomplishment, field, value)

        session.add(accomplishment)
        await session.commit()
        await session.refresh(accomplishment)
        session.expunge(accomplishment)
        return accomplishment
