"""
REST API — FastAPI HTTP + WebSocket endpoints for the React frontend.

Provides:
* POST /api/auth/login — JWT authentication
* GET /api/files — list available files
* GET /api/files/{filename} — read file content
* POST /api/files/{filename}/summarize — AI file summary (streaming SSE)
* POST /api/chat — AI chat (streaming SSE)
* POST /api/search — natural-language file search
* GET /api/health — health check
* WebSocket /ws — full-duplex real-time communication
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from loguru import logger

from ai_engine import AIEngine
from auth import authenticate_user, create_token, validate_token
from config import settings
from file_manager import get_file_metadata, get_file_names, list_files, read_file_content
from models import MessageType

# ── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ARIA",
    description="Adaptive Real-time Intelligence Assistant — AI-Native Document Intelligence Platform",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_engine = AIEngine()
security = HTTPBearer()

# ── Conversation history (in-memory, per user) ───────────────────────────────

conversation_history: dict[str, list[dict[str, str]]] = {}
MAX_HISTORY = 20


def _get_history(user: str) -> list[dict[str, str]]:
    return conversation_history.setdefault(user, [])


def _add_to_history(user: str, role: str, content: str) -> None:
    history = _get_history(user)
    history.append({"role": role, "content": content})
    if len(history) > MAX_HISTORY * 2:
        conversation_history[user] = history[-MAX_HISTORY * 2:]


# ── Auth dependency ──────────────────────────────────────────────────────────


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Validate JWT and return the username."""
    username = validate_token(credentials.credentials)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return username


# ── Request / Response models ────────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


class ChatRequest(BaseModel):
    message: str


class SearchRequest(BaseModel):
    query: str


class SearchResponse(BaseModel):
    query: str
    matches: list[str]


class FileMetaResponse(BaseModel):
    filename: str
    size_bytes: int
    line_count: int
    last_modified: str
    mime_type: str


class HealthResponse(BaseModel):
    status: str
    ai_available: bool
    connected_clients: int
    files_count: int


# ── Endpoints ────────────────────────────────────────────────────────────────


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """System health check."""
    files = await get_file_names()
    return HealthResponse(
        status="healthy",
        ai_available=ai_engine.available,
        connected_clients=0,
        files_count=len(files),
    )


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """Authenticate and receive a JWT."""
    if not authenticate_user(request.username, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_token(request.username)
    return LoginResponse(token=token, username=request.username)


@app.get("/api/files")
async def list_all_files(user: str = Depends(get_current_user)) -> list[dict[str, str]]:
    """List all available files."""
    return await list_files()


@app.get("/api/files/{filename}")
async def get_file(filename: str, user: str = Depends(get_current_user)) -> dict[str, Any]:
    """Read file content and metadata."""
    meta = await get_file_metadata(filename)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    content = await read_file_content(filename)
    if content is None:
        raise HTTPException(status_code=500, detail=f"Could not read file: {filename}")

    return {
        "content": content,
        "metadata": meta.model_dump(mode="json"),
    }


@app.post("/api/files/{filename}/summarize")
async def summarize_file(
    filename: str, user: str = Depends(get_current_user)
) -> EventSourceResponse:
    """Stream an AI-generated file summary via SSE."""
    content = await read_file_content(filename)
    if content is None:
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    async def event_generator():
        async for token in ai_engine.summarize_file_stream(filename, content):
            yield {"event": "token", "data": token}
        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())


@app.post("/api/chat")
async def chat(request: ChatRequest, user: str = Depends(get_current_user)) -> EventSourceResponse:
    """Stream an AI chat response via SSE with conversation history."""
    _add_to_history(user, "user", request.message)

    async def event_generator():
        full_response = []
        async for token in ai_engine.chat_stream(request.message, user_id=user):
            full_response.append(token)
            yield {"event": "token", "data": token}
        _add_to_history(user, "assistant", "".join(full_response))
        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())


@app.post("/api/search", response_model=SearchResponse)
async def search_files(
    request: SearchRequest, user: str = Depends(get_current_user)
) -> SearchResponse:
    """Natural language file search."""
    available = await get_file_names()
    matches = await ai_engine.search_files(request.query, available)
    return SearchResponse(query=request.query, matches=matches)


@app.get("/api/history")
async def get_chat_history(user: str = Depends(get_current_user)) -> list[dict[str, str]]:
    """Return the conversation history for the current user."""
    return _get_history(user)


@app.delete("/api/history")
async def clear_chat_history(user: str = Depends(get_current_user)) -> dict[str, str]:
    """Clear conversation history for the current user."""
    conversation_history.pop(user, None)
    return {"status": "cleared"}


# ── WebSocket endpoint (for real-time features) ─────────────────────────────


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """WebSocket endpoint for real-time bidirectional communication."""
    await ws.accept()
    authenticated_user: str | None = None

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)

            # Auth
            if data.get("type") == "AUTH_LOGIN":
                payload = json.loads(data.get("payload", "{}"))
                username = payload.get("username", "")
                password = payload.get("password", "")
                if authenticate_user(username, password):
                    token = create_token(username)
                    authenticated_user = username
                    await ws.send_json({
                        "type": "AUTH_SUCCESS",
                        "content": token,
                        "metadata": {"username": username},
                    })
                else:
                    await ws.send_json({
                        "type": "AUTH_FAILURE",
                        "content": "Invalid credentials",
                    })
                continue

            # Require auth
            if not authenticated_user:
                token = data.get("token")
                if token:
                    authenticated_user = validate_token(token)
                if not authenticated_user:
                    await ws.send_json({
                        "type": "ERROR",
                        "content": "Authentication required",
                    })
                    continue

            msg_type = data.get("type", "AI_QUERY")
            payload = data.get("payload", "")
            request_id = data.get("request_id", str(uuid.uuid4()))

            if msg_type == "AI_QUERY":
                async for token in ai_engine.chat_stream(payload, user_id=authenticated_user):
                    await ws.send_json({
                        "type": "CHUNK",
                        "request_id": request_id,
                        "content": token,
                    })
                await ws.send_json({
                    "type": "COMPLETE",
                    "request_id": request_id,
                    "content": "",
                })

            elif msg_type == "FILE_REQUEST":
                content = await read_file_content(payload)
                if content:
                    await ws.send_json({
                        "type": "COMPLETE",
                        "request_id": request_id,
                        "content": content,
                    })
                else:
                    await ws.send_json({
                        "type": "ERROR",
                        "request_id": request_id,
                        "content": f"File not found: {payload}",
                    })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as exc:
        logger.error("WebSocket error: {}", exc)
