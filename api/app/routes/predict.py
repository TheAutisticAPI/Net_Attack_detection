"""Prediction endpoint — accepts flow features and returns inference results."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.schemas import FlowFeatures, PredictionResponse
from app.services.prediction import prediction_service

router = APIRouter(prefix="/predict", tags=["prediction"])


@router.post(
    "",
    response_model=PredictionResponse,
    status_code=200,
    summary="Run inference on a network flow",
    description=(
        "Accepts flow metadata and extracted features, runs the classification "
        "model (mock in Phase 1), persists the flow / prediction / alert records, "
        "and returns the prediction result."
    ),
)
async def create_prediction(
    payload: FlowFeatures,
    db: AsyncSession = Depends(get_db),
) -> PredictionResponse:
    """Run model inference and return the prediction."""
    return await prediction_service.predict(
        src_ip=payload.src_ip,
        dst_ip=payload.dst_ip,
        src_port=payload.src_port,
        dst_port=payload.dst_port,
        protocol=payload.protocol,
        features=payload.features,
        db=db,
    )
