import logging

from app.db.base import Base
from app.db.session import engine

# Side-effect import: registers all models with Base.metadata
import app.models  # noqa: F401

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Create all tables. Use only in development; prefer Alembic in production."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created.")
