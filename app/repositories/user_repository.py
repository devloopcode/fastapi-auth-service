from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self) -> None:
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, username: str) -> User | None:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def email_exists(self, db: AsyncSession, email: str) -> bool:
        result = await db.execute(select(User.id).where(User.email == email))
        return result.scalar_one_or_none() is not None

    async def username_exists(self, db: AsyncSession, username: str) -> bool:
        result = await db.execute(select(User.id).where(User.username == username))
        return result.scalar_one_or_none() is not None


user_repository = UserRepository()
