"""
Test configuration.

Tests use SQLite (via aiosqlite) — no PostgreSQL required.
Redis and email are mocked — no external services required.
"""

import os
import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

# Set env vars before importing any app module so that pydantic-settings
# picks up the SQLite URL instead of the production DATABASE_URL.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_auth.db"
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-characters")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# Clear the lru_cache so Settings() re-reads the patched environment
from app.core.config import get_settings  # noqa: E402
get_settings.cache_clear()

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import hash_password
from app.db.base import Base
from app.dependencies.database import get_db
from app.models.user import User, UserRole

# ── SQLite engine for tests ───────────────────────────────────────────────────
TEST_DB_URL = "sqlite+aiosqlite:///./test_auth.db"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


# ── Schema setup / teardown ───────────────────────────────────────────────────
@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    import app.models  # noqa: F401  registers all models with Base.metadata
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


# ── DB session per test ───────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


# ── Redis mock ────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def mock_redis():
    _blacklist: set[str] = set()

    async def fake_blacklist(jti: str, ttl: int) -> None:
        _blacklist.add(jti)

    async def fake_is_blacklisted(jti: str) -> bool:
        return jti in _blacklist

    async def fake_ping() -> bool:
        return True

    with (
        patch(
            "app.services.redis_service.redis_service.blacklist_token",
            side_effect=fake_blacklist,
        ),
        patch(
            "app.services.redis_service.redis_service.is_token_blacklisted",
            side_effect=fake_is_blacklisted,
        ),
        patch(
            "app.services.redis_service.redis_service.ping",
            side_effect=fake_ping,
        ),
        patch(
            "app.dependencies.auth.redis_service.is_token_blacklisted",
            side_effect=fake_is_blacklisted,
        ),
    ):
        yield


# ── Email mock ────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def mock_email():
    with (
        patch(
            "app.services.email_service.email_service.send_verification_email",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.email_service.email_service.send_password_reset_email",
            new_callable=AsyncMock,
        ),
    ):
        yield


# ── HTTP test client ──────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from main import app

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Reusable user fixtures ────────────────────────────────────────────────────
# Use flush() (not commit()) so that changes live only in the current session
# transaction and are automatically rolled back when the db fixture tears down.
@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        username="testuser",
        hashed_password=hash_password("TestPass123!"),
        full_name="Test User",
        role=UserRole.USER,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        username="adminuser",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    return user


# ── Auth helper ───────────────────────────────────────────────────────────────
async def get_auth_headers(client: AsyncClient, email: str, password: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
