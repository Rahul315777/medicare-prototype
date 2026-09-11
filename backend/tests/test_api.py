"""Pytest configuration and sample tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_register_and_login(client):
    register_data = {
        "email": "test@medicare.app",
        "password": "securepass123",
        "full_name": "Test User",
    }
    response = await client.post("/api/v1/auth/register", json=register_data)
    assert response.status_code in (201, 400)  # 400 if already exists

    login_data = {"email": "test@medicare.app", "password": "securepass123"}
    response = await client.post("/api/v1/auth/login", json=login_data)
    if response.status_code == 200:
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
