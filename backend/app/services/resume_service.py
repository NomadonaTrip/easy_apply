"""Resume service with CRUD operations."""

from typing import Optional

from sqlmodel import select

from app.models.resume import Resume
from app.database import async_session_maker
from app.utils.file_storage import delete_file


async def create_resume(
    role_id: int,
    filename: str,
    file_type: str,
    file_path: str,
    file_size: int
) -> Resume:
    """
    Create a resume record in the database.

    Args:
        role_id: The role this resume belongs to
        filename: Original filename
        file_type: File extension (pdf or docx)
        file_path: Path where file is stored (relative to data/)
        file_size: File size in bytes

    Returns:
        The created Resume object
    """
    if role_id is None:
        raise ValueError("role_id is required")

    async with async_session_maker() as session:
        resume = Resume(
            role_id=role_id,
            filename=filename,
            file_type=file_type,
            file_path=file_path,
            file_size=file_size
        )
        session.add(resume)
        await session.commit()
        await session.refresh(resume)
        session.expunge(resume)
        return resume


async def get_resumes(role_id: int) -> list[Resume]:
    """
    Get all resumes for a role.

    Args:
        role_id: The role to get resumes for

    Returns:
        List of Resume objects for the role
    """
    if role_id is None:
        raise ValueError("role_id is required")

    async with async_session_maker() as session:
        result = await session.execute(
            select(Resume).where(Resume.role_id == role_id)
        )
        resumes = result.scalars().all()
        for resume in resumes:
            session.expunge(resume)
        return list(resumes)


async def get_resume(resume_id: int, role_id: int) -> Optional[Resume]:
    """
    Get a single resume with role verification.

    Args:
        resume_id: The resume ID to fetch
        role_id: The role ID for verification

    Returns:
        Resume if found and owned by role, None otherwise
    """
    if role_id is None:
        raise ValueError("role_id is required")

    async with async_session_maker() as session:
        result = await session.execute(
            select(Resume).where(
                Resume.id == resume_id,
                Resume.role_id == role_id
            )
        )
        resume = result.scalar_one_or_none()
        if resume:
            session.expunge(resume)
        return resume


async def delete_resume(resume_id: int, role_id: int) -> bool:
    """
    Delete a resume (file and database record).

    Args:
        resume_id: The resume ID to delete
        role_id: The role ID for ownership verification

    Returns:
        True if deleted

    Raises:
        ValueError: If resume not found or doesn't belong to role
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(Resume).where(
                Resume.id == resume_id,
                Resume.role_id == role_id
            )
        )
        resume = result.scalar_one_or_none()

        if not resume:
            raise ValueError("Resume not found")

        # Delete file from disk
        delete_file(resume.file_path)

        # Delete database record
        await session.delete(resume)
        await session.commit()
        return True


async def mark_resume_processed(resume_id: int, role_id: int) -> Resume:
    """
    Mark a resume as processed (skill extraction complete).

    Args:
        resume_id: The resume ID to update
        role_id: The role ID for ownership verification

    Returns:
        Updated Resume object

    Raises:
        ValueError: If resume not found
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(Resume).where(
                Resume.id == resume_id,
                Resume.role_id == role_id
            )
        )
        resume = result.scalar_one_or_none()

        if not resume:
            raise ValueError("Resume not found")

        resume.processed = True
        await session.commit()
        await session.refresh(resume)
        session.expunge(resume)
        return resume
