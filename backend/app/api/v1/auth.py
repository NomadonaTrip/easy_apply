"""Authentication API endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Response, Depends, Cookie
from pydantic import BaseModel

from app.models.user import User, UserCreate, UserRead
from app.services import auth_service, session_service
from app.api.deps import get_current_user


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Request schema for login."""
    username: str
    password: str


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


@router.post(
    "/login",
    response_model=UserRead,
    responses={
        401: {"description": "Invalid credentials"}
    }
)
async def login(login_data: LoginRequest, response: Response):
    """
    Authenticate user and create session.

    Sets HTTP-only session cookie on success.
    """
    # Get user by username
    user = await auth_service.get_user_by_username(login_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Verify password
    if not auth_service.verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Create session
    session_token = session_service.create_session(user.id)

    # Set HTTP-only cookie
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        secure=False,  # Set True in production with HTTPS
        samesite="lax",
        max_age=session_service.SESSION_TIMEOUT_HOURS * 3600
    )

    return UserRead.model_validate(user)


@router.get(
    "/me",
    response_model=UserRead,
    responses={
        401: {"description": "Not authenticated"}
    }
)
async def get_current_user_endpoint(
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user."""
    return UserRead.model_validate(current_user)


@router.post("/logout")
async def logout(
    response: Response,
    session: Optional[str] = Cookie(default=None)
):
    """
    Log out the current user.

    Invalidates the session server-side and clears the session cookie.
    """
    if session:
        session_service.invalidate_session(session)

    # Clear the cookie by setting it to expire immediately
    response.delete_cookie(
        key="session",
        httponly=True,
        secure=False,  # Set True in production
        samesite="lax"
    )

    return {"message": "Logged out successfully"}
