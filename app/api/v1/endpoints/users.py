import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, require_admin
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import user_service
from app.utils.pagination import PaginationParams

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    return await user_service.get_me(db, current_user.id)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update the currently authenticated user's profile",
)
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    return await user_service.update_me(db, current_user.id, data)


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
    summary="List all users (admin only)",
)
async def list_users(
    params: PaginationParams = Depends(),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[UserResponse]:
    return await user_service.get_users(db, page=params.page, per_page=params.per_page)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user by ID (admin only)",
)
async def delete_user(
    user_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    await user_service.delete_user(db, user_id)
