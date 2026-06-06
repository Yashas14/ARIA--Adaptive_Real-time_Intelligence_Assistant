"""
AI-Powered Async WebSocket Server
===================================
Production-quality server built on ``asyncio`` + ``websockets`` with:

* Multi-client concurrency (async connection handler per client)
* Anthropic Claude AI — intent classification, chat, summarization, search
* JWT-based authentication middleware
* Per-client sliding-window rate limiting
* TLS/SSL support (self-signed certificate auto-generation for dev)
* Structured logging via ``loguru``
"""

from __future__ import annotations

import asyncio
import json
import ssl
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

import websockets
from websockets.asyncio.server import ServerConnection as WSConn
from loguru import logger

from ai_engine import AIEngine
from auth import authenticate_user, create_token, validate_token
from config import settings
from file_manager import (
    get_file_metadata,
    get_file_names,
    list_files,
    read_file_content,
)
from models import (
    ClientMessage,
    MessageType,
    ResponseType,
    ServerMessage,
    UserCredentials,
)

# ── Logging configuration ───────────────────────────────────────────────────
logger.add(
    settings.LOG_DIR / "server_{time}.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}",
    enqueue=True,
)

# ── Global server state ─────────────────────────────────────────────────────
connected_clients: dict[str, WSConn] = {}
rate_limit_buckets: dict[str, list[float]] = defaultdict(list)
ai_engine = AIEngine()


# ── Utility helpers ──────────────────────────────────────────────────────────


def _client_id(ws: WSConn) -> str:
    """Derive a stable identifier for logging / rate-limit tracking."""
    try:
        addr = ws.remote_address
        if addr:
            return f"{addr[0]}:{addr[1]}"
    except Exception:
        pass
    return str(id(ws))


def _check_rate_limit(cid: str) -> bool:
    """Return ``True`` if the client may proceed, ``False`` if rate-limited."""
    now = time.time()
    bucket = rate_limit_buckets[cid]
    rate_limit_buckets[cid] = [t for t in bucket if now - t < settings.RATE_LIMIT_WINDOW]
    if len(rate_limit_buckets[cid]) >= settings.RATE_LIMIT_REQUESTS:
        return False
    rate_limit_buckets[cid].append(now)
    return True


# Public alias for test access
check_rate_limit = _check_rate_limit


async def _send(ws: WSConn, msg: ServerMessage) -> None:
    """Serialise and send a :class:`ServerMessage`, swallowing connection errors."""
    try:
        await ws.send(msg.model_dump_json())
    except websockets.ConnectionClosed:
        pass


async def _send_error(
    ws: WSConn,
    request_id: str,
    error: str,
    **extra_meta: Any,
) -> None:
    """Convenience wrapper: send an ERROR response."""
    await _send(
        ws,
        ServerMessage(
            type=ResponseType.ERROR,
            request_id=request_id,
            content=error,
            metadata=extra_meta,
        ),
    )


# ── Request handlers ────────────────────────────────────────────────────────


async def handle_file_request(ws: WSConn, msg: ClientMessage, username: str) -> None:
    """Serve a file or list available files."""
    filename = msg.payload.strip()

    # List files
    if not filename or filename.lower() in ("list", "ls"):
        files = await list_files()
        await _send(
            ws,
            ServerMessage(
                type=ResponseType.COMPLETE,
                request_id=msg.request_id,
                content=json.dumps(files, indent=2),
                metadata={"kind": "file_list", "count": len(files)},
            ),
        )
        return

    # Fetch metadata
    meta = await get_file_metadata(filename)
    if meta is None:
        await _send_error(ws, msg.request_id, f"File not found: {filename}")
        return

    content = await read_file_content(filename)
    if content is None:
        await _send_error(ws, msg.request_id, f"Could not read file: {filename}")
        return

    # Stream content in manageable chunks
    chunk_size = 512
    for offset in range(0, len(content), chunk_size):
        await _send(
            ws,
            ServerMessage(
                type=ResponseType.CHUNK,
                request_id=msg.request_id,
                content=content[offset : offset + chunk_size],
            ),
        )
        await asyncio.sleep(0.02)  # Allow other tasks to run

    await _send(
        ws,
        ServerMessage(
            type=ResponseType.COMPLETE,
            request_id=msg.request_id,
            content="",
            metadata=meta.model_dump(mode="json"),
        ),
    )
    logger.info("[{}] Served file: {} ({} bytes)", username, filename, meta.size_bytes)


