"""Authentication API endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.models.user import UserCreate, UserRead
from app.services import auth_service


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Username taken or max accounts reached"},
        400: {"description": "Validation error"}
    }
)
async def register(user_data: UserCreate):
    """
    Register a new user account.

    - Maximum 2 accounts allowed (FR4)
    - Username must be 3-50 characters
    - Password must be 8+ characters
    """
    try:
        user = await auth_service.create_user(user_data)
        return UserRead.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.get("/account-limit")
async def check_account_limit():
    """Check if new registrations are allowed."""
    count = await auth_service.get_user_count()
    return {
        "current_count": count,
        "max_accounts": auth_service.MAX_ACCOUNTS,
        "registration_allowed": count < auth_service.MAX_ACCOUNTS
    }
