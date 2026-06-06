"""
Tests for the Pydantic message models.
"""

from __future__ import annotations

import json
import uuid

from models import (
    ClientMessage,
    FileMeta,
    MessageType,
    ResponseType,
    ServerMessage,
    SummarizationResult,
    UserCredentials,
)


# ── ClientMessage tests ──────────────────────────────────────────────────────


class TestClientMessage:
    """Verify ClientMessage parsing and serialisation."""

    def test_minimal_message(self) -> None:
        msg = ClientMessage(type=MessageType.AI_QUERY, payload="hello")
        assert msg.type == MessageType.AI_QUERY
        assert msg.payload == "hello"
        assert msg.token is None
        assert msg.request_id  # auto-generated UUID

    def test_full_message(self) -> None:
        rid = str(uuid.uuid4())
        msg = ClientMessage(
            type=MessageType.FILE_REQUEST,
            payload="test.txt",
            token="jwt-token",
            request_id=rid,
        )
        assert msg.request_id == rid
        assert msg.token == "jwt-token"

    def test_json_roundtrip(self) -> None:
        msg = ClientMessage(type=MessageType.FILE_SEARCH, payload="invoices")
        raw = msg.model_dump_json()
        parsed = ClientMessage.model_validate_json(raw)
        assert parsed.type == msg.type
        assert parsed.payload == msg.payload
        assert parsed.request_id == msg.request_id

    def test_all_message_types_valid(self) -> None:
        for mt in MessageType:
            msg = ClientMessage(type=mt, payload="test")
            assert msg.type == mt

    def test_invalid_type_raises(self) -> None:
        try:
            ClientMessage.model_validate({"type": "INVALID", "payload": "x"})
            assert False, "Should have raised"
        except Exception:
            pass


# ── ServerMessage tests ──────────────────────────────────────────────────────


class TestServerMessage:
    """Verify ServerMessage parsing and serialisation."""

    def test_basic_message(self) -> None:
        msg = ServerMessage(
            type=ResponseType.COMPLETE,
            request_id="r1",
            content="data",
        )
        assert msg.type == ResponseType.COMPLETE
        assert msg.metadata == {}

    def test_with_metadata(self) -> None:
        msg = ServerMessage(
            type=ResponseType.CHUNK,
            request_id="r2",
            content="token",
            metadata={"kind": "ai_response", "tokens": 42},
        )
        assert msg.metadata["tokens"] == 42

    def test_json_roundtrip(self) -> None:
        msg = ServerMessage(
            type=ResponseType.ERROR,
            request_id="r3",
            content="something went wrong",
            metadata={"code": 500},
        )
        raw = msg.model_dump_json()
        parsed = ServerMessage.model_validate_json(raw)
        assert parsed.type == ResponseType.ERROR
        assert parsed.content == "something went wrong"
        assert parsed.metadata["code"] == 500

    def test_all_response_types(self) -> None:
        for rt in ResponseType:
            msg = ServerMessage(type=rt, request_id="x")
            assert msg.type == rt


# ── FileMeta tests ───────────────────────────────────────────────────────────


class TestFileMeta:
    """Verify FileMeta data object."""

    def test_creation(self) -> None:
        from datetime import datetime, timezone

        meta = FileMeta(
            filename="test.csv",
            size_bytes=1024,
            line_count=50,
            last_modified=datetime.now(timezone.utc),
            mime_type="text/csv",
        )
        assert meta.filename == "test.csv"
        assert meta.size_bytes == 1024

    def test_default_mime_type(self) -> None:
        from datetime import datetime, timezone

        meta = FileMeta(
            filename="unknown",
            size_bytes=0,
            line_count=0,
            last_modified=datetime.now(timezone.utc),
        )
        assert meta.mime_type == "text/plain"


# ── SummarizationResult tests ───────────────────────────────────────────────


class TestSummarizationResult:
    """Verify structured summary model."""

    def test_valid_summary(self) -> None:
        result = SummarizationResult(
            executive_summary="A short summary.",
            key_topics=["topic1", "topic2"],
            sentiment="positive",
            follow_up_questions=["q1?", "q2?", "q3?"],
        )
        assert result.sentiment == "positive"
        assert len(result.key_topics) == 2

    def test_json_parse(self) -> None:
        raw = json.dumps({
            "executive_summary": "Test",
            "key_topics": [],
            "sentiment": "neutral",
            "follow_up_questions": [],
        })
        result = SummarizationResult.model_validate_json(raw)
        assert result.executive_summary == "Test"


# ── UserCredentials tests ────────────────────────────────────────────────────


class TestUserCredentials:
    """Verify credential parsing."""

    def test_valid_credentials(self) -> None:
        creds = UserCredentials(username="admin", password="secret")
        assert creds.username == "admin"

    def test_from_json(self) -> None:
        raw = '{"username": "user", "password": "pass123"}'
        creds = UserCredentials.model_validate_json(raw)
        assert creds.username == "user"
        assert creds.password == "pass123"

    def test_missing_field_raises(self) -> None:
        try:
            UserCredentials.model_validate_json('{"username": "only"}')
            assert False, "Should have raised"
        except Exception:
            pass
