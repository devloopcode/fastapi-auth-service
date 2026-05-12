from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.services.redis_service import redis_service

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    redis: str


@router.get(
    "",
    response_model=HealthResponse,
    summary="Service health check",
)
async def health_check() -> HealthResponse:
    redis_ok = await redis_service.ping()
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        redis="ok" if redis_ok else "unavailable",
    )
