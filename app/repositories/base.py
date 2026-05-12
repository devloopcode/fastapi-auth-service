import uuid
from typing import Any, Generic, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic async repository providing common CRUD operations."""

    def __init__(self, model: Type[ModelType]) -> None:
        self.model = model

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> ModelType | None:
        result = await db.execute(select(self.model).where(self.model.id == id))  # type: ignore[attr-defined]
        return result.scalar_one_or_none()

    async def get_all(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 20
    ) -> tuple[list[ModelType], int]:
        count_result = await db.execute(
            select(func.count()).select_from(self.model)
        )
        total: int = count_result.scalar_one()

        result = await db.execute(select(self.model).offset(skip).limit(limit))
        items = list(result.scalars().all())
        return items, total

    async def create(self, db: AsyncSession, **kwargs: Any) -> ModelType:
        instance = self.model(**kwargs)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def update(
        self, db: AsyncSession, instance: ModelType, **kwargs: Any
    ) -> ModelType:
        for key, value in kwargs.items():
            setattr(instance, key, value)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def delete(self, db: AsyncSession, instance: ModelType) -> None:
        await db.delete(instance)
        await db.flush()
