import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AccountDisabledException,
    BadRequestException,
    ConflictException,
    InvalidTokenException,
    NotFoundException,
    TokenExpiredException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import UserRole
from app.repositories.token_repository import (
    email_verification_token_repository,
    password_reset_token_repository,
    refresh_token_repository,
)
from app.repositories.user_repository import user_repository
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.schemas.user import UserResponse
from app.services.email_service import email_service
from app.services.redis_service import redis_service

logger = logging.getLogger(__name__)

_EMAIL_VERIFY_TTL_HOURS = 24
_PASSWORD_RESET_TTL_HOURS = 1


class AuthService:
    async def register(self, db: AsyncSession, data: RegisterRequest) -> UserResponse:
        if await user_repository.email_exists(db, data.email):
            raise ConflictException("An account with this email already exists.")
        if await user_repository.username_exists(db, data.username):
            raise ConflictException("This username is already taken.")

        user = await user_repository.create(
            db,
            email=data.email,
            username=data.username,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=UserRole.USER,
            is_active=True,
            is_verified=False,
        )

        token_str = str(uuid.uuid4())
        await email_verification_token_repository.create(
            db,
            token=token_str,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc)
            + timedelta(hours=_EMAIL_VERIFY_TTL_HOURS),
        )

        await email_service.send_verification_email(user.email, token_str)
        logger.info("User registered | id=%s email=%s", user.id, user.email)
        return UserResponse.model_validate(user)

    async def login(self, db: AsyncSession, data: LoginRequest) -> dict:
        user = await user_repository.get_by_email(db, data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            # Identical message for both "not found" and "wrong password" to
            # prevent user-enumeration attacks.
            raise BadRequestException("Invalid email or password.")

        if not user.is_active:
            raise AccountDisabledException()

        access_token, _jti, _exp = create_access_token(
            subject=str(user.id),
            role=user.role.value,
            email=user.email,
        )
        refresh_token_str, refresh_expires = create_refresh_token()

        await refresh_token_repository.create(
            db,
            token=refresh_token_str,
            user_id=user.id,
            expires_at=refresh_expires,
        )

        logger.info("User logged in | id=%s", user.id)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token_str,
            "token_type": "bearer",
        }

    async def refresh(self, db: AsyncSession, data: RefreshTokenRequest) -> dict:
        db_token = await refresh_token_repository.get_by_token(db, data.refresh_token)

        if not db_token or db_token.revoked:
            raise InvalidTokenException()

        # Ensure the stored datetime is timezone-aware before comparison
        token_exp = db_token.expires_at
        if token_exp.tzinfo is None:
            token_exp = token_exp.replace(tzinfo=timezone.utc)
        if token_exp < datetime.now(timezone.utc):
            raise TokenExpiredException()

        user = await user_repository.get_by_id(db, db_token.user_id)
        if not user or not user.is_active:
            raise AccountDisabledException()

        # Rotate: revoke old token, issue new pair
        await refresh_token_repository.revoke_token(db, data.refresh_token)

        access_token, _jti, _exp = create_access_token(
            subject=str(user.id),
            role=user.role.value,
            email=user.email,
        )
        new_refresh_token, new_refresh_expires = create_refresh_token()
        await refresh_token_repository.create(
            db,
            token=new_refresh_token,
            user_id=user.id,
            expires_at=new_refresh_expires,
        )

        logger.info("Tokens refreshed | user_id=%s", user.id)
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

    async def logout(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        jti: str,
        token_exp: int,
        refresh_token: str | None = None,
    ) -> None:
        # Blacklist the access token for its remaining lifetime
        remaining_ttl = token_exp - int(datetime.now(timezone.utc).timestamp())
        await redis_service.blacklist_token(jti, remaining_ttl)

        if refresh_token:
            await refresh_token_repository.revoke_token(db, refresh_token)
        else:
            await refresh_token_repository.revoke_all_for_user(db, user_id)

        logger.info("User logged out | user_id=%s", user_id)

    async def forgot_password(
        self, db: AsyncSession, data: ForgotPasswordRequest
    ) -> None:
        user = await user_repository.get_by_email(db, data.email)
        if not user:
            # Silently return to prevent email enumeration
            return

        token_str = str(uuid.uuid4())
        await password_reset_token_repository.create(
            db,
            token=token_str,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc)
            + timedelta(hours=_PASSWORD_RESET_TTL_HOURS),
        )
        await email_service.send_password_reset_email(user.email, token_str)
        logger.info("Password reset requested | user_id=%s", user.id)

    async def reset_password(
        self, db: AsyncSession, data: ResetPasswordRequest
    ) -> None:
        db_token = await password_reset_token_repository.get_by_token(db, data.token)

        if not db_token or db_token.used:
            raise InvalidTokenException()

        token_exp = db_token.expires_at
        if token_exp.tzinfo is None:
            token_exp = token_exp.replace(tzinfo=timezone.utc)
        if token_exp < datetime.now(timezone.utc):
            raise TokenExpiredException()

        user = await user_repository.get_by_id(db, db_token.user_id)
        if not user:
            raise NotFoundException("User")

        await user_repository.update(
            db, user, hashed_password=hash_password(data.new_password)
        )
        await password_reset_token_repository.mark_used(db, data.token)
        # Force re-login on all devices after password change
        await refresh_token_repository.revoke_all_for_user(db, user.id)
        logger.info("Password reset completed | user_id=%s", user.id)

    async def verify_email(self, db: AsyncSession, data: VerifyEmailRequest) -> None:
        db_token = await email_verification_token_repository.get_by_token(
            db, data.token
        )

        if not db_token or db_token.used:
            raise InvalidTokenException()

        token_exp = db_token.expires_at
        if token_exp.tzinfo is None:
            token_exp = token_exp.replace(tzinfo=timezone.utc)
        if token_exp < datetime.now(timezone.utc):
            raise TokenExpiredException()

        user = await user_repository.get_by_id(db, db_token.user_id)
        if not user:
            raise NotFoundException("User")

        await user_repository.update(db, user, is_verified=True)
        await email_verification_token_repository.mark_used(db, data.token)
        logger.info("Email verified | user_id=%s", user.id)


auth_service = AuthService()
