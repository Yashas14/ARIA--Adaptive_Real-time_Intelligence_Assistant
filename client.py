"""
AI-Powered Async WebSocket Client — Rich Terminal UI
=====================================================
Interactive terminal client with:

* Beautiful Rich panels, tables, spinners, and syntax highlighting
* Three interaction modes: file requests, AI chat, file summarization
* Reconnect logic with exponential back-off
* JWT token stored in session and sent with every request
* Streaming response display (token-by-token for AI output)

Original Java project by Yashas D — completely rebuilt in Python.
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from typing import Any, Optional

import websockets
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from config import settings
from models import (
    ClientMessage,
    MessageType,
    ResponseType,
    ServerMessage,
)

console = Console()


# ═════════════════════════════════════════════════════════════════════════════
# Connection Manager
# ═════════════════════════════════════════════════════════════════════════════


class ServerConnection:
    """Manages a WebSocket connection with automatic reconnect logic."""

    def __init__(self, uri: str) -> None:
        self.uri = uri
        self.ws: Optional[websockets.ClientConnection] = None
        self.token: Optional[str] = None
        self.username: Optional[str] = None
        self._max_retries: int = 5

    async def connect(self) -> None:
        """Establish a WebSocket connection with exponential back-off."""
        backoff = 1.0
        for attempt in range(1, self._max_retries + 1):
            try:
                ssl_ctx = None
                if self.uri.startswith("wss://"):
                    import ssl
                    ssl_ctx = ssl.create_default_context()
                    ssl_ctx.check_hostname = False
                    ssl_ctx.verify_mode = ssl.CERT_NONE  # dev self-signed cert
                self.ws = await websockets.connect(
                    self.uri, ssl=ssl_ctx, max_size=2**22,
                )
                console.print(f"[green]✓ Connected to {self.uri}[/green]")
                return
            except Exception as exc:
                console.print(
                    f"[yellow]Connection attempt {attempt}/{self._max_retries} "
                    f"failed: {exc}[/yellow]"
                )
                if attempt < self._max_retries:
                    console.print(f"[dim]Retrying in {backoff:.1f}s …[/dim]")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 30.0)
        console.print("[red bold]Could not connect to server. Exiting.[/red bold]")
        sys.exit(1)

    async def send(self, msg: ClientMessage) -> None:
        """Serialise and send a :class:`ClientMessage`."""
        if msg.token is None and self.token:
            msg.token = self.token
        assert self.ws is not None
        await self.ws.send(msg.model_dump_json())

    async def receive(self) -> ServerMessage:
        """Wait for and deserialise the next :class:`ServerMessage`."""
        assert self.ws is not None
        raw = await self.ws.recv()
        return ServerMessage.model_validate_json(raw)

    async def receive_stream(self, request_id: str) -> str:
        """Collect CHUNK messages until COMPLETE or ERROR.

        Tokens are printed to the console in real-time as they arrive.
        Returns the full concatenated content.
        """
        chunks: list[str] = []
        while True:
            resp = await self.receive()
            if resp.request_id != request_id:
                continue

            if resp.type == ResponseType.ERROR:
                console.print(f"\n[red]✗ Error: {resp.content}[/red]")
                return ""

            if resp.type == ResponseType.COMPLETE:
                if resp.metadata:
                    _print_metadata(resp.metadata)
                return "".join(chunks)

            if resp.type == ResponseType.CHUNK:
                chunks.append(resp.content)
                console.print(resp.content, end="", highlight=False)

            elif resp.type == ResponseType.AUTH_SUCCESS:
                self.token = resp.content
                self.username = resp.metadata.get("username", "")
                console.print(f"[green]✓ Authenticated as {self.username}[/green]")
                return resp.content

            elif resp.type == ResponseType.AUTH_FAILURE:
                console.print(f"[red]✗ Auth failed: {resp.content}[/red]")
                return ""

    async def close(self) -> None:
        """Gracefully close the WebSocket."""
        if self.ws:
            await self.ws.close()


# ═════════════════════════════════════════════════════════════════════════════
# UI Helpers
# ═════════════════════════════════════════════════════════════════════════════


def _print_metadata(meta: dict[str, Any]) -> None:
    """Render metadata as a compact table."""
    if not meta:
        return
    console.print()
    table = Table(
        box=box.ROUNDED,
        title="Metadata",
        title_style="bold cyan",
        expand=False,
    )
    table.add_column("Key", style="bold")
    table.add_column("Value")
    for key, value in meta.items():
        table.add_row(str(key), str(value))
    console.print(table)


def print_banner() -> None:
    """Display the client startup banner."""
    banner = Text()
    banner.append("╔══════════════════════════════════════════════╗\n", style="bright_blue")
    banner.append("║   ARIA — Adaptive Real-time Intelligence     ║\n", style="bold magenta")
    banner.append("║   Assistant  •  WebSocket Client             ║\n", style="dim")
    banner.append("╚══════════════════════════════════════════════╝\n", style="bright_blue")
    banner.append("  Type ")
    banner.append("/help", style="bold green")
    banner.append(" for available commands\n")
    console.print(Panel(banner, border_style="bright_blue", expand=False))


def print_help() -> None:
    """Render the command reference table."""
    table = Table(
        title="Available Commands",
        box=box.ROUNDED,
        border_style="cyan",
    )
    table.add_column("Command", style="bold green")
    table.add_column("Description")
    commands = [
        ("/file <name>", "Request and display a file"),
        ("/files", "List all available files"),
        ("/ask <question>", "Ask Claude AI a question"),
        ("/summarize <file>", "AI-generated summary of a file"),
        ("/search <query>", "Natural-language file search"),
        ("/status", "Show connection status"),
        ("/help", "Show this help table"),
        ("/quit", "Disconnect and exit"),
    ]
    for cmd, desc in commands:
        table.add_row(cmd, desc)
    console.print(table)


# ═════════════════════════════════════════════════════════════════════════════
# Authentication
# ═════════════════════════════════════════════════════════════════════════════


async def login(conn: ServerConnection) -> bool:
    """Prompt for credentials and authenticate with the server."""
    console.print(
        Panel("[bold]Authentication Required[/bold]", border_style="yellow"),
    )
    username = Prompt.ask("[cyan]Username[/cyan]")
    password = Prompt.ask("[cyan]Password[/cyan]", password=True)
    req_id = str(uuid.uuid4())
    msg = ClientMessage(
        type=MessageType.AUTH_LOGIN,
        payload=json.dumps({"username": username, "password": password}),
        request_id=req_id,
    )
    await conn.send(msg)
    await conn.receive_stream(req_id)
    return conn.token is not None


# ═════════════════════════════════════════════════════════════════════════════
# Command Dispatch
# ═════════════════════════════════════════════════════════════════════════════


async def handle_command(conn: ServerConnection, user_input: str) -> bool:
    """Process a single user command.  Returns ``False`` to quit."""
    stripped = user_input.strip()
    if not stripped:
        return True

    # ── Exit ─────────────────────────────────────────────────────────────
    if stripped.lower() in ("/quit", "/exit", "/q"):
        return False

    # ── Help ─────────────────────────────────────────────────────────────
    if stripped.lower() == "/help":
        print_help()
        return True

    # ── Status ───────────────────────────────────────────────────────────
    if stripped.lower() == "/status":
        console.print(
            Panel(
                f"[bold]Server:[/bold]  {conn.uri}\n"
                f"[bold]User:[/bold]    {conn.username or 'N/A'}\n"
                f"[bold]Token:[/bold]   {'✓ set' if conn.token else '✗ none'}",
                title="Connection Status",
                border_style="green",
            )
        )
        return True

    # ── List files ───────────────────────────────────────────────────────
    if stripped.lower() in ("/files", "/file list"):
        req_id = str(uuid.uuid4())
        await conn.send(
            ClientMessage(
                type=MessageType.FILE_REQUEST,
                payload="list",
                request_id=req_id,
            )
        )
        console.print("[dim]Fetching file list …[/dim]")
        result = await conn.receive_stream(req_id)
        if result:
            _render_file_list(result)
        return True

    # ── File request ─────────────────────────────────────────────────────
    if stripped.lower().startswith("/file "):
        filename = stripped[6:].strip()
        req_id = str(uuid.uuid4())
        await conn.send(
            ClientMessage(
                type=MessageType.FILE_REQUEST,
                payload=filename,
                request_id=req_id,
            )
        )
        console.print(f"[dim]Requesting file: {filename} …[/dim]")
        result = await conn.receive_stream(req_id)
        if result:
            console.print(
                Panel(
                    Syntax(result, "text", theme="monokai", line_numbers=True),
                    title=filename,
                    border_style="green",
                )
            )
        return True

    # ── AI query ─────────────────────────────────────────────────────────
    if stripped.lower().startswith("/ask "):
        question = stripped[5:].strip()
        req_id = str(uuid.uuid4())
        await conn.send(
            ClientMessage(
                type=MessageType.AI_QUERY,
                payload=question,
                request_id=req_id,
            )
        )
        console.print(
            Panel.fit("[bold cyan]AI Response[/bold cyan]", border_style="cyan"),
        )
        await conn.receive_stream(req_id)
        console.print()
        return True

    # ── Summarize ────────────────────────────────────────────────────────
    if stripped.lower().startswith("/summarize "):
        filename = stripped[11:].strip()
        req_id = str(uuid.uuid4())
        await conn.send(
            ClientMessage(
                type=MessageType.FILE_SUMMARIZE,
                payload=filename,
                request_id=req_id,
            )
        )
        console.print(f"[dim]Summarizing {filename} …[/dim]")
        result = await conn.receive_stream(req_id)
        if result:
            _render_summary(result, filename)
        console.print()
        return True

    # ── File search ──────────────────────────────────────────────────────
    if stripped.lower().startswith("/search "):
        query = stripped[8:].strip()
        req_id = str(uuid.uuid4())
        await conn.send(
            ClientMessage(
                type=MessageType.FILE_SEARCH,
                payload=query,
                request_id=req_id,
            )
        )
        console.print(f"[dim]Searching: {query} …[/dim]")
        result = await conn.receive_stream(req_id)
        if result:
            _render_search_results(result)
        return True

    # ── Default: treat free-text as AI query ─────────────────────────────
    req_id = str(uuid.uuid4())
    await conn.send(
        ClientMessage(
            type=MessageType.AI_QUERY,
            payload=stripped,
            request_id=req_id,
        )
    )
    console.print(
        Panel.fit("[bold cyan]AI Response[/bold cyan]", border_style="cyan"),
    )
    await conn.receive_stream(req_id)
    console.print()
    return True


# ── Rendering helpers ────────────────────────────────────────────────────────


def _render_file_list(raw: str) -> None:
    """Pretty-print a JSON file list as a table."""
    try:
        files = json.loads(raw)
        table = Table(
            title="Available Files",
            box=box.ROUNDED,
            border_style="cyan",
        )
        table.add_column("Filename", style="bold")
        table.add_column("Size", justify="right")
        table.add_column("Last Modified")
        for f in files:
            table.add_row(f["name"], f["size"], f["modified"])
        console.print(table)
    except json.JSONDecodeError:
        console.print(raw)


def _render_summary(raw: str, filename: str) -> None:
    """Pretty-print a structured file summary."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        console.print(raw)
        return

    console.print()
    console.print(
        Panel(
            f"[bold]{data.get('executive_summary', 'N/A')}[/bold]",
            title=f"Summary: {filename}",
            border_style="green",
        )
    )

    topics = data.get("key_topics", [])
    if topics:
        console.print("[bold cyan]Key Topics:[/bold cyan]")
        for topic in topics:
            console.print(f"  [cyan]●[/cyan] {topic}")

    sentiment = data.get("sentiment", "unknown")
    colour = {"positive": "green", "negative": "red"}.get(sentiment, "yellow")
    console.print(f"\n[bold]Sentiment:[/bold] [{colour}]{sentiment}[/{colour}]")

    questions = data.get("follow_up_questions", [])
    if questions:
        console.print("\n[bold magenta]Follow-up Questions:[/bold magenta]")
        for q in questions:
            console.print(f"  [magenta]?[/magenta] {q}")


