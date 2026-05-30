"""Pydantic v2 request / response schemas for the NIDS API."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Enums ─────────────────────────────────────────────────────────────────────

class SeverityLevel(str, Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Origin of the alert."""

    CLASSIFIER = "classifier"
    ANOMALY = "anomaly"


class SortField(str, Enum):
    """Allowed sort fields for alert listing."""

    CREATED_AT = "created_at"
    CONFIDENCE = "confidence"
    ANOMALY_SCORE = "anomaly_score"


class SortOrder(str, Enum):
    """Sort direction."""

    ASC = "asc"
    DESC = "desc"


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """GET /health response."""

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(..., examples=["ok"])
    database: str = Field(..., examples=["connected"])
    api_version: str = Field(..., examples=["0.1.0"])
    uptime_seconds: float = Field(..., ge=0)


# ── Flow / Prediction ────────────────────────────────────────────────────────

class FlowFeatures(BaseModel):
    """Input schema for POST /predict.

    Uses a flexible dict so the feature set can evolve without schema changes.
    At least one feature must be present.
    """

    model_config = ConfigDict(from_attributes=True)

    src_ip: str = Field(..., examples=["192.168.1.100"])
    dst_ip: str = Field(..., examples=["10.0.0.1"])
    src_port: int = Field(..., ge=0, le=65535, examples=[54321])
    dst_port: int = Field(..., ge=0, le=65535, examples=[80])
    protocol: int = Field(..., ge=0, examples=[6])
    features: dict[str, float] = Field(
        ...,
        min_length=1,
        examples=[{"flow_duration": 1.23, "total_fwd_packets": 10.0}],
    )

    @field_validator("features")
    @classmethod
    def features_must_be_numeric(cls, v: dict[str, float]) -> dict[str, float]:
        """Ensure every value in the features dict is a finite number."""
        import math

        for key, val in v.items():
            if not isinstance(val, (int, float)):
                raise ValueError(f"Feature '{key}' must be numeric, got {type(val).__name__}")
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"Feature '{key}' must be finite, got {val}")
        return v


class PredictionResponse(BaseModel):
    """POST /predict response."""

    model_config = ConfigDict(from_attributes=True)

    prediction_id: uuid.UUID
    flow_id: uuid.UUID
    alert_id: uuid.UUID
    label: str = Field(..., examples=["BENIGN"])
    confidence: float = Field(..., ge=0.0, le=1.0)
    class_probabilities: dict[str, float] = Field(
        ...,
        examples=[{"BENIGN": 0.95, "DDoS": 0.03, "PortScan": 0.02}],
    )
    anomaly_score: float | None = Field(default=None)
    inference_latency_ms: float = Field(..., ge=0)


# ── Alerts ────────────────────────────────────────────────────────────────────

class AlertBase(BaseModel):
    """Shared alert fields."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prediction_id: uuid.UUID
    flow_id: uuid.UUID
    alert_type: str
    severity: str
    label: str
    confidence: float
    anomaly_score: float | None = None
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: int
    case_status: str | None = None
    analyst_verdict: str | None = None
    tenant_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class AlertResponse(AlertBase):
    """GET /alerts/{id} response — full alert detail."""

    pass


class PaginationMeta(BaseModel):
    """Pagination metadata included in list responses."""

    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_items: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)


class AlertListResponse(BaseModel):
    """GET /alerts response — paginated alert list."""

    items: list[AlertBase]
    pagination: PaginationMeta


class AlertFilterParams(BaseModel):
    """Query-parameter schema for alert filtering.

    Used internally — FastAPI Query() params are extracted in the route and
    validated into this model.
    """

    label: str | None = None
    min_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    max_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    start_time: datetime | None = None
    end_time: datetime | None = None
    anomaly_flag: bool | None = None
    severity: SeverityLevel | None = None
    sort_by: SortField = SortField.CREATED_AT
    sort_order: SortOrder = SortOrder.DESC
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# ── Model Versions ───────────────────────────────────────────────────────────

class ModelVersionResponse(BaseModel):
    """Single model version in the registry."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    version: str
    stage: str
    framework: str
    metrics: dict | None = None
    hyperparameters: dict | None = None
    created_at: datetime


class ModelListResponse(BaseModel):
    """GET /models response."""

    items: list[ModelVersionResponse]
    total: int
