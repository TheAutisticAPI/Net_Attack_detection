"""Tests for POST /predict endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


# ── Valid payload ─────────────────────────────────────────────────────────────

VALID_PAYLOAD = {
    "src_ip": "192.168.1.100",
    "dst_ip": "10.0.0.1",
    "src_port": 54321,
    "dst_port": 80,
    "protocol": 6,
    "features": {
        "flow_duration": 1.23,
        "total_fwd_packets": 10.0,
        "total_bwd_packets": 8.0,
        "flow_bytes_per_s": 5000.0,
        "flow_packets_per_s": 100.0,
    },
}


@pytest.mark.asyncio
async def test_predict_valid_returns_200(client: AsyncClient) -> None:
    """POST /predict with a valid payload should return 200."""
    response = await client.post("/predict", json=VALID_PAYLOAD)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_predict_response_has_label_and_confidence(client: AsyncClient) -> None:
    """Response must include label (str) and confidence (float 0–1)."""
    response = await client.post("/predict", json=VALID_PAYLOAD)
    data = response.json()

    assert "label" in data
    assert isinstance(data["label"], str)
    assert len(data["label"]) > 0

    assert "confidence" in data
    assert 0.0 <= data["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_predict_response_has_ids(client: AsyncClient) -> None:
    """Response must include prediction_id, flow_id, and alert_id as UUIDs."""
    response = await client.post("/predict", json=VALID_PAYLOAD)
    data = response.json()

    for field in ("prediction_id", "flow_id", "alert_id"):
        assert field in data
        # UUID strings are 36 chars (8-4-4-4-12)
        assert len(data[field]) == 36, f"{field} does not look like a UUID"


@pytest.mark.asyncio
async def test_predict_response_has_class_probabilities(client: AsyncClient) -> None:
    """Response must include class_probabilities dict summing to ~1.0."""
    response = await client.post("/predict", json=VALID_PAYLOAD)
    data = response.json()

    probs = data["class_probabilities"]
    assert isinstance(probs, dict)
    assert len(probs) > 0
    assert abs(sum(probs.values()) - 1.0) < 0.01


@pytest.mark.asyncio
async def test_predict_response_has_latency(client: AsyncClient) -> None:
    """Response must include inference_latency_ms >= 0."""
    response = await client.post("/predict", json=VALID_PAYLOAD)
    data = response.json()

    assert "inference_latency_ms" in data
    assert data["inference_latency_ms"] >= 0


@pytest.mark.asyncio
async def test_predict_invalid_empty_features(client: AsyncClient) -> None:
    """POST /predict with empty features dict should return 422."""
    payload = {**VALID_PAYLOAD, "features": {}}
    response = await client.post("/predict", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_predict_invalid_missing_fields(client: AsyncClient) -> None:
    """POST /predict with missing required fields should return 422."""
    response = await client.post("/predict", json={"features": {"x": 1.0}})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_predict_invalid_port_range(client: AsyncClient) -> None:
    """POST /predict with out-of-range port should return 422."""
    payload = {**VALID_PAYLOAD, "src_port": 99999}
    response = await client.post("/predict", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_predict_invalid_nan_feature(client: AsyncClient) -> None:
    """POST /predict with NaN feature value should return 422."""
    payload = {**VALID_PAYLOAD, "features": {"bad_feature": float("nan")}}
    response = await client.post("/predict", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_predict_invalid_no_body(client: AsyncClient) -> None:
    """POST /predict with no JSON body should return 422."""
    response = await client.post("/predict")
    assert response.status_code == 422