def _render_search_results(raw: str) -> None:
    """Pretty-print file search matches."""
    try:
        matches = json.loads(raw)
        if matches:
            console.print("[bold cyan]Matching files:[/bold cyan]")
            for m in matches:
                console.print(f"  [green]●[/green] {m}")
        else:
            console.print("[yellow]No matching files found.[/yellow]")
    except json.JSONDecodeError:
        console.print(raw)


# ═════════════════════════════════════════════════════════════════════════════
# Main Loop
# ═════════════════════════════════════════════════════════════════════════════


async def main() -> None:
    """Entry point — connect, authenticate, then enter the command loop."""
    scheme = "wss" if settings.TLS_ENABLED else "ws"
    uri = f"{scheme}://{settings.HOST}:{settings.PORT}"

    conn = ServerConnection(uri)
    print_banner()
    await conn.connect()

    # Authenticate
    if not await login(conn):
        console.print("[red]Authentication failed. Exiting.[/red]")
        await conn.close()
        return

    print_help()

    try:
        while True:
            try:
                user_input: str = await asyncio.to_thread(
                    Prompt.ask,
                    f"\n[bold blue]{conn.username}[/bold blue]",
                )
                keep_going = await handle_command(conn, user_input)
                if not keep_going:
                    break
            except (EOFError, KeyboardInterrupt):
                break
    finally:
        console.print("[dim]Disconnecting …[/dim]")
        await conn.close()
        console.print("[green]Goodbye![/green]")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
