<div align="center">

# ARIA
### Adaptive Real-time Intelligence Assistant

> *Your documents, understood — not just served*

**ARIA is an AI-native document intelligence platform — it understands what you want, streams responses in real-time, and secures every request through multi-layer AI-augmented protection.**

---

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)
![Claude AI](https://img.shields.io/badge/Claude_AI-Sonnet_4-FF6F00?style=flat-square&logo=anthropic&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat-square&logo=typescript&logoColor=white)
![WebSocket](https://img.shields.io/badge/WebSocket-Async-4DB33D?style=flat-square)
![Tests](https://img.shields.io/badge/Tests-107_Passing-brightgreen?style=flat-square)
![License](https://img.shields.io/badge/License-Educational-blueviolet?style=flat-square)

</div>

---

## What is ARIA?

ARIA reimagines what a file server can be. Instead of navigating folders, users speak naturally — *"find me files about invoices"* or *"summarize the employee data"* — and ARIA's AI engine classifies the intent, executes the right action, and streams the result in real-time.

Built on FastAPI, asyncio WebSockets, and Anthropic's Claude Sonnet, it delivers document intelligence through a polished React SPA and a Rich terminal client from the same backend. Every interaction passes through seven security layers including AI-powered semantic threat detection, JWT authentication, and sliding-window rate limiting.

Originally a single-client Java TCP project — completely rebuilt as a production-grade, multi-client, AI-integrated platform.

**ARIA** stands for **Adaptive Real-time Intelligence Assistant** — and every word earns its place:

| Letter | Meaning | How it manifests |
|--------|---------|-----------------|
| **A** — Adaptive | Changes behavior based on your intent | Claude reclassifies `AI_QUERY → FILE_REQUEST` on the fly |
| **R** — Real-time | Streams responses as they generate | Token-by-token via WebSocket chunks and SSE events |
| **I** — Intelligence | AI reasoning at every layer | 5 AI subsystems: classify, chat, summarize, search, detect threats |
| **A** — Assistant | Helps you find, understand, and work with documents | Natural language replaces all navigation |

---

## The Core Insight

Most file servers just store and retrieve. ARIA **understands**.

```
You type:  "show me the employee data"
  ↓
ARIA:       Detects intent → FILE_REQUEST
            Finds employees.csv
            Streams content in 512-byte chunks
            Returns metadata (size, lines, MIME type)

You type:  "what does this file tell us about the team?"
  ↓
ARIA:       Detects intent → FILE_SUMMARIZE
            Reads the file
            Asks Claude: executive summary + key topics + sentiment + questions
            Streams the structured JSON response token-by-token

You type:  "find something about invoices"
  ↓
ARIA:       Detects intent → FILE_SEARCH
            Claude fuzzy-matches query against all filenames
            Returns ranked matches
```

No commands. No navigation. Just language.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ARIA System                                  │
│                                                                       │
│  ┌─────────────────────┐         ┌──────────────────────────────┐   │
│  │   React Frontend     │         │     Terminal Client           │   │
│  │  (Vite + TypeScript) │         │  (Rich CLI — client.py)      │   │
│  │                       │         │                               │   │
│  │  • Login Page         │         │  • /file /ask /summarize      │   │
│  │  • AI Chat (SSE)      │         │  • /search /status /help      │   │
│  │  • File Browser       │         │  • Streaming display          │   │
│  │  • Status Dashboard   │         │  • Exponential reconnect      │   │
│  └──────────┬────────────┘         └───────────────┬──────────────┘   │
│             │ HTTP + SSE                            │ WebSocket JSON    │
│             ▼                                       ▼                   │
│  ┌────────────────────┐          ┌──────────────────────────────────┐  │
│  │   api.py           │          │   server.py                       │  │
│  │   FastAPI REST API │          │   Async WebSocket Server          │  │
│  │                    │          │                                   │  │
│  │  JWT Auth Dep.     │          │  JWT Validation                  │  │
│  │  CORS Middleware   │          │  Rate Limiter (sliding window)   │  │
│  │  SSE Streaming     │          │  Anomaly Detection               │  │
│  │  WebSocket /ws     │          │  Intent Router                   │  │
│  └──────────┬─────────┘          └──────────────────┬───────────────┘  │
│             └──────────────────┬─────────────────────┘                  │
│                                ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        Core Modules                               │   │
│  │                                                                   │   │
│  │   ai_engine.py          auth.py           file_manager.py        │   │
│  │   ─────────────         ────────          ────────────────       │   │
│  │   • Intent Classify     • SHA-256 hash    • Async file I/O       │   │
│  │   • Streaming Chat      • HMAC compare    • Path-traversal       │   │
│  │   • Summarization       • JWT sign/verify   protection           │   │
│  │   • Semantic Search     • User registry   • CSV/JSON/PDF         │   │
│  │   • Threat Detection                        format dispatch      │   │
│  │                                                                   │   │
│  │   config.py                     models.py                        │   │
│  │   ─────────                     ─────────                        │   │
│  │   • Pydantic Settings           • ClientMessage                  │   │
│  │   • .env loading                • ServerMessage                  │   │
│  │   • All 16 settings             • FileMeta / SummarizationResult │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Storage & Logs                                                   │   │
│  │  files/  ──  employees.csv · project_info.json · sample.txt     │   │
│  │  logs/   ──  Rotating structured logs (10MB, 7-day retention)   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Five AI Subsystems

ARIA embeds Claude at five distinct points in the pipeline — not as a chatbot bolted on top, but as the intelligence layer woven through every operation.

### 1. Intent Classifier
Every message — regardless of whether the user typed a slash command or free text — is semantically classified into exactly one intent:

```python
# Claude receives a strict system prompt and responds with ONE word
"FILE_REQUEST"    →  user wants to read, view, open, or list a file
"FILE_SUMMARIZE"  →  user wants a summary or analysis of a file
"FILE_SEARCH"     →  user wants to find a file by description or topic
"AI_QUERY"        →  user wants a general conversation or answer
```

The result: ARIA automatically reclassifies `AI_QUERY → FILE_REQUEST` when Claude detects you're asking for a file. You never need to know which command to type.

**Fallback (no API key):** Keyword matching across 12 trigger words per category.

### 2. Streaming Chat
Uses `client.messages.stream()` — an async generator that yields tokens as Claude produces them. Each token is forwarded immediately as a `CHUNK` message or SSE event, giving users live, character-by-character responses.

```
Claude generates: "Python is a..."
                        ↓
ARIA yields: "Python" → " is" → " a" → "..."
                        ↓
Client displays each token as it arrives
```

**Fallback:** Returns a single message: *"AI features are disabled — set ANTHROPIC_API_KEY."*

### 3. Document Summarizer
Sends file content (truncated to 12,000 chars to stay within context limits) with a structured output prompt. Claude returns **strict JSON** with four fields:

```json
{
  "executive_summary": "3-sentence overview",
  "key_topics": ["topic 1", "topic 2", "topic 3"],
  "sentiment": "positive | neutral | negative",
  "follow_up_questions": ["Q1?", "Q2?", "Q3?"]
}
```

The React frontend parses this and renders a structured summary panel with colour-coded sentiment and topic badges.

### 4. Semantic File Search
Claude fuzzy-matches a natural language query against the full list of available filenames. Returns only filenames that actually exist — no hallucinations.

```
Query: "employee data"
Files: [employees.csv, sample.txt, project_info.json, welcome.txt]
Result: ["employees.csv"]
```

**Fallback:** Simple `query.lower() in filename.lower()` substring matching.

### 5. AI-Augmented Threat Detection
Every message passes through this before being dispatched. Claude performs **semantic analysis** — not just pattern matching — to detect:
- Path traversal attacks (`../../../etc/passwd`)
- SQL injection (`DROP TABLE users; --`)
- Command injection (`rm -rf /`, `; wget malicious.sh`)
- Prompt injection (attempts to override system behaviour)
- Null byte attacks (`%00`)

**Fallback:** 14-pattern regex check covering the most common attack vectors.

---

## Feature Matrix

| Feature | React UI | Terminal CLI | Detail |
|---------|----------|-------------|--------|
| AI Chat | ✅ | ✅ | Real-time streaming, token-by-token |
| File Browser | ✅ | ✅ | List, read, metadata display |
| AI Summarize | ✅ | ✅ | Structured JSON: summary, topics, sentiment |
| Semantic Search | ✅ | ✅ | Natural language → fuzzy filename match |
| Intent Detection | ✅ | ✅ | Automatic reclassification, no commands needed |
| Conversation History | ✅ | ❌ | Per-user, clearable |
| System Status | ✅ | ❌ | Health check, AI status, file count |
| JWT Auth | ✅ | ✅ | Stateless tokens, 24h expiry |
| Rate Limiting | ✅ | ✅ | 10 req / 60s sliding window |
| Threat Detection | ✅ | ✅ | AI semantic + rule-based, 7 layers |
| TLS/SSL | ✅ | ✅ | Optional wss://, auto self-signed cert |
| CSV Rendering | ✅ | ✅ | Formatted column-aligned table |
| JSON Rendering | ✅ | ✅ | Pretty-printed with indentation |
| PDF Support | ✅ | ✅ | Via PyPDF2 (optional install) |

---

## Tech Stack

### Backend — Python 3.12+

| Library | Version | Role |
|---------|---------|------|
| `FastAPI` | 0.115+ | REST API framework with auto-docs and dependency injection |
| `uvicorn` | 0.32+ | ASGI server with hot-reload for development |
| `websockets` | 14.0+ | Async-native WebSocket transport for the terminal client |
| `anthropic` | 0.42+ | Official Claude SDK — streaming via async generators |
| `sse-starlette` | 2.1+ | Server-Sent Events for React token streaming |
| `pydantic` v2 | 2.10+ | Schema validation, 5-50x faster than v1 |
| `pydantic-settings` | 2.7+ | .env loading with type coercion |
| `python-jose` | 3.3+ | JWT signing and verification (HS256) |
| `aiofiles` | 24.1+ | Non-blocking file I/O — never stalls the event loop |
| `loguru` | 0.7+ | Structured logging with rotation and retention |
| `rich` | 13.9+ | Terminal panels, tables, syntax highlighting, spinners |
| `python-dotenv` | 1.0+ | .env file parsing |
| `pytest` | 8.3+ | Test framework |
| `pytest-asyncio` | 0.24+ | Async test support |
| `httpx` | 0.27+ | Async HTTP client for FastAPI integration tests |

### Frontend — React 19 + TypeScript

| Library | Version | Role |
|---------|---------|------|
| `React` | 19 | UI framework with concurrent features |
| `TypeScript` | 5.x | Static typing — catches errors at compile time |
| `Vite` | 8.x | Build tool with instant HMR and native ESM |
| `Tailwind CSS` | 4.x | Utility-first CSS with the new Oxide engine |
| `React Router` | 7.x | Client-side routing with nested layouts |
| `Axios` | latest | HTTP client with JWT interceptors |
| `Lucide React` | latest | Tree-shakeable icon system |

---

## Project Structure

```
ARIA/
│
├── api.py                  ← FastAPI REST + SSE + WebSocket (serves React)
├── server.py               ← Standalone WebSocket server (serves terminal client)
├── client.py               ← Rich terminal client (CLI interface)
├── ai_engine.py            ← All 5 Claude AI subsystems
├── auth.py                 ← JWT lifecycle + SHA-256 user registry
├── file_manager.py         ← Async I/O with format dispatch + path safety
├── config.py               ← Pydantic settings loaded from .env
├── models.py               ← All Pydantic schemas (wire + DTOs)
├── requirements.txt        ← Python dependencies
├── pyproject.toml          ← pytest config (asyncio_mode = auto)
│
├── frontend/               ← React + TypeScript SPA
│   ├── vite.config.ts      ← Tailwind plugin + /api proxy to :8000
│   ├── package.json
│   └── src/
│       ├── main.tsx        ← Entry point
│       ├── App.tsx         ← Router: /login, /chat, /files, /status
│       ├── index.css       ← Tailwind directives + custom animations
│       ├── types.ts        ← Shared TypeScript interfaces
│       ├── lib/
│       │   └── api.ts      ← Axios client + SSE stream helpers
│       ├── contexts/
│       │   └── AuthContext.tsx   ← JWT state (localStorage + React context)
│       ├── components/
│       │   └── Layout.tsx        ← Sidebar shell (nav + user info)
│       └── pages/
│           ├── LoginPage.tsx     ← JWT auth form
│           ├── ChatPage.tsx      ← Real-time streaming AI chat
│           ├── FilesPage.tsx     ← File browser + viewer + summarizer
│           └── StatusPage.tsx    ← Health dashboard (auto-refreshes 30s)
│
├── files/                  ← Documents served by ARIA
│   ├── employees.csv
│   ├── project_info.json
│   ├── sample.txt
│   └── welcome.txt
│
├── logs/                   ← Rotating logs (auto-created, 10MB/file, 7-day)
│
└── tests/
    ├── conftest.py             ← sys.path setup
    ├── test_api.py             ← FastAPI integration tests (httpx)
    ├── test_auth.py            ← JWT, password hashing, registration
    ├── test_ai_engine.py       ← AI classification + anomaly (mocked)
    ├── test_config.py          ← Settings validation and defaults
    ├── test_file_manager.py    ← Path safety + 4 format readers
    ├── test_models.py          ← Pydantic schema roundtrips
    └── test_server.py          ← WebSocket handlers + rate limiter
```

---

## Getting Started

### Prerequisites

- **Python 3.12+** — [python.org/downloads](https://www.python.org/downloads/)
- **Node.js 18+** — [nodejs.org](https://nodejs.org/)
- **Anthropic API key** *(optional)* — [console.anthropic.com](https://console.anthropic.com/) — ARIA works without it, AI features gracefully degrade

### 1. Clone

```bash
git clone https://github.com/Yashas14/ARIA.git
cd ARIA
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate — Windows
.venv\Scripts\activate

# Activate — macOS / Linux
source .venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` as needed:

```env
# ── AI (optional — ARIA works without this) ──────────────────────────
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# ── Security ──────────────────────────────────────────────────────────
JWT_SECRET=replace-this-with-a-32-char-random-string

# ── Server ────────────────────────────────────────────────────────────
HOST=localhost
PORT=9000
MAX_CLIENTS=50

# ── AI Model ──────────────────────────────────────────────────────────
AI_MODEL=claude-sonnet-4-20250514
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=4096

# ── Rate Limiting ─────────────────────────────────────────────────────
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60

# ── TLS (optional) ────────────────────────────────────────────────────
TLS_ENABLED=false
```

> **No API key?** ARIA still runs completely. Intent classification uses keyword rules, file search uses substring matching, and anomaly detection uses pattern matching. All file operations work normally.

### 4. Start the Backend

```bash
uvicorn api:app --reload --port 8000
```

```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### 5. Start the Frontend

```bash
cd frontend
npm install    # first time only
npm run dev
```

```
VITE v8.0.14  ready in 2030 ms
  ➜  Local:   http://localhost:5173/
```

### 6. Open ARIA

Navigate to **[http://localhost:5173](http://localhost:5173)**

Log in with one of the built-in demo accounts:

| Username | Password | Access |
|----------|----------|--------|
| `admin` | `admin123` | Full |
| `user` | `user123` | Standard |
| `demo` | `demo` | Demo |

### 7. (Optional) Terminal Client

If you prefer the CLI experience:

```bash
# Terminal 1 — WebSocket server
python server.py

# Terminal 2 — Rich terminal client
python client.py
```

#### CLI Commands

```
/ask  <question>       Ask Claude a natural-language question
/file <filename>       Read and display a file
/files                 List all available files
/summarize <filename>  AI-generated document summary
/search <query>        Natural-language file search
/status                Show connection and auth status
/help                  Display command reference
/quit                  Disconnect and exit
```

> **Free text mode:** Any input without a leading `/` is automatically sent as an AI query.

---

## REST API Reference

### Authentication

```bash
# POST /api/auth/login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# → {"token": "eyJhbGciOiJIUzI1NiJ9...", "username": "admin"}
```

### File Operations

```bash
# GET /api/files — list all files
curl http://localhost:8000/api/files \
  -H "Authorization: Bearer <token>"

# GET /api/files/{name} — read file + metadata
curl http://localhost:8000/api/files/employees.csv \
  -H "Authorization: Bearer <token>"

# POST /api/files/{name}/summarize — AI summary (SSE stream)
curl -N -X POST http://localhost:8000/api/files/employees.csv/summarize \
  -H "Authorization: Bearer <token>"
```

### AI Chat

```bash
# POST /api/chat — streaming response (SSE)
curl -N -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain the key trends in the employee data"}'
```

### Search

```bash
# POST /api/search — natural language file search
curl -X POST http://localhost:8000/api/search \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "employee or HR data"}'

# → {"query": "employee or HR data", "matches": ["employees.csv"]}
```

### Conversation History

```bash
# GET /api/history — retrieve chat history
curl http://localhost:8000/api/history \
  -H "Authorization: Bearer <token>"

# DELETE /api/history — clear history
curl -X DELETE http://localhost:8000/api/history \
  -H "Authorization: Bearer <token>"
```

### Health Check

```bash
# GET /api/health — no auth required
curl http://localhost:8000/api/health

# → {"status": "healthy", "ai_available": true, "files_count": 4}
```

### Complete Endpoint Map

| Method | Endpoint | Auth | Response |
|--------|----------|------|----------|
| `GET` | `/api/health` | — | JSON |
| `POST` | `/api/auth/login` | — | JSON (JWT) |
| `GET` | `/api/files` | JWT | JSON array |
| `GET` | `/api/files/{name}` | JWT | JSON (content + metadata) |
| `POST` | `/api/files/{name}/summarize` | JWT | SSE stream |
| `POST` | `/api/chat` | JWT | SSE stream |
| `POST` | `/api/search` | JWT | JSON |
| `GET` | `/api/history` | JWT | JSON array |
| `DELETE` | `/api/history` | JWT | JSON |
| `WS` | `/ws` | Token in payload | Bidirectional JSON |

> **Auto-generated docs:** Visit [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive Swagger UI.

---

## WebSocket Protocol

For the terminal client and direct integrations, ARIA uses a JSON protocol over WebSocket.

### Client → Server

```json
{
  "type": "AUTH_LOGIN | FILE_REQUEST | AI_QUERY | FILE_SUMMARIZE | FILE_SEARCH",
  "payload": "the message, filename, or JSON-encoded credentials",
  "token": "jwt-token (after login, attach to every message)",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Server → Client

```json
{
  "type": "CHUNK | COMPLETE | ERROR | AUTH_SUCCESS | AUTH_FAILURE",
  "request_id": "same UUID as the client request",
  "content": "token fragment or full response",
  "metadata": {"kind": "ai_response", "filename": "employees.csv"}
}
```

### Streaming Pattern

```
→ CLIENT  {type: "AI_QUERY", payload: "What is async/await?", request_id: "abc"}
← SERVER  {type: "CHUNK",    content: "Async/await",          request_id: "abc"}
← SERVER  {type: "CHUNK",    content: " is a pattern",        request_id: "abc"}
← SERVER  {type: "CHUNK",    content: " for non-blocking...", request_id: "abc"}
← SERVER  {type: "COMPLETE", content: "",                     request_id: "abc", metadata: {kind: "ai_response"}}
```

### Authentication Flow

```
→ CLIENT  {type: "AUTH_LOGIN", payload: '{"username":"admin","password":"admin123"}'}
← SERVER  {type: "AUTH_SUCCESS", content: "eyJhbGc...", metadata: {"username": "admin"}}

# All subsequent messages:
→ CLIENT  {type: "FILE_REQUEST", payload: "sample.txt", token: "eyJhbGc..."}
```

---

## Security Architecture

ARIA applies **seven layers of security** to every request:

```
Incoming Request
      │
      ▼
  [1] TLS/SSL  ──────── Encrypts transport (optional wss://)
      │
      ▼
  [2] Input Validation ── Pydantic schemas reject malformed messages
      │
      ▼
  [3] JWT Authentication ─ Token signed HS256, expiry checked
      │
      ▼
  [4] Rate Limiting ────── 10 req/60s sliding window per client IP
      │
      ▼
  [5] AI Threat Detection ─ Claude semantic analysis + 14-pattern fallback
      │
      ▼
  [6] Path Traversal Guard ─ _safe_path() resolves + prefix-checks every filename
      │
      ▼
  [7] Constant-Time Compare ─ hmac.compare_digest() prevents timing attacks
      │
      ▼
   Request Dispatched
```

### Password Security

Passwords are stored as **SHA-256 hex digests** (64 characters). Comparison uses `hmac.compare_digest()` — a constant-time function that prevents timing-based attacks where an attacker could deduce the correct password character-by-character by measuring response times.

### JWT Lifecycle

```
Login  →  create_token(username)  →  JWT payload: {sub, iat, exp}
           signed with HS256 + JWT_SECRET

Request  →  validate_token(token)  →  decode + verify expiry + confirm user exists
             returns username or None
```

---

## Configuration Reference

All settings load from environment variables or `.env` file via Pydantic Settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `localhost` | Server bind address |
| `PORT` | `9000` | WebSocket server port |
| `MAX_CLIENTS` | `50` | Max simultaneous WebSocket connections |
| `ANTHROPIC_API_KEY` | *(empty)* | Enables Claude AI — system works without it |
| `AI_MODEL` | `claude-sonnet-4-20250514` | Claude model identifier |
| `AI_TEMPERATURE` | `0.7` | Creativity (0.0 = deterministic, 1.0 = creative) |
| `AI_MAX_TOKENS` | `4096` | Maximum tokens per AI response |
| `JWT_SECRET` | *(placeholder)* | ⚠️ Change in production — use 32+ random chars |
| `JWT_ALGORITHM` | `HS256` | HMAC-SHA256 signing |
| `JWT_EXPIRY_HOURS` | `24` | Token lifetime in hours |
| `RATE_LIMIT_REQUESTS` | `10` | Max requests per time window |
| `RATE_LIMIT_WINDOW` | `60` | Sliding window in seconds |
| `FILES_DIR` | `./files` | Directory ARIA serves — add files here |
| `LOG_DIR` | `./logs` | Log output (auto-created, auto-rotated) |
| `TLS_ENABLED` | `false` | Set `true` for `wss://` encryption |
| `TLS_CERT_FILE` | `./cert.pem` | TLS certificate (auto-generated if missing) |
| `TLS_KEY_FILE` | `./key.pem` | TLS private key |

---

## Testing

ARIA has **107 automated tests** across 8 modules with zero failures.

### Run Tests

```bash
# All tests
python -m pytest tests/ -v

# By module
python -m pytest tests/test_api.py -v           # REST API integration
python -m pytest tests/test_auth.py -v          # JWT + password hashing
python -m pytest tests/test_ai_engine.py -v     # AI intent + threat detection
python -m pytest tests/test_file_manager.py -v  # Path safety + file formats
python -m pytest tests/test_models.py -v        # Pydantic schema validation
python -m pytest tests/test_config.py -v        # Settings validation
python -m pytest tests/test_server.py -v        # WebSocket handlers

# With coverage report
pip install pytest-cov
python -m pytest tests/ --cov=. --cov-report=html
```

### Test Coverage Breakdown

| Module | Tests | What's Verified |
|--------|------:|----------------|
| `test_api.py` | 12 | Login success/fail, file CRUD, path traversal blocked, search, history clear |
| `test_auth.py` | 10 | SHA-256 determinism, registration, correct/wrong creds, JWT create/validate/deleted-user |
| `test_ai_engine.py` | 14 | Rule-based classify (9 inputs), anomaly detection (6 patterns), mocked Claude calls |
| `test_file_manager.py` | 14 | 7 path safety cases, list/names/metadata, .txt/.json/.csv/.nonexistent readers |
| `test_models.py` | 14 | All message types, JSON roundtrip, defaults, validation error on bad input |
| `test_config.py` | 12 | Type safety, range validation, directory auto-creation, all 16 settings |
| `test_server.py` | 8 | Valid/invalid/malformed auth, rate limit allow/block, file list/missing, message parse |
| **Total** | **107** | **107 passing** |

---

## Before / After — The Transformation

| Dimension | Java (Original) | ARIA (This Project) |
|-----------|:--------------:|:-------------------:|
| Protocol | Raw TCP sockets | WebSocket + REST + SSE |
| Frontend | None | React 19 + TypeScript + Tailwind |
| Concurrency | 1 client | 50+ clients (async) |
| AI Integration | None | 5 AI subsystems (Claude Sonnet 4) |
| User Interaction | Manual commands | Natural language |
| Authentication | None | JWT with 24h expiry |
| Security Layers | None | 7 layers |
| File Formats | `.txt` only | `.txt` `.csv` `.json` `.md` `.py` `.pdf` |
| Streaming | None | Token-by-token real-time |
| Configuration | Hardcoded | 16 env-vars via Pydantic |
| Logging | None | Structured rotating logs |
| Automated Tests | None | 107 passing |
| Documentation | None | Full API reference + protocol spec |

---

## Roadmap

- [ ] User self-registration via React UI
- [ ] File upload with drag-and-drop
- [ ] Multi-turn conversation memory (Claude remembers context)
- [ ] Database backend (SQLite → PostgreSQL) for users and history
- [ ] Docker + Docker Compose one-command deployment
- [ ] Role-based access control (admin / editor / viewer)
- [ ] Markdown preview rendering in the browser
- [ ] Dark / light theme toggle
- [ ] Auto-reconnect in the React WebSocket client
- [ ] Real-time collaboration — see other users' file requests

---

## Author

**Yashas D**
- GitHub: [@Yashas14](https://github.com/Yashas14)


---

<div align="center">

*Built with Python · React · Claude AI*

**ARIA — Adaptive Real-time Intelligence Assistant**
*Your documents, understood — not just served*

</div>