async def handle_ai_query(ws: WSConn, msg: ClientMessage, username: str) -> None:
    """Forward an AI chat query to Claude and stream the response."""
    logger.info("[{}] AI query: {!r}", username, msg.payload[:80])
    async for token in ai_engine.chat_stream(msg.payload, user_id=username):
        await _send(
            ws,
            ServerMessage(
                type=ResponseType.CHUNK,
                request_id=msg.request_id,
                content=token,
            ),
        )
    await _send(
        ws,
        ServerMessage(
            type=ResponseType.COMPLETE,
            request_id=msg.request_id,
            content="",
            metadata={"kind": "ai_response"},
        ),
    )


async def handle_file_summarize(ws: WSConn, msg: ClientMessage, username: str) -> None:
    """Read a file and stream its AI-generated summary."""
    filename = msg.payload.strip()
    content = await read_file_content(filename)
    if content is None:
        await _send_error(ws, msg.request_id, f"File not found or unreadable: {filename}")
        return

    logger.info("[{}] Summarizing: {}", username, filename)
    async for token in ai_engine.summarize_file_stream(filename, content):
        await _send(
            ws,
            ServerMessage(
                type=ResponseType.CHUNK,
                request_id=msg.request_id,
                content=token,
            ),
        )
    await _send(
        ws,
        ServerMessage(
            type=ResponseType.COMPLETE,
            request_id=msg.request_id,
            content="",
            metadata={"kind": "file_summary", "filename": filename},
        ),
    )


async def handle_file_search(ws: WSConn, msg: ClientMessage, username: str) -> None:
    """Search for files matching a natural-language query."""
    available = await get_file_names()
    matches = await ai_engine.search_files(msg.payload, available)
    await _send(
        ws,
        ServerMessage(
            type=ResponseType.COMPLETE,
            request_id=msg.request_id,
            content=json.dumps(matches),
            metadata={
                "kind": "file_search",
                "query": msg.payload,
                "match_count": len(matches),
            },
        ),
    )
    logger.info("[{}] File search {!r} → {} results", username, msg.payload, len(matches))


# ── Authentication handler ──────────────────────────────────────────────────


async def handle_auth(ws: WSConn, msg: ClientMessage) -> Optional[str]:
    """Process an ``AUTH_LOGIN`` message; return *username* on success."""
    try:
        creds = UserCredentials.model_validate_json(msg.payload)
    except Exception:
        await _send(
            ws,
            ServerMessage(
                type=ResponseType.AUTH_FAILURE,
                request_id=msg.request_id,
                content="Invalid credentials payload.",
            ),
        )
        return None

    if not authenticate_user(creds.username, creds.password):
        await _send(
            ws,
            ServerMessage(
                type=ResponseType.AUTH_FAILURE,
                request_id=msg.request_id,
                content="Authentication failed — wrong username or password.",
            ),
        )
        logger.warning("Failed login attempt for user: {}", creds.username)
        return None

    token = create_token(creds.username)
    await _send(
        ws,
        ServerMessage(
            type=ResponseType.AUTH_SUCCESS,
            request_id=msg.request_id,
            content=token,
            metadata={"username": creds.username},
        ),
    )
    logger.info("User authenticated: {}", creds.username)
    return creds.username


# ── Dispatch table ──────────────────────────────────────────────────────────

_HANDLERS: dict[MessageType, Any] = {
    MessageType.FILE_REQUEST: handle_file_request,
    MessageType.AI_QUERY: handle_ai_query,
    MessageType.FILE_SUMMARIZE: handle_file_summarize,
    MessageType.FILE_SEARCH: handle_file_search,
}


# ── Main connection handler ─────────────────────────────────────────────────


