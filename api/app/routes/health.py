"""Health-check endpoint."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.schemas import HealthResponse

router = APIRouter(tags=["health"])

# Captured at module import — used to calculate uptime.
_START_TIME: float = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns API status, database connectivity, version, and uptime.",
)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Verify API and database are operational."""
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        database=db_status,
        api_version=settings.API_VERSION,
        uptime_seconds=round(time.time() - _START_TIME, 2),
    )
