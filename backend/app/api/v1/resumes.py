"""Resume upload API endpoints."""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status

from app.api.deps import get_current_role
from app.models.role import Role
from app.models.resume import ResumeRead
from app.services import resume_service
from app.utils.file_storage import validate_file, save_uploaded_file

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/upload", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    current_role: Role = Depends(get_current_role)
) -> ResumeRead:
    """
    Upload a resume file (PDF or DOCX).

    The file is stored and associated with the current role.
    Skill extraction will be triggered separately in Story 2.6.
    """
    # Validate file type
    is_valid, error = validate_file(file)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    try:
        # Save file to disk
        file_path, file_size = await save_uploaded_file(file, current_role.id)

        # Extract file type from filename
        filename = file.filename or "file"
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"

        # Create database record
        resume = await resume_service.create_resume(
            role_id=current_role.id,
            filename=filename,
            file_type=extension,
            file_path=file_path,
            file_size=file_size
        )

        return ResumeRead.model_validate(resume)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=list[ResumeRead])
async def list_resumes(
    current_role: Role = Depends(get_current_role)
) -> list[ResumeRead]:
    """Get all resumes for the current role."""
    resumes = await resume_service.get_resumes(current_role.id)
    return [ResumeRead.model_validate(r) for r in resumes]


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: int,
    current_role: Role = Depends(get_current_role)
) -> None:
    """Delete a resume (file and database record)."""
    try:
        await resume_service.delete_resume(resume_id, current_role.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
