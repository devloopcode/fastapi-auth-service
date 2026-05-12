import logging
import uuid

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AccountDisabledException,
    ForbiddenException,
    InvalidTokenException,
)
from app.core.security import decode_access_token
from app.dependencies.database import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import user_repository
from app.services.redis_service import redis_service

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise InvalidTokenException()

    if payload.get("type") != "access":
        raise InvalidTokenException()

    jti: str | None = payload.get("jti")
    if jti and await redis_service.is_token_blacklisted(jti):
        raise InvalidTokenException()

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise InvalidTokenException()

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise InvalidTokenException()

    user = await user_repository.get_by_id(db, user_uuid)
    if not user:
        raise InvalidTokenException()

    if not user.is_active:
        raise AccountDisabledException()

    return user


async def get_current_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    from app.core.exceptions import AccountNotVerifiedException
    if not current_user.is_verified:
        raise AccountNotVerifiedException()
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenException("Admin access required.")
    return current_user
