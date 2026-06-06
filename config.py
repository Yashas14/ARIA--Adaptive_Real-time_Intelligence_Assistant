"""
Configuration — Pydantic Settings for the AI-Powered Client-Server System.

Loads settings from environment variables and an optional ``.env`` file.
All configuration is centralised here for easy management and validation.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR: Path = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Application-wide settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=str(_BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Network ──────────────────────────────────────────────────────────────
    HOST: str = Field(default="localhost", description="Server bind address")
    PORT: int = Field(default=9000, description="Server bind port")
    MAX_CLIENTS: int = Field(default=50, description="Maximum concurrent WebSocket clients")

    # ── Anthropic / Claude AI ────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = Field(default="", description="Anthropic API key for Claude")
    AI_MODEL: str = Field(
        default="claude-sonnet-4-20250514",
        description="Claude model identifier",
    )
    AI_TEMPERATURE: float = Field(default=0.7, ge=0.0, le=1.0, description="Sampling temperature")
    AI_MAX_TOKENS: int = Field(default=4096, gt=0, description="Max output tokens per AI response")

    # ── JWT Authentication ───────────────────────────────────────────────────
    JWT_SECRET: str = Field(
        default="change-me-in-production-use-a-strong-random-secret",
        description="HMAC signing secret for JWT tokens",
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    JWT_EXPIRY_HOURS: int = Field(default=24, gt=0, description="Token lifetime in hours")

    # ── Rate Limiting ────────────────────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = Field(default=10, description="Max requests per sliding window")
    RATE_LIMIT_WINDOW: int = Field(default=60, description="Sliding-window size in seconds")

    # ── Paths ────────────────────────────────────────────────────────────────
    FILES_DIR: Path = Field(default=_BASE_DIR / "files", description="Directory served to clients")
    LOG_DIR: Path = Field(default=_BASE_DIR / "logs", description="Log output directory")

    # ── TLS / SSL ────────────────────────────────────────────────────────────
    TLS_ENABLED: bool = Field(default=False, description="Enable TLS for WebSocket (wss://)")
    TLS_CERT_FILE: Path = Field(default=_BASE_DIR / "cert.pem", description="Path to TLS certificate")
    TLS_KEY_FILE: Path = Field(default=_BASE_DIR / "key.pem", description="Path to TLS private key")


# ── Singleton used throughout the application ────────────────────────────────
settings = Settings()

# Ensure required directories exist at import time
settings.FILES_DIR.mkdir(parents=True, exist_ok=True)
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
