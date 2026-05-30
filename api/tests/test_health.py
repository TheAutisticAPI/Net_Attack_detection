"""Tests for GET /health endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    """GET /health should return 200 with status, database, version, uptime."""
    response = await client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["database"] in ("connected", "disconnected")
    assert "api_version" in data
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["uptime_seconds"] >= 0


@pytest.mark.asyncio
async def test_health_includes_version(client: AsyncClient) -> None:
    """The api_version field should match the configured version."""
    response = await client.get("/health")
    data = response.json()
    assert data["api_version"] == "0.1.0"


@pytest.mark.asyncio
async def test_health_db_connected(client: AsyncClient) -> None:
    """Database field should report 'connected' with in-memory SQLite."""
    response = await client.get("/health")
    data = response.json()
    assert data["database"] == "connected"
