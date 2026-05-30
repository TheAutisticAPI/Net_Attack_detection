"""Tests for GET /alerts and GET /alerts/{id} endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────

PREDICT_PAYLOAD = {
    "src_ip": "192.168.1.100",
    "dst_ip": "10.0.0.1",
    "src_port": 54321,
    "dst_port": 80,
    "protocol": 6,
    "features": {
        "flow_duration": 1.23,
        "total_fwd_packets": 10.0,
        "total_bwd_packets": 8.0,
    },
}


async def _create_alert(client: AsyncClient) -> dict:
    """Create an alert via POST /predict and return the response data."""
    resp = await client.post("/predict", json=PREDICT_PAYLOAD)
    assert resp.status_code == 200
    return resp.json()


# ── GET /alerts ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_alerts_empty_list(client: AsyncClient) -> None:
    """GET /alerts on a fresh DB should return an empty paginated list."""
    response = await client.get("/alerts")
    assert response.status_code == 200

    data = response.json()
    assert data["items"] == []
    assert data["pagination"]["total_items"] == 0
    assert data["pagination"]["page"] == 1


@pytest.mark.asyncio
async def test_alerts_returns_created_alerts(client: AsyncClient) -> None:
    """After creating predictions, GET /alerts should list them."""
    # Create two alerts
    await _create_alert(client)
    await _create_alert(client)

    response = await client.get("/alerts")
    assert response.status_code == 200

    data = response.json()
    assert data["pagination"]["total_items"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_alerts_pagination(client: AsyncClient) -> None:
    """Pagination params should limit and offset results."""
    for _ in range(5):
        await _create_alert(client)

    response = await client.get("/alerts", params={"page": 1, "page_size": 2})
    data = response.json()

    assert len(data["items"]) == 2
    assert data["pagination"]["total_items"] == 5
    assert data["pagination"]["total_pages"] == 3
    assert data["pagination"]["page"] == 1


@pytest.mark.asyncio
async def test_alerts_pagination_page_2(client: AsyncClient) -> None:
    """Second page should contain remaining items."""
    for _ in range(3):
        await _create_alert(client)

    response = await client.get("/alerts", params={"page": 2, "page_size": 2})
    data = response.json()

    assert len(data["items"]) == 1
    assert data["pagination"]["page"] == 2


@pytest.mark.asyncio
async def test_alerts_filter_by_label(client: AsyncClient) -> None:
    """Filtering by label should only return matching alerts."""
    pred = await _create_alert(client)
    label = pred["label"]

    response = await client.get("/alerts", params={"label": label})
    data = response.json()

    assert data["pagination"]["total_items"] >= 1
    for item in data["items"]:
        assert item["label"] == label


@pytest.mark.asyncio
async def test_alerts_filter_by_confidence_range(client: AsyncClient) -> None:
    """Filtering by confidence range should work."""
    await _create_alert(client)

    response = await client.get(
        "/alerts", params={"min_confidence": 0.0, "max_confidence": 1.0}
    )
    data = response.json()
    assert data["pagination"]["total_items"] >= 1


@pytest.mark.asyncio
async def test_alerts_sort_by_confidence(client: AsyncClient) -> None:
    """Sorting by confidence should order results correctly."""
    for _ in range(3):
        await _create_alert(client)

    response = await client.get(
        "/alerts", params={"sort_by": "confidence", "sort_order": "desc"}
    )
    data = response.json()
    confidences = [item["confidence"] for item in data["items"]]
    assert confidences == sorted(confidences, reverse=True)


# ── GET /alerts/{id} ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_alert_detail_returns_alert(client: AsyncClient) -> None:
    """GET /alerts/{id} should return the full alert."""
    pred = await _create_alert(client)
    alert_id = pred["alert_id"]

    response = await client.get(f"/alerts/{alert_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == alert_id
    assert "label" in data
    assert "confidence" in data
    assert "severity" in data
    assert "src_ip" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_alert_detail_not_found(client: AsyncClient) -> None:
    """GET /alerts/{id} with a non-existent UUID should return 404."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/alerts/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_alert_detail_invalid_uuid(client: AsyncClient) -> None:
    """GET /alerts/{id} with an invalid UUID should return 422."""
    response = await client.get("/alerts/not-a-uuid")
    assert response.status_code == 422
