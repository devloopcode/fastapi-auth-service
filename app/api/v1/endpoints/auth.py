import logging

from fastapi import APIRouter, Depends, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.dependencies.auth import get_current_user, oauth2_scheme
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserResponse
from app.services.auth_service import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    return await auth_service.register(db, data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive JWT tokens",
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    result = await auth_service.login(db, data)
    return TokenResponse(**result)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate tokens using a valid refresh token",
)
async def refresh_tokens(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    result = await auth_service.refresh(db, data)
    return TokenResponse(**result)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Invalidate tokens and end the session",
)
async def logout(
    data: LogoutRequest,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    jti, exp = "", 0
    try:
        payload = decode_access_token(token)
        jti = payload.get("jti", "")
        exp = int(payload.get("exp", 0))
    except JWTError:
        pass  # Token already invalid — proceed to clean up DB state

    await auth_service.logout(
        db,
        user_id=current_user.id,
        jti=jti,
        token_exp=exp,
        refresh_token=data.refresh_token,
    )
    return MessageResponse(message="Successfully logged out.")


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request a password-reset email",
)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await auth_service.forgot_password(db, data)
    # Always return the same message to prevent email enumeration
    return MessageResponse(
        message="If that email is registered you will receive a reset link shortly."
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Set a new password using a reset token",
)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await auth_service.reset_password(db, data)
    return MessageResponse(message="Password has been reset successfully.")


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Confirm an email address using a verification token",
)
async def verify_email(
    data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await auth_service.verify_email(db, data)
    return MessageResponse(message="Email verified successfully.")
