"""
Tests for the authentication module.
"""

from __future__ import annotations

import time

from auth import (
    _hash_password,  # type: ignore[attr-access]
    authenticate_user,
    create_token,
    register_user,
    validate_token,
    _USER_REGISTRY,  # type: ignore[attr-access]
)


# ── Password hashing ────────────────────────────────────────────────────────

class TestPasswordHashing:
    """Verify SHA-256 password hashing is deterministic and correct."""

    def test_hash_deterministic(self) -> None:
        assert _hash_password("hello") == _hash_password("hello")

    def test_hash_different_inputs(self) -> None:
        assert _hash_password("abc") != _hash_password("xyz")

    def test_hash_length(self) -> None:
        assert len(_hash_password("test")) == 64  # SHA-256 hex = 64 chars


# ── User registration ───────────────────────────────────────────────────────

class TestRegistration:
    """Verify user registration logic."""

    def test_register_new_user(self) -> None:
        username = f"_test_user_{time.time_ns()}"
        assert register_user(username, "pass123") is True
        assert username in _USER_REGISTRY
        # Clean up
        _USER_REGISTRY.pop(username, None)

    def test_register_duplicate(self) -> None:
        assert register_user("admin", "anything") is False


# ── Authentication ───────────────────────────────────────────────────────────

class TestAuthentication:
    """Verify user authentication against the registry."""

    def test_correct_credentials(self) -> None:
        assert authenticate_user("admin", "admin123") is True

    def test_wrong_password(self) -> None:
        assert authenticate_user("admin", "wrong") is False

    def test_unknown_user(self) -> None:
        assert authenticate_user("nonexistent_user", "password") is False


# ── JWT tokens ───────────────────────────────────────────────────────────────

class TestJWT:
    """Verify JWT creation and validation."""

    def test_create_and_validate(self) -> None:
        token = create_token("admin")
        assert isinstance(token, str)
        assert len(token) > 10

        username = validate_token(token)
        assert username == "admin"

    def test_invalid_token(self) -> None:
        assert validate_token("this.is.invalid") is None

    def test_empty_token(self) -> None:
        assert validate_token("") is None

    def test_token_contains_username(self) -> None:
        token = create_token("demo")
        assert validate_token(token) == "demo"

    def test_validate_returns_none_for_deleted_user(self) -> None:
        username = f"_temp_{time.time_ns()}"
        register_user(username, "pass")
        token = create_token(username)
        assert validate_token(token) == username
        # Remove user
        _USER_REGISTRY.pop(username, None)
        assert validate_token(token) is None
