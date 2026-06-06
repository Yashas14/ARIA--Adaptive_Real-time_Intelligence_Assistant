"""
Tests for the WebSocket server.

Uses mocked WebSocket connections and AI engine to validate the server's
message routing, authentication, and rate-limiting logic.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from models import (
    ClientMessage,
    MessageType,
    ResponseType,
    ServerMessage,
)


# ═════════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════════


def _make_ws_mock() -> MagicMock:
    """Create a mock WebSocket with ``send`` / ``remote_address``."""
    ws = AsyncMock()
    ws.remote_address = ("127.0.0.1", 55555)
    ws.send = AsyncMock()
    return ws


def _last_sent(ws_mock: MagicMock) -> ServerMessage:
    """Parse the most recent message sent through the mock WebSocket."""
    raw = ws_mock.send.call_args_list[-1][0][0]
    return ServerMessage.model_validate_json(raw)


# ═════════════════════════════════════════════════════════════════════════════
# Authentication handler
# ═════════════════════════════════════════════════════════════════════════════


class TestHandleAuth:
    """Test the authentication handler in isolation."""

    @pytest.mark.asyncio
    async def test_valid_login(self) -> None:
        from server import handle_auth

        ws = _make_ws_mock()
        msg = ClientMessage(
            type=MessageType.AUTH_LOGIN,
            payload=json.dumps({"username": "admin", "password": "admin123"}),
            request_id=str(uuid.uuid4()),
        )
        result = await handle_auth(ws, msg)
        assert result == "admin"
        resp = _last_sent(ws)
        assert resp.type == ResponseType.AUTH_SUCCESS
        assert resp.metadata.get("username") == "admin"

    @pytest.mark.asyncio
    async def test_invalid_password(self) -> None:
        from server import handle_auth

        ws = _make_ws_mock()
        msg = ClientMessage(
            type=MessageType.AUTH_LOGIN,
            payload=json.dumps({"username": "admin", "password": "wrong"}),
            request_id=str(uuid.uuid4()),
        )
        result = await handle_auth(ws, msg)
        assert result is None
        resp = _last_sent(ws)
        assert resp.type == ResponseType.AUTH_FAILURE

    @pytest.mark.asyncio
    async def test_malformed_payload(self) -> None:
        from server import handle_auth

        ws = _make_ws_mock()
        msg = ClientMessage(
            type=MessageType.AUTH_LOGIN,
            payload="not-json",
            request_id=str(uuid.uuid4()),
        )
        result = await handle_auth(ws, msg)
        assert result is None
        resp = _last_sent(ws)
        assert resp.type == ResponseType.AUTH_FAILURE


# ═════════════════════════════════════════════════════════════════════════════
# Rate limiting
# ═════════════════════════════════════════════════════════════════════════════


class TestRateLimiting:
    """Verify the sliding-window rate limiter."""

    def test_allows_within_limit(self) -> None:
        from server import check_rate_limit, rate_limit_buckets

        cid = "_test_rate_limit_ok"
        rate_limit_buckets.pop(cid, None)
        for _ in range(10):
            assert check_rate_limit(cid) is True
        # Clean up
        rate_limit_buckets.pop(cid, None)

    def test_blocks_over_limit(self) -> None:
        from server import check_rate_limit, rate_limit_buckets

        cid = "_test_rate_limit_block"
        rate_limit_buckets.pop(cid, None)
        for _ in range(10):
            check_rate_limit(cid)
        assert check_rate_limit(cid) is False
        rate_limit_buckets.pop(cid, None)


# ═════════════════════════════════════════════════════════════════════════════
# File request handler
# ═════════════════════════════════════════════════════════════════════════════


class TestHandleFileRequest:
    """Test the file-request handler."""

    @pytest.mark.asyncio
    async def test_list_files(self) -> None:
        from server import handle_file_request

        ws = _make_ws_mock()
        msg = ClientMessage(
            type=MessageType.FILE_REQUEST,
            payload="list",
            request_id=str(uuid.uuid4()),
        )
        await handle_file_request(ws, msg, "testuser")
        resp = _last_sent(ws)
        assert resp.type == ResponseType.COMPLETE
        assert resp.metadata.get("kind") == "file_list"

    @pytest.mark.asyncio
    async def test_missing_file(self) -> None:
        from server import handle_file_request

        ws = _make_ws_mock()
        msg = ClientMessage(
            type=MessageType.FILE_REQUEST,
            payload="nonexistent_file_12345.txt",
            request_id=str(uuid.uuid4()),
        )
        await handle_file_request(ws, msg, "testuser")
        resp = _last_sent(ws)
        assert resp.type == ResponseType.ERROR
        assert "not found" in resp.content.lower()


# ═════════════════════════════════════════════════════════════════════════════
# Message parsing
# ═════════════════════════════════════════════════════════════════════════════


class TestMessageParsing:
    """Ensure the Pydantic models correctly parse wire messages."""

    def test_valid_client_message(self) -> None:
        raw = json.dumps(
            {
                "type": "AI_QUERY",
                "payload": "hello",
                "token": "abc",
                "request_id": "123",
            }
        )
        msg = ClientMessage.model_validate_json(raw)
        assert msg.type == MessageType.AI_QUERY
        assert msg.payload == "hello"
        assert msg.token == "abc"

    def test_server_message_roundtrip(self) -> None:
        msg = ServerMessage(
            type=ResponseType.CHUNK,
            request_id="r1",
            content="data",
            metadata={"key": "value"},
        )
        raw = msg.model_dump_json()
        parsed = ServerMessage.model_validate_json(raw)
        assert parsed.type == ResponseType.CHUNK
        assert parsed.content == "data"
        assert parsed.metadata["key"] == "value"
