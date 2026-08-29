"""
GET /api/v1/health

Reports real service health. Never exposes secrets or internal
configuration values - only booleans / short status strings.
"""
from fastapi import APIRouter

from app.config import get_settings
from app.database.session import check_database_connection
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()
    db_ok = check_database_connection()

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        app_name=settings.APP_NAME,
        app_env=settings.APP_ENV,
        database=db_ok,
    )
