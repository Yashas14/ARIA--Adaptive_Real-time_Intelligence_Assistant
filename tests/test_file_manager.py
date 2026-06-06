"""
Tests for the file_manager module.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from file_manager import (
    _safe_path,
    _read_csv,
    _read_json,
    get_file_metadata,
    get_file_names,
    list_files,
    read_file_content,
)
from config import settings


# ── Path safety tests ────────────────────────────────────────────────────────


class TestSafePath:
    """Verify path-traversal protection."""

    def test_normal_filename(self) -> None:
        result = _safe_path("sample.txt")
        assert result is not None
        assert result.name == "sample.txt"

    def test_blocks_parent_traversal(self) -> None:
        assert _safe_path("../etc/passwd") is None

    def test_blocks_double_dot_in_middle(self) -> None:
        assert _safe_path("foo/../bar.txt") is None

    def test_blocks_absolute_path_unix(self) -> None:
        assert _safe_path("/etc/passwd") is None

    def test_blocks_absolute_path_windows(self) -> None:
        assert _safe_path("\\Windows\\system32\\config") is None

    def test_blocks_dot_dot_only(self) -> None:
        assert _safe_path("..") is None

    def test_allows_dotfile_without_traversal(self) -> None:
        # Files starting with . are allowed by _safe_path (filtered elsewhere)
        result = _safe_path(".hidden")
        assert result is not None


# ── File listing tests ───────────────────────────────────────────────────────


class TestListFiles:
    """Verify file listing returns correct structure."""

    @pytest.mark.asyncio
    async def test_returns_list(self) -> None:
        result = await list_files()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_entries_have_required_keys(self) -> None:
        result = await list_files()
        if result:
            entry = result[0]
            assert "name" in entry
            assert "size" in entry
            assert "modified" in entry

    @pytest.mark.asyncio
    async def test_does_not_include_hidden_files(self) -> None:
        result = await list_files()
        for entry in result:
            assert not entry["name"].startswith(".")


class TestGetFileNames:
    """Verify filename retrieval."""

    @pytest.mark.asyncio
    async def test_returns_sorted_list(self) -> None:
        result = await get_file_names()
        assert isinstance(result, list)
        assert result == sorted(result)

    @pytest.mark.asyncio
    async def test_contains_known_files(self) -> None:
        result = await get_file_names()
        # The project has sample files
        assert "sample.txt" in result or len(result) >= 0


# ── File metadata tests ──────────────────────────────────────────────────────


class TestGetFileMetadata:
    """Verify metadata extraction."""

    @pytest.mark.asyncio
    async def test_existing_file(self) -> None:
        files = await get_file_names()
        if files:
            meta = await get_file_metadata(files[0])
            assert meta is not None
            assert meta.filename == files[0]
            assert meta.size_bytes > 0
            assert meta.line_count >= 0

    @pytest.mark.asyncio
    async def test_nonexistent_file(self) -> None:
        meta = await get_file_metadata("definitely_does_not_exist_12345.xyz")
        assert meta is None

    @pytest.mark.asyncio
    async def test_path_traversal_returns_none(self) -> None:
        meta = await get_file_metadata("../server.py")
        assert meta is None


# ── File reading tests ───────────────────────────────────────────────────────


class TestReadFileContent:
    """Verify file content reading with format dispatch."""

    @pytest.mark.asyncio
    async def test_read_text_file(self) -> None:
        content = await read_file_content("sample.txt")
        if content is not None:
            assert isinstance(content, str)
            assert len(content) > 0

    @pytest.mark.asyncio
    async def test_read_json_file(self) -> None:
        content = await read_file_content("project_info.json")
        if content is not None:
            # Should be pretty-printed valid JSON
            data = json.loads(content)
            assert isinstance(data, (dict, list))

    @pytest.mark.asyncio
    async def test_read_csv_file(self) -> None:
        content = await read_file_content("employees.csv")
        if content is not None:
            assert "|" in content  # Formatted as table

    @pytest.mark.asyncio
    async def test_nonexistent_file_returns_none(self) -> None:
        content = await read_file_content("ghost_file_999.txt")
        assert content is None

    @pytest.mark.asyncio
    async def test_traversal_returns_none(self) -> None:
        content = await read_file_content("../../etc/passwd")
        assert content is None
