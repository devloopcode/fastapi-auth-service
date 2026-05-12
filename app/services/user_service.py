import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.repositories.user_repository import user_repository
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserResponse, UserUpdate

logger = logging.getLogger(__name__)


class UserService:
    async def get_me(self, db: AsyncSession, user_id: uuid.UUID) -> UserResponse:
        user = await user_repository.get_by_id(db, user_id)
        if not user:
            raise NotFoundException("User")
        return UserResponse.model_validate(user)

    async def get_users(
        self, db: AsyncSession, *, page: int = 1, per_page: int = 20
    ) -> PaginatedResponse[UserResponse]:
        skip = (page - 1) * per_page
        users, total = await user_repository.get_all(db, skip=skip, limit=per_page)
        pages = max(1, (total + per_page - 1) // per_page)
        return PaginatedResponse(
            items=[UserResponse.model_validate(u) for u in users],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
        )

    async def update_me(
        self, db: AsyncSession, user_id: uuid.UUID, data: UserUpdate
    ) -> UserResponse:
        user = await user_repository.get_by_id(db, user_id)
        if not user:
            raise NotFoundException("User")

        updates = data.model_dump(exclude_none=True)

        if "username" in updates and updates["username"] != user.username:
            if await user_repository.username_exists(db, updates["username"]):
                raise ConflictException("This username is already taken.")

        updated = await user_repository.update(db, user, **updates)
        logger.info("User profile updated | user_id=%s", user_id)
        return UserResponse.model_validate(updated)

    async def delete_user(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        user = await user_repository.get_by_id(db, user_id)
        if not user:
            raise NotFoundException("User")
        await user_repository.delete(db, user)
        logger.info("User deleted | user_id=%s", user_id)


user_service = UserService()
