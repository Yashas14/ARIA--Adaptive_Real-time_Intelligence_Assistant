"""
Authentication — JWT token generation, validation, and user registry.

Uses ``python-jose`` for JWT operations and a simple in-memory user registry
that is easily swappable to a database backend.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from loguru import logger

from config import settings

# ── In-memory user registry ─────────────────────────────────────────────────
# Passwords stored as SHA-256 hex digests.  In production swap this dict for
# a proper database table (SQLAlchemy, Tortoise-ORM, etc.).
_USER_REGISTRY: dict[str, str] = {
    "admin": hashlib.sha256(b"admin123").hexdigest(),
    "user": hashlib.sha256(b"user123").hexdigest(),
    "demo": hashlib.sha256(b"demo").hexdigest(),
}


# ── Password helpers ─────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    """Return the SHA-256 hex digest of *password*."""
    return hashlib.sha256(password.encode()).hexdigest()


# ── Public API ───────────────────────────────────────────────────────────────

def register_user(username: str, password: str) -> bool:
    """Register a new user.  Returns ``False`` if *username* already exists."""
    if username in _USER_REGISTRY:
        return False
    _USER_REGISTRY[username] = _hash_password(password)
    logger.info("New user registered: {}", username)
    return True


def authenticate_user(username: str, password: str) -> bool:
    """Verify *username* / *password* against the registry."""
    stored = _USER_REGISTRY.get(username)
    if stored is None:
        return False
    return hmac.compare_digest(stored, _hash_password(password))


def create_token(username: str) -> str:
    """Create a signed JWT for *username*."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(hours=settings.JWT_EXPIRY_HOURS),
    }
    token: str = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    logger.debug("JWT issued for {}", username)
    return token


def validate_token(token: str) -> Optional[str]:
    """Validate a JWT and return the *username*, or ``None`` on failure."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        username: str | None = payload.get("sub")
        if username is None:
            return None
        # Verify the user still exists in the registry
        if username not in _USER_REGISTRY:
            return None
        return username
    except JWTError as exc:
        logger.warning("JWT validation failed: {}", exc)
        return None
