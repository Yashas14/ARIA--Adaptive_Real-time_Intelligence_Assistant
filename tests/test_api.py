"""
Tests for the FastAPI REST API module.

Uses httpx async test client against the FastAPI app.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api import app


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
async def client():
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Authenticate and return headers with JWT token."""
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


# ── Health endpoint ──────────────────────────────────────────────────────────


class TestHealth:
    """Test the health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client: AsyncClient) -> None:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "ai_available" in data
        assert "files_count" in data


# ── Authentication ───────────────────────────────────────────────────────────


class TestAuth:
    """Test authentication endpoints."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["username"] == "admin"

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrongpass"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unknown_user(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/auth/login",
            json={"username": "nobody", "password": "pass"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, client: AsyncClient) -> None:
        resp = await client.get("/api/files")
        assert resp.status_code in (401, 403)


# ── Files endpoints ──────────────────────────────────────────────────────────


class TestFiles:
    """Test file-related endpoints."""

    @pytest.mark.asyncio
    async def test_list_files(self, client: AsyncClient, auth_headers: dict) -> None:
        resp = await client.get("/api/files", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_existing_file(self, client: AsyncClient, auth_headers: dict) -> None:
        # First get the file list
        list_resp = await client.get("/api/files", headers=auth_headers)
        files = list_resp.json()
        if files:
            filename = files[0]["name"]
            resp = await client.get(f"/api/files/{filename}", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert "content" in data
            assert "metadata" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_file(self, client: AsyncClient, auth_headers: dict) -> None:
        resp = await client.get("/api/files/ghost_file_xyz.txt", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, client: AsyncClient, auth_headers: dict) -> None:
        resp = await client.get("/api/files/..%2F..%2Fetc%2Fpasswd", headers=auth_headers)
        assert resp.status_code == 404


# ── Search endpoint ──────────────────────────────────────────────────────────


class TestSearch:
    """Test the file search endpoint."""

    @pytest.mark.asyncio
    async def test_search_returns_structure(self, client: AsyncClient, auth_headers: dict) -> None:
        resp = await client.post(
            "/api/search",
            headers=auth_headers,
            json={"query": "employee"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "query" in data
        assert "matches" in data
        assert isinstance(data["matches"], list)


# ── Chat history ─────────────────────────────────────────────────────────────


class TestChatHistory:
    """Test conversation history endpoints."""

    @pytest.mark.asyncio
    async def test_get_empty_history(self, client: AsyncClient, auth_headers: dict) -> None:
        # Clear first
        await client.delete("/api/history", headers=auth_headers)
        resp = await client.get("/api/history", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_clear_history(self, client: AsyncClient, auth_headers: dict) -> None:
        resp = await client.delete("/api/history", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "cleared"
