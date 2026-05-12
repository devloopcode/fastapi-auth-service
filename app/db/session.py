from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

# get_settings() is cached via @lru_cache, so reading DATABASE_URL here always
# picks up whatever value was in the environment at first call — including any
# overrides set by the test suite before the first import.
_settings = get_settings()

engine = create_async_engine(
    _settings.DATABASE_URL,
    echo=_settings.DEBUG,
    pool_pre_ping=True,
    # SQLite does not support pool_size / max_overflow — omit those kwargs
    # when not using PostgreSQL.
    **({} if "sqlite" in _settings.DATABASE_URL else {"pool_size": 10, "max_overflow": 20}),
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)
