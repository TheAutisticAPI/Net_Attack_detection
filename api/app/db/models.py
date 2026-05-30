"""SQLAlchemy ORM models for the NIDS database.

All tables are designed for forward-compatibility:
  - Phase 2: anomaly_score / anomaly_flag on Prediction
  - Phase 3: SHAP explanations via ShapExplanation
  - Phase 5: case management fields on Alert
  - Phase 6: tenant_id for multi-tenant RLS
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# ── helpers ───────────────────────────────────────────────────────────────────

def _uuid_pk() -> Mapped[uuid.UUID]:
    """Primary-key UUID column with a server-side default."""
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


def _created_at() -> Mapped[datetime]:
    """Timestamp column that defaults to UTC now on the server."""
    return mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


def _updated_at() -> Mapped[datetime]:
    """Timestamp column that auto-updates on every write."""
    return mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ── Flow ──────────────────────────────────────────────────────────────────────

class Flow(Base):
    """Raw network flow record with extracted feature vector."""

    __tablename__ = "flows"

    id: Mapped[uuid.UUID] = _uuid_pk()
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    src_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    dst_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    src_port: Mapped[int] = mapped_column(Integer, nullable=False)
    dst_port: Mapped[int] = mapped_column(Integer, nullable=False)
    protocol: Mapped[int] = mapped_column(Integer, nullable=False)
    features: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = _created_at()

    # relationships
    predictions: Mapped[list[Prediction]] = relationship(
        back_populates="flow", cascade="all, delete-orphan"
    )
    alerts: Mapped[list[Alert]] = relationship(
        back_populates="flow", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_flows_timestamp", "timestamp"),
        Index("ix_flows_src_ip", "src_ip"),
        Index("ix_flows_dst_ip", "dst_ip"),
    )


# ── Prediction ────────────────────────────────────────────────────────────────

class Prediction(Base):
    """Model inference result linked to a Flow."""

    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    flow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("flows.id", ondelete="CASCADE"), nullable=False
    )
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    class_probabilities: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Phase 2 – anomaly detection
    anomaly_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    anomaly_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    inference_latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = _created_at()

    # relationships
    flow: Mapped[Flow] = relationship(back_populates="predictions")
    alerts: Mapped[list[Alert]] = relationship(
        back_populates="prediction", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_predictions_flow_id", "flow_id"),
        Index("ix_predictions_label", "label"),
        Index("ix_predictions_created_at", "created_at"),
    )


# ── Alert ─────────────────────────────────────────────────────────────────────

class Alert(Base):
    """Security alert generated from a prediction.

    Forward-compatible columns:
      * case_status / analyst_verdict → Phase 5 case management
      * tenant_id → Phase 6 multi-tenant RLS
    """

    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = _uuid_pk()
    prediction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("predictions.id", ondelete="CASCADE"),
        nullable=False,
    )
    flow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("flows.id", ondelete="CASCADE"),
        nullable=False,
    )

    alert_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="classifier"
    )  # 'classifier' | 'anomaly'
    severity: Mapped[str] = mapped_column(
        String(16), nullable=False, default="medium"
    )  # low | medium | high | critical
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    anomaly_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Denormalized flow metadata for fast querying
    src_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    dst_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    src_port: Mapped[int] = mapped_column(Integer, nullable=False)
    dst_port: Mapped[int] = mapped_column(Integer, nullable=False)
    protocol: Mapped[int] = mapped_column(Integer, nullable=False)

    # Phase 5 – case management
    case_status: Mapped[str | None] = mapped_column(String(32), nullable=True, default=None)
    analyst_verdict: Mapped[str | None] = mapped_column(String(32), nullable=True, default=None)

    # Phase 6 – multi-tenant
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, default=None
    )

    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()

    # relationships
    prediction: Mapped[Prediction] = relationship(back_populates="alerts")
    flow: Mapped[Flow] = relationship(back_populates="alerts")
    shap_explanations: Mapped[list[ShapExplanation]] = relationship(
        back_populates="alert", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_alerts_label", "label"),
        Index("ix_alerts_severity", "severity"),
        Index("ix_alerts_confidence", "confidence"),
        Index("ix_alerts_created_at", "created_at"),
        Index("ix_alerts_tenant_id", "tenant_id"),
        Index("ix_alerts_case_status", "case_status"),
    )


# ── ShapExplanation ───────────────────────────────────────────────────────────

class ShapExplanation(Base):
    """SHAP feature-attribution explanation for an alert (Phase 3)."""

    __tablename__ = "shap_explanations"

    id: Mapped[uuid.UUID] = _uuid_pk()
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
    )
    feature_names: Mapped[list] = mapped_column(JSON, nullable=False)
    shap_values: Mapped[list] = mapped_column(JSON, nullable=False)
    base_value: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = _created_at()

    # relationships
    alert: Mapped[Alert] = relationship(back_populates="shap_explanations")

    __table_args__ = (
        Index("ix_shap_explanations_alert_id", "alert_id"),
    )


# ── ModelVersion ──────────────────────────────────────────────────────────────

class ModelVersion(Base):
    """Registry of ML model versions (mirrors MLflow registry)."""

    __tablename__ = "model_versions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    stage: Mapped[str] = mapped_column(
        String(32), nullable=False, default="None"
    )  # None | Staging | Production | Archived
    framework: Mapped[str] = mapped_column(
        String(32), nullable=False, default="lightgbm"
    )  # lightgbm | xgboost
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    hyperparameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = _created_at()

    __table_args__ = (
        Index("ix_model_versions_name_version", "name", "version", unique=True),
        Index("ix_model_versions_stage", "stage"),
    )
