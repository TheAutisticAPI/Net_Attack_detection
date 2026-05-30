"""FastAPI application factory with lifespan, CORS, and router registration."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routes import alerts, health, models, predict
from app.services.prediction import prediction_service

logging.basicConfig(
    level=logging.DEBUG if settings.API_DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown hooks.

    Startup:
      1. Log configuration
      2. Load ML model (mock in Phase 1)

    Shutdown:
      1. Dispose DB engine connections
    """
    logger.info("Starting %s v%s", settings.API_TITLE, settings.API_VERSION)
    logger.info("Database URL: %s", settings.DATABASE_URL.split("@")[-1])  # hide creds
    logger.info("MLflow URI:   %s", settings.MLFLOW_TRACKING_URI)

    # Pre-load model
    await prediction_service._load_model()

    yield  # ── application runs ──

    # Shutdown
    from app.db.session import engine

    await engine.dispose()
    logger.info("Database connections disposed — shutdown complete")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    app = FastAPI(
        title=settings.API_TITLE,
        description=(
            "Network Intrusion Detection System API.  "
            "Provides real-time flow classification, alert management, "
            "and model version tracking."
        ),
        version=settings.API_VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ──────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.API_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(predict.router)
    app.include_router(alerts.router)
    app.include_router(models.router)

    return app


# Module-level app instance used by `uvicorn app.main:app`
app = create_app()
