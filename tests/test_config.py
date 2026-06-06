"""
Tests for the config module.
"""

from __future__ import annotations

from pathlib import Path

from config import Settings, settings


class TestSettings:
    """Verify configuration loading and defaults."""

    def test_singleton_instance(self) -> None:
        assert settings is not None
        assert isinstance(settings, Settings)

    def test_default_host(self) -> None:
        assert isinstance(settings.HOST, str)
        assert len(settings.HOST) > 0

    def test_default_port(self) -> None:
        assert isinstance(settings.PORT, int)
        assert settings.PORT > 0

    def test_default_rate_limit(self) -> None:
        assert settings.RATE_LIMIT_REQUESTS == 10
        assert settings.RATE_LIMIT_WINDOW == 60

    def test_default_jwt_algorithm(self) -> None:
        assert settings.JWT_ALGORITHM == "HS256"

    def test_default_jwt_expiry(self) -> None:
        assert settings.JWT_EXPIRY_HOURS == 24

    def test_files_dir_exists(self) -> None:
        assert settings.FILES_DIR.exists()
        assert settings.FILES_DIR.is_dir()

    def test_log_dir_exists(self) -> None:
        assert settings.LOG_DIR.exists()
        assert settings.LOG_DIR.is_dir()

    def test_tls_disabled_by_default(self) -> None:
        assert settings.TLS_ENABLED is False

    def test_ai_model_set(self) -> None:
        assert "claude" in settings.AI_MODEL.lower()

    def test_ai_temperature_range(self) -> None:
        assert 0.0 <= settings.AI_TEMPERATURE <= 1.0

    def test_ai_max_tokens_positive(self) -> None:
        assert settings.AI_MAX_TOKENS > 0

    def test_max_clients_positive(self) -> None:
        assert settings.MAX_CLIENTS > 0
