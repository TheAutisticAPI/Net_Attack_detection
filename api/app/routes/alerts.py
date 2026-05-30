"""Alert endpoints — list (paginated + filtered) and detail."""

from __future__ import annotations

import math
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert
from app.db.session import get_db
from app.models.schemas import (
    AlertBase,
    AlertFilterParams,
    AlertListResponse,
    AlertResponse,
    PaginationMeta,
    SortField,
    SortOrder,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _build_filters(params: AlertFilterParams, query):  # noqa: ANN001
    """Apply WHERE clauses to a SQLAlchemy select based on filter params."""
    if params.label is not None:
        query = query.where(Alert.label == params.label)
    if params.min_confidence is not None:
        query = query.where(Alert.confidence >= params.min_confidence)
    if params.max_confidence is not None:
        query = query.where(Alert.confidence <= params.max_confidence)
    if params.start_time is not None:
        query = query.where(Alert.created_at >= params.start_time)
    if params.end_time is not None:
        query = query.where(Alert.created_at <= params.end_time)
    if params.severity is not None:
        query = query.where(Alert.severity == params.severity.value)
    if params.anomaly_flag is not None:
        if params.anomaly_flag:
            query = query.where(Alert.anomaly_score.isnot(None))
        else:
            query = query.where(Alert.anomaly_score.is_(None))
    return query


def _apply_sorting(params: AlertFilterParams, query):  # noqa: ANN001
    """Apply ORDER BY to the query."""
    column_map = {
        SortField.CREATED_AT: Alert.created_at,
        SortField.CONFIDENCE: Alert.confidence,
        SortField.ANOMALY_SCORE: Alert.anomaly_score,
    }
    col = column_map[params.sort_by]
    if params.sort_order == SortOrder.ASC:
        query = query.order_by(col.asc())
    else:
        query = query.order_by(col.desc())
    return query


@router.get(
    "",
    response_model=AlertListResponse,
    summary="List alerts",
    description="Paginated, filterable, sortable list of security alerts.",
)
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    # ── filter params ─────────────────────────────────────────────────
    label: str | None = Query(default=None, description="Filter by predicted label"),
    min_confidence: float | None = Query(default=None, ge=0.0, le=1.0),
    max_confidence: float | None = Query(default=None, ge=0.0, le=1.0),
    start_time: datetime | None = Query(default=None, description="ISO-8601 start"),
    end_time: datetime | None = Query(default=None, description="ISO-8601 end"),
    anomaly_flag: bool | None = Query(default=None),
    severity: str | None = Query(default=None, description="low|medium|high|critical"),
    # ── sorting / pagination ──────────────────────────────────────────
    sort_by: SortField = Query(default=SortField.CREATED_AT),
    sort_order: SortOrder = Query(default=SortOrder.DESC),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AlertListResponse:
    """Return a paginated list of alerts with optional filters."""
    params = AlertFilterParams(
        label=label,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
        start_time=start_time,
        end_time=end_time,
        anomaly_flag=anomaly_flag,
        severity=severity,  # type: ignore[arg-type]
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )

    # Count total matching rows
    count_q = select(func.count()).select_from(Alert)
    count_q = _build_filters(params, count_q)
    total_items = (await db.execute(count_q)).scalar_one()

    # Fetch page
    data_q = select(Alert)
    data_q = _build_filters(params, data_q)
    data_q = _apply_sorting(params, data_q)
    data_q = data_q.offset((params.page - 1) * params.page_size).limit(params.page_size)
    result = await db.execute(data_q)
    alerts = result.scalars().all()

    total_pages = math.ceil(total_items / params.page_size) if total_items else 0

    return AlertListResponse(
        items=[AlertBase.model_validate(a) for a in alerts],
        pagination=PaginationMeta(
            page=params.page,
            page_size=params.page_size,
            total_items=total_items,
            total_pages=total_pages,
        ),
    )


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Get alert detail",
    description="Retrieve a single alert by its UUID.",
)
async def get_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AlertResponse:
    """Return a single alert or 404."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return AlertResponse.model_validate(alert)
