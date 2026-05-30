"""Model version registry endpoint."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ModelVersion
from app.db.session import get_db
from app.models.schemas import ModelListResponse, ModelVersionResponse

router = APIRouter(prefix="/models", tags=["models"])

# Mock model data returned when the DB is empty (Phase 1 placeholder).
_MOCK_MODELS: list[dict] = [
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "name": "nids-classifier",
        "version": "1",
        "stage": "Production",
        "framework": "lightgbm",
        "metrics": {"accuracy": 0.9823, "f1_macro": 0.9741, "log_loss": 0.0612},
        "hyperparameters": {
            "n_estimators": 300,
            "learning_rate": 0.05,
            "max_depth": 8,
            "num_leaves": 63,
        },
        "created_at": datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
        "name": "nids-classifier",
        "version": "2",
        "stage": "Staging",
        "framework": "xgboost",
        "metrics": {"accuracy": 0.9845, "f1_macro": 0.9762, "log_loss": 0.0584},
        "hyperparameters": {
            "n_estimators": 500,
            "learning_rate": 0.03,
            "max_depth": 10,
        },
        "created_at": datetime(2026, 3, 20, 9, 30, 0, tzinfo=timezone.utc),
    },
]


@router.get(
    "",
    response_model=ModelListResponse,
    summary="List model versions",
    description=(
        "Returns all registered model versions. In Phase 1 this falls back to "
        "mock data when no rows exist in the database."
    ),
)
async def list_models(
    db: AsyncSession = Depends(get_db),
) -> ModelListResponse:
    """Return model versions from the DB, falling back to mock data."""
    count = (await db.execute(select(func.count()).select_from(ModelVersion))).scalar_one()

    if count > 0:
        result = await db.execute(
            select(ModelVersion).order_by(ModelVersion.created_at.desc())
        )
        rows = result.scalars().all()
        items = [ModelVersionResponse.model_validate(r) for r in rows]
    else:
        # Phase 1 fallback — return mock model versions
        items = [ModelVersionResponse(**m) for m in _MOCK_MODELS]

    return ModelListResponse(items=items, total=len(items))
