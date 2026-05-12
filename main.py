import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.middleware.logging import RequestLoggingMiddleware
from app.services.redis_service import redis_service

configure_logging(debug=settings.DEBUG)
logger = logging.getLogger(__name__)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(
        "Starting %s v%s [%s]",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.ENVIRONMENT,
    )
    yield
    await redis_service.close()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production-ready authentication API with JWT, refresh token rotation, "
        "RBAC, email verification, rate limiting, and Redis-backed token revocation."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── Rate limiter state ────────────────────────────────────────────────────────
app.state.limiter = limiter

# ── Middleware (added in reverse execution order) ─────────────────────────────
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ────────────────────────────────────────────────────────
register_exception_handlers(app)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(api_router)


@app.get("/", tags=["Root"], include_in_schema=False)
async def root() -> dict:
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
