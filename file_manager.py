"""
File Manager — Async file I/O, metadata extraction, and multi-format support.

Serves files from the configured ``FILES_DIR`` with path-traversal protection.
Supports ``.txt``, ``.md``, ``.py``, ``.log``, ``.csv``, ``.json``, and
``.pdf`` (via optional ``PyPDF2`` dependency).
"""

from __future__ import annotations

import csv
import io
import json as json_lib
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiofiles
from loguru import logger

from config import settings
from models import FileMeta

_FILES_ROOT: Path = settings.FILES_DIR


# ── Public API ───────────────────────────────────────────────────────────────

async def list_files() -> list[dict[str, str]]:
    """Return a list of available files with basic info (name, size, modified)."""
    results: list[dict[str, str]] = []
    if not _FILES_ROOT.exists():
        return results
    for entry in sorted(_FILES_ROOT.iterdir()):
        if entry.is_file() and not entry.name.startswith("."):
            stat = entry.stat()
            results.append(
                {
                    "name": entry.name,
                    "size": f"{stat.st_size:,} bytes",
                    "modified": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                }
            )
    return results


async def get_file_metadata(filename: str) -> Optional[FileMeta]:
    """Build a :class:`FileMeta` for *filename*, or ``None`` if not found."""
    path = _safe_path(filename)
    if path is None or not path.is_file():
        return None
    stat = path.stat()

    line_count = 0
    try:
        async with aiofiles.open(path, "r", encoding="utf-8", errors="replace") as fh:
            async for _ in fh:
                line_count += 1
    except Exception:
        pass

    mime, _ = mimetypes.guess_type(str(path))
    return FileMeta(
        filename=path.name,
        size_bytes=stat.st_size,
        line_count=line_count,
        last_modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        mime_type=mime or "application/octet-stream",
    )


async def read_file_content(filename: str) -> Optional[str]:
    """Read and return the textual content of *filename*.

    Dispatches to format-specific readers based on extension.
    Returns ``None`` when the file does not exist or cannot be read.
    """
    path = _safe_path(filename)
    if path is None or not path.is_file():
        return None

    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            return await _read_pdf(path)
        if ext == ".csv":
            return await _read_csv(path)
        if ext == ".json":
            return await _read_json(path)
        # Default: treat as UTF-8 text (.txt, .md, .py, .log, etc.)
        async with aiofiles.open(path, "r", encoding="utf-8", errors="replace") as fh:
            return await fh.read()
    except Exception as exc:
        logger.error("Error reading {}: {}", filename, exc)
        return None


async def get_file_names() -> list[str]:
    """Return a sorted list of filenames available for serving."""
    if not _FILES_ROOT.exists():
        return []
    return sorted(
        entry.name
        for entry in _FILES_ROOT.iterdir()
        if entry.is_file() and not entry.name.startswith(".")
    )


# ── Private helpers ──────────────────────────────────────────────────────────

def _safe_path(filename: str) -> Optional[Path]:
    """Resolve *filename* inside ``FILES_ROOT``, blocking path-traversal attacks."""
    if ".." in filename or filename.startswith(("/", "\\")):
        logger.warning("Path traversal attempt blocked: {!r}", filename)
        return None

    resolved = (_FILES_ROOT / filename).resolve()
    if not str(resolved).startswith(str(_FILES_ROOT.resolve())):
        logger.warning("Path escape attempt blocked: {!r}", filename)
        return None

    return resolved


async def _read_pdf(path: Path) -> str:
    """Extract text from a PDF (requires ``PyPDF2``)."""
    try:
        from PyPDF2 import PdfReader  # type: ignore[import-untyped]

        reader = PdfReader(str(path))
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages) if pages else "(empty PDF)"
    except ImportError:
        return "(PDF support requires PyPDF2 — pip install PyPDF2)"
    except Exception as exc:
        return f"(Failed to read PDF: {exc})"


async def _read_csv(path: Path) -> str:
    """Read a CSV and return a neatly formatted text table."""
    async with aiofiles.open(path, "r", encoding="utf-8", errors="replace") as fh:
        raw = await fh.read()
    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)
    if not rows:
        return "(empty CSV)"

    col_widths = [
        max(len(str(row[i])) for row in rows if i < len(row))
        for i in range(len(rows[0]))
    ]
    lines: list[str] = []
    for idx, row in enumerate(rows):
        line = " | ".join(str(cell).ljust(col_widths[j]) for j, cell in enumerate(row))
        lines.append(line)
        if idx == 0:
            lines.append("-+-".join("-" * w for w in col_widths))
    return "\n".join(lines)


async def _read_json(path: Path) -> str:
    """Read a JSON file and return it pretty-printed."""
    async with aiofiles.open(path, "r", encoding="utf-8", errors="replace") as fh:
        raw = await fh.read()
    data = json_lib.loads(raw)
    return json_lib.dumps(data, indent=2, ensure_ascii=False)
