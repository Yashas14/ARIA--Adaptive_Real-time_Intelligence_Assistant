"""
Message Models — Pydantic models for the JSON-over-WebSocket protocol.

Defines every structured message exchanged between clients and the server,
plus supporting data-transfer objects used across modules.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enumerations ─────────────────────────────────────────────────────────────

class MessageType(str, Enum):
    """Client → Server message types."""

    FILE_REQUEST = "FILE_REQUEST"
    AI_QUERY = "AI_QUERY"
    FILE_SUMMARIZE = "FILE_SUMMARIZE"
    FILE_SEARCH = "FILE_SEARCH"
    AUTH_LOGIN = "AUTH_LOGIN"


class ResponseType(str, Enum):
    """Server → Client response types."""

    CHUNK = "CHUNK"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"
    AUTH_SUCCESS = "AUTH_SUCCESS"
    AUTH_FAILURE = "AUTH_FAILURE"


# ── Wire Messages ────────────────────────────────────────────────────────────

class ClientMessage(BaseModel):
    """Incoming message from a WebSocket client."""

    type: MessageType
    payload: str
    token: Optional[str] = None
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class ServerMessage(BaseModel):
    """Outgoing message to a WebSocket client."""

    type: ResponseType
    request_id: str
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Data-Transfer Objects ────────────────────────────────────────────────────

class FileMeta(BaseModel):
    """Metadata returned alongside file content."""

    filename: str
    size_bytes: int
    line_count: int
    last_modified: datetime
    mime_type: str = "text/plain"


class SummarizationResult(BaseModel):
    """Structured AI-generated file summary."""

    executive_summary: str
    key_topics: list[str]
    sentiment: str  # positive | neutral | negative
    follow_up_questions: list[str]


class UserCredentials(BaseModel):
    """Login payload sent inside ``ClientMessage.payload`` (JSON-encoded)."""

    username: str
    password: str
