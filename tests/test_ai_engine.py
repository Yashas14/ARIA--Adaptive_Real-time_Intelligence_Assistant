"""
Tests for the AI Engine module.

These tests exercise both the rule-based fallbacks (which run without an API key)
and mock the Anthropic client for AI-dependent paths.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_engine import AIEngine
from models import MessageType


# ═════════════════════════════════════════════════════════════════════════════
# Rule-based fallback tests (no API key required)
# ═════════════════════════════════════════════════════════════════════════════


class TestRuleBasedClassify:
    """Test the deterministic intent classifier."""

    @pytest.mark.parametrize(
        "message, expected",
        [
            ("summarize this document", MessageType.FILE_SUMMARIZE),
            ("give me a summary of report.txt", MessageType.FILE_SUMMARIZE),
            ("search for invoices", MessageType.FILE_SEARCH),
            ("find me a file about sales", MessageType.FILE_SEARCH),
            ("download report.txt", MessageType.FILE_REQUEST),
            ("open the log file", MessageType.FILE_REQUEST),
            ("list files", MessageType.FILE_REQUEST),
            ("what is the weather today?", MessageType.AI_QUERY),
            ("hello", MessageType.AI_QUERY),
        ],
    )
    def test_classification(self, message: str, expected: MessageType) -> None:
        assert AIEngine.rule_based_classify(message) == expected


class TestRuleBasedAnomaly:
    """Test the deterministic anomaly detector."""

    @pytest.mark.parametrize(
        "message, suspicious",
        [
            ("../../../etc/passwd", True),
            ("normal file request", False),
            ("DROP TABLE users", True),
            ("<script>alert('xss')</script>", True),
            ("hello world", False),
            ("rm -rf /", True),
        ],
    )
    def test_anomaly_detection(self, message: str, suspicious: bool) -> None:
        result, _ = AIEngine._rule_based_anomaly(message)  # type: ignore[attr-access]
        assert result is suspicious


# ═════════════════════════════════════════════════════════════════════════════
# AI Engine initialisation
# ═════════════════════════════════════════════════════════════════════════════


class TestAIEngineInit:
    """Test engine initialisation with and without an API key."""

    @patch("ai_engine.settings")
    def test_no_api_key(self, mock_settings: MagicMock) -> None:
        mock_settings.ANTHROPIC_API_KEY = ""
        mock_settings.AI_MODEL = "claude-sonnet-4-20250514"
        mock_settings.AI_TEMPERATURE = 0.7
        mock_settings.AI_MAX_TOKENS = 4096
        engine = AIEngine()
        assert engine.available is False

    @patch("ai_engine.settings")
    @patch("ai_engine.anthropic.AsyncAnthropic")
    def test_with_api_key(
        self,
        mock_client_cls: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        mock_settings.ANTHROPIC_API_KEY = "sk-test-key"
        mock_settings.AI_MODEL = "claude-sonnet-4-20250514"
        mock_settings.AI_TEMPERATURE = 0.7
        mock_settings.AI_MAX_TOKENS = 4096
        engine = AIEngine()
        assert engine.available is True


# ═════════════════════════════════════════════════════════════════════════════
# AI-powered methods (mocked Anthropic client)
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def ai_engine() -> AIEngine:
    """Return an AIEngine with a mocked Anthropic client."""
    with patch("ai_engine.settings") as mock_settings:
        mock_settings.ANTHROPIC_API_KEY = "sk-test-key"
        mock_settings.AI_MODEL = "claude-sonnet-4-20250514"
        mock_settings.AI_TEMPERATURE = 0.7
        mock_settings.AI_MAX_TOKENS = 4096
        engine = AIEngine()
    engine.client = MagicMock()  # type: ignore[assignment]
    return engine


class TestClassifyIntent:
    """Test AI-driven intent classification (mocked)."""

    @pytest.mark.asyncio
    async def test_classify_file_request(self, ai_engine: AIEngine) -> None:
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="FILE_REQUEST")]
        ai_engine.client.messages.create = AsyncMock(return_value=mock_resp)  # type: ignore[union-attr]

        result = await ai_engine.classify_intent("show me report.txt")
        assert result == MessageType.FILE_REQUEST

    @pytest.mark.asyncio
    async def test_classify_ai_query(self, ai_engine: AIEngine) -> None:
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="AI_QUERY")]
        ai_engine.client.messages.create = AsyncMock(return_value=mock_resp)  # type: ignore[union-attr]

        result = await ai_engine.classify_intent("what is Python?")
        assert result == MessageType.AI_QUERY

    @pytest.mark.asyncio
    async def test_classify_fallback_on_error(self, ai_engine: AIEngine) -> None:
        ai_engine.client.messages.create = AsyncMock(side_effect=Exception("API error"))  # type: ignore[union-attr]
        result = await ai_engine.classify_intent("summarize this file")
        assert result == MessageType.FILE_SUMMARIZE  # rule-based fallback


class TestSearchFiles:
    """Test AI-driven file search (mocked)."""

    @pytest.mark.asyncio
    async def test_search_returns_matches(self, ai_engine: AIEngine) -> None:
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text='["report.txt", "invoice.csv"]')]
        ai_engine.client.messages.create = AsyncMock(return_value=mock_resp)  # type: ignore[union-attr]

        available = ["report.txt", "invoice.csv", "readme.md"]
        matches = await ai_engine.search_files("find reports", available)
        assert "report.txt" in matches
        assert "invoice.csv" in matches

    @pytest.mark.asyncio
    async def test_search_filters_nonexistent(self, ai_engine: AIEngine) -> None:
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text='["ghost.txt"]')]
        ai_engine.client.messages.create = AsyncMock(return_value=mock_resp)  # type: ignore[union-attr]

        matches = await ai_engine.search_files("ghost", ["real.txt"])
        assert matches == []


class TestAnomalyDetection:
    """Test AI-driven anomaly detection (mocked)."""

    @pytest.mark.asyncio
    async def test_suspicious_message(self, ai_engine: AIEngine) -> None:
        mock_resp = MagicMock()
        mock_resp.content = [
            MagicMock(text='{"suspicious": true, "reason": "path traversal"}')
        ]
        ai_engine.client.messages.create = AsyncMock(return_value=mock_resp)  # type: ignore[union-attr]

        suspicious, reason = await ai_engine.detect_anomaly("../../../etc/passwd")
        assert suspicious is True
        assert "path traversal" in reason

    @pytest.mark.asyncio
    async def test_safe_message(self, ai_engine: AIEngine) -> None:
        mock_resp = MagicMock()
        mock_resp.content = [
            MagicMock(text='{"suspicious": false, "reason": ""}')
        ]
        ai_engine.client.messages.create = AsyncMock(return_value=mock_resp)  # type: ignore[union-attr]

        suspicious, _reason = await ai_engine.detect_anomaly("hello world")
        assert suspicious is False
