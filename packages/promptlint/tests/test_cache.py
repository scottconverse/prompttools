"""Tests for promptlint.core.cache."""
from __future__ import annotations

from pathlib import Path

from promptlint.core.cache import clear_cache, get_cached, set_cached


class TestCache:
    def test_set_and_get(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / ".promptlint-cache"
        fp = tmp_path / "prompt.txt"
        fp.write_text("hello", encoding="utf-8")

        set_cached(fp, "hello", "cl100k_base", 42, cache_dir=cache_dir)
        result = get_cached(fp, "hello", "cl100k_base", cache_dir=cache_dir)
        assert result == 42

    def test_cache_miss(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / ".promptlint-cache"
        fp = tmp_path / "prompt.txt"
        result = get_cached(fp, "hello", "cl100k_base", cache_dir=cache_dir)
        assert result is None

    def test_invalidation_on_content_change(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / ".promptlint-cache"
        fp = tmp_path / "prompt.txt"

        set_cached(fp, "hello", "cl100k_base", 42, cache_dir=cache_dir)
        # Same file, different content -> cache miss
        result = get_cached(fp, "hello changed", "cl100k_base", cache_dir=cache_dir)
        assert result is None

    def test_invalidation_on_encoding_change(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / ".promptlint-cache"
        fp = tmp_path / "prompt.txt"

        set_cached(fp, "hello", "cl100k_base", 42, cache_dir=cache_dir)
        result = get_cached(fp, "hello", "p50k_base", cache_dir=cache_dir)
        assert result is None

    def test_clear_cache(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / ".promptlint-cache"
        fp = tmp_path / "prompt.txt"

        set_cached(fp, "hello", "cl100k_base", 42, cache_dir=cache_dir)
        assert cache_dir.is_dir()

        clear_cache(cache_dir)
        assert not cache_dir.exists()

    def test_clear_nonexistent(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / ".promptlint-cache"
        # Should not raise
        clear_cache(cache_dir)
