"""Tests for GET /models endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_models_returns_200(client: AsyncClient) -> None:
    """GET /models should return 200."""
    response = await client.get("/models")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_models_returns_list(client: AsyncClient) -> None:
    """GET /models should return items list and total count."""
    response = await client.get("/models")
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)


@pytest.mark.asyncio
async def test_models_mock_data_present(client: AsyncClient) -> None:
    """In Phase 1, mock model data should be returned when DB is empty."""
    response = await client.get("/models")
    data = response.json()

    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_models_item_shape(client: AsyncClient) -> None:
    """Each model version should have the expected fields."""
    response = await client.get("/models")
    data = response.json()

    for item in data["items"]:
        assert "id" in item
        assert "name" in item
        assert "version" in item
        assert "stage" in item
        assert "framework" in item
        assert "created_at" in item


@pytest.mark.asyncio
async def test_models_stage_values(client: AsyncClient) -> None:
    """Model stage should be one of the expected values."""
    valid_stages = {"None", "Staging", "Production", "Archived"}
    response = await client.get("/models")
    data = response.json()

    for item in data["items"]:
        assert item["stage"] in valid_stages


@pytest.mark.asyncio
async def test_models_framework_values(client: AsyncClient) -> None:
    """Model framework should be one of the supported values."""
    valid_frameworks = {"lightgbm", "xgboost"}
    response = await client.get("/models")
    data = response.json()

    for item in data["items"]:
        assert item["framework"] in valid_frameworks
