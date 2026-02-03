"""Role management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.user import User
from app.models.role import RoleCreate, RoleRead
from app.services import role_service


router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RoleRead])
async def list_roles(
    current_user: User = Depends(get_current_user)
) -> list[RoleRead]:
    """Get all roles for the current user."""
    roles = await role_service.get_roles_by_user(current_user.id)
    return [RoleRead.model_validate(role) for role in roles]


@router.post("", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(get_current_user)
) -> RoleRead:
    """Create a new role for the current user."""
    role = await role_service.create_role(current_user.id, role_data)
    return RoleRead.model_validate(role)


@router.get("/{role_id}", response_model=RoleRead)
async def get_role(
    role_id: int,
    current_user: User = Depends(get_current_user)
) -> RoleRead:
    """Get a specific role (ownership verified)."""
    role = await role_service.get_role_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    if role.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this role"
        )
    return RoleRead.model_validate(role)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    current_user: User = Depends(get_current_user)
) -> None:
    """Delete a role (ownership verified)."""
    try:
        await role_service.delete_role(role_id, current_user.id)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this role"
        )