async def connection_handler(ws: WSConn) -> None:
    """Handle the full lifecycle of a single WebSocket client."""
    cid = _client_id(ws)
    logger.info("Client connected: {}", cid)
    connected_clients[cid] = ws
    authenticated_user: Optional[str] = None

    try:
        async for raw in ws:
            # ── Parse incoming message ───────────────────────────────────
            try:
                msg = ClientMessage.model_validate_json(raw)
            except Exception as exc:
                await _send_error(ws, str(uuid.uuid4()), f"Invalid message format: {exc}")
                continue

            # ── Authentication flow ──────────────────────────────────────
            if msg.type == MessageType.AUTH_LOGIN:
                authenticated_user = await handle_auth(ws, msg)
                continue

            # Accept token on every message (allows stateless auth)
            if msg.token:
                resolved_user = validate_token(msg.token)
                if resolved_user:
                    authenticated_user = resolved_user

            if not authenticated_user:
                await _send_error(
                    ws, msg.request_id,
                    "Authentication required. Send an AUTH_LOGIN message first.",
                )
                continue

            # ── Rate limiting ────────────────────────────────────────────
            if not _check_rate_limit(cid):
                await _send_error(
                    ws, msg.request_id,
                    "Rate limit exceeded — please wait before retrying.",
                    retry_after=settings.RATE_LIMIT_WINDOW,
                )
                continue

            # ── Anomaly detection ────────────────────────────────────────
            suspicious, reason = await ai_engine.detect_anomaly(msg.payload)
            if suspicious:
                logger.warning(
                    "ANOMALY from {}/{}: {}", cid, authenticated_user, reason,
                )
                await _send_error(ws, msg.request_id, f"Request blocked: {reason}")
                continue

            # ── Smart intent reclassification ────────────────────────────
            # If the client sends AI_QUERY, let Claude decide if it's really
            # a file request, summary, or search disguised as a question.
            if msg.type == MessageType.AI_QUERY:
                detected = await ai_engine.classify_intent(msg.payload)
                if detected != MessageType.AI_QUERY:
                    logger.debug("Intent reclassified: {} → {}", msg.type, detected)
                    msg.type = detected

            # ── Dispatch to handler ──────────────────────────────────────
            handler = _HANDLERS.get(msg.type)
            if handler:
                await handler(ws, msg, authenticated_user)
            else:
                await _send_error(ws, msg.request_id, f"Unknown message type: {msg.type}")

    except websockets.ConnectionClosed:
        logger.info("Client disconnected: {}", cid)
    except Exception as exc:
        logger.error("Unhandled error for {}: {}", cid, exc)
    finally:
        connected_clients.pop(cid, None)
        rate_limit_buckets.pop(cid, None)
        logger.info(
            "Cleaned up: {} (active clients: {})", cid, len(connected_clients),
        )


# ── TLS / SSL Helpers ───────────────────────────────────────────────────────


def _build_ssl_context() -> Optional[ssl.SSLContext]:
    """Build an SSL context if TLS is enabled in settings."""
    if not settings.TLS_ENABLED:
        return None

    cert = Path(settings.TLS_CERT_FILE)
    key = Path(settings.TLS_KEY_FILE)

    if not cert.exists() or not key.exists():
        logger.warning("TLS enabled but cert/key missing — generating self-signed pair …")
        _generate_self_signed_cert(cert, key)

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(str(cert), str(key))
    logger.info("TLS enabled ✓")
    return ctx


def _generate_self_signed_cert(cert_path: Path, key_path: Path) -> None:
    """Generate a self-signed TLS certificate for local development."""
    try:
        import datetime as dt

        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(dt.datetime.now(dt.timezone.utc))
            .not_valid_after(dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=365))
            .sign(private_key, hashes.SHA256())
        )
        key_path.write_bytes(
            private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            )
        )
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        logger.info("Self-signed TLS certificate generated ✓")
    except ImportError:
        logger.error(
            "The 'cryptography' package is required for TLS cert generation. "
            "Install it with: pip install cryptography"
        )
        raise


# ── Server entry point ──────────────────────────────────────────────────────


async def main() -> None:
    """Start the WebSocket server and run until interrupted."""
    ssl_ctx = _build_ssl_context()
    scheme = "wss" if ssl_ctx else "ws"

    async with websockets.serve(
        connection_handler,
        settings.HOST,
        settings.PORT,
        ssl=ssl_ctx,
        max_size=2**22,       # 4 MiB max message
        ping_interval=30,
        ping_timeout=10,
    ):
        logger.info(
            "Server listening on {}://{}:{}  "
            "(max_clients={}, rate_limit={}/{} s, TLS={})",
            scheme,
            settings.HOST,
            settings.PORT,
            settings.MAX_CLIENTS,
            settings.RATE_LIMIT_REQUESTS,
            settings.RATE_LIMIT_WINDOW,
            "on" if ssl_ctx else "off",
        )
        logger.info(
            "AI engine: {}",
            "enabled" if ai_engine.available else "disabled (no API key)",
        )
        logger.info("Serving files from: {}", settings.FILES_DIR)

        # Run forever until cancelled
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shut down by user.")
