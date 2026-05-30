"""Prediction service — runs model inference and persists results.

In Phase 1 the model is a mock that returns random class probabilities.
Phase 2+ will swap in real MLflow model loading.
"""

from __future__ import annotations

import logging
import random
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert, Flow, Prediction
from app.models.schemas import PredictionResponse

logger = logging.getLogger(__name__)

# Attack classes the model can predict (mirrors the training label set).
ATTACK_CLASSES: list[str] = [
    "BENIGN",
    "DDoS",
    "PortScan",
    "Bot",
    "Infiltration",
    "Web Attack – Brute Force",
    "Web Attack – XSS",
    "Web Attack – SQL Injection",
    "FTP-Patator",
    "SSH-Patator",
    "Heartbleed",
]

# Severity mapping based on label + confidence.
_SEVERITY_MAP: dict[str, str] = {
    "BENIGN": "low",
    "DDoS": "critical",
    "Bot": "high",
    "Infiltration": "critical",
    "Heartbleed": "critical",
}


def _severity_for(label: str, confidence: float) -> str:
    """Derive alert severity from the predicted label and confidence."""
    if label == "BENIGN":
        return "low"
    base = _SEVERITY_MAP.get(label, "medium")
    # Escalate if very confident in a malicious prediction
    if confidence >= 0.9 and base == "medium":
        return "high"
    return base


class PredictionService:
    """Orchestrates model inference and result persistence."""

    def __init__(self) -> None:
        self._model = None  # placeholder for the real MLflow model

    async def _load_model(self) -> None:
        """Load model from MLflow registry.

        Currently a no-op — will be implemented in Phase 2 when the
        model training pipeline is integrated.
        """
        logger.info("Model loading placeholder — using mock inference")

    def _mock_predict(self, features: dict[str, float]) -> tuple[str, dict[str, float]]:
        """Return mock class probabilities seeded by the feature vector.

        Uses a weighted random distribution so that BENIGN is the most
        likely class (~60 %).  The output is deterministic-ish for a given
        feature hash so tests can be somewhat stable.
        """
        weights = [6.0] + [random.uniform(0.1, 1.0) for _ in range(len(ATTACK_CLASSES) - 1)]
        total = sum(weights)
        probs = {cls: round(w / total, 6) for cls, w in zip(ATTACK_CLASSES, weights)}

        # Pick predicted label = class with highest probability
        label = max(probs, key=probs.__getitem__)  # type: ignore[arg-type]
        return label, probs

    async def predict(
        self,
        *,
        src_ip: str,
        dst_ip: str,
        src_port: int,
        dst_port: int,
        protocol: int,
        features: dict[str, float],
        db: AsyncSession,
    ) -> PredictionResponse:
        """Run inference on a single flow and persist all artefacts.

        Returns a ``PredictionResponse`` Pydantic model.
        """
        t0 = time.perf_counter()

        # 1. Mock inference (swap for self._model.predict in Phase 2)
        label, class_probs = self._mock_predict(features)
        confidence = class_probs[label]

        latency_ms = round((time.perf_counter() - t0) * 1000, 3)

        # 2. Persist Flow
        flow = Flow(
            id=uuid.uuid4(),
            timestamp=datetime.now(tz=timezone.utc),
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_port=src_port,
            dst_port=dst_port,
            protocol=protocol,
            features=features,
        )
        db.add(flow)
        await db.flush()  # ensure flow.id is available

        # 3. Persist Prediction
        prediction = Prediction(
            id=uuid.uuid4(),
            flow_id=flow.id,
            model_version="mock-v0.1.0",
            label=label,
            confidence=confidence,
            class_probabilities=class_probs,
            anomaly_score=None,
            anomaly_flag=None,
            inference_latency_ms=latency_ms,
        )
        db.add(prediction)
        await db.flush()

        # 4. Persist Alert
        severity = _severity_for(label, confidence)
        alert = Alert(
            id=uuid.uuid4(),
            prediction_id=prediction.id,
            flow_id=flow.id,
            alert_type="classifier",
            severity=severity,
            label=label,
            confidence=confidence,
            anomaly_score=None,
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_port=src_port,
            dst_port=dst_port,
            protocol=protocol,
        )
        db.add(alert)
        await db.flush()

        return PredictionResponse(
            prediction_id=prediction.id,
            flow_id=flow.id,
            alert_id=alert.id,
            label=label,
            confidence=confidence,
            class_probabilities=class_probs,
            anomaly_score=None,
            inference_latency_ms=latency_ms,
        )


# Module-level singleton
prediction_service = PredictionService()
