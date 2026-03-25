"""Tests for prompttools_core.cache."""

import pytest

from prompttools_core.cache import PromptCache


class TestPromptCacheGetSet:
    def test_get_returns_none_on_miss(self, tmp_path):
        cache = PromptCache(cache_dir=tmp_path / "cache")
        assert cache.get("nonexistent_key") is None

    def test_set_then_get(self, tmp_path):
        cache = PromptCache(cache_dir=tmp_path / "cache")
        cache.set("my_key", 42)
        assert cache.get("my_key") == 42

    def test_set_complex_value(self, tmp_path):
        cache = PromptCache(cache_dir=tmp_path / "cache")
        value = {"tokens": 100, "encoding": "cl100k_base"}
        cache.set("complex", value)
        result = cache.get("complex")
        assert result == value

    def test_overwrite_existing_key(self, tmp_path):
        cache = PromptCache(cache_dir=tmp_path / "cache")
        cache.set("key", "old")
        cache.set("key", "new")
        assert cache.get("key") == "new"


class TestContentKey:
    def test_deterministic(self):
        key1 = PromptCache.content_key("hello", "cl100k_base")
        key2 = PromptCache.content_key("hello", "cl100k_base")
        assert key1 == key2

    def test_different_content_different_key(self):
        key1 = PromptCache.content_key("hello", "cl100k_base")
        key2 = PromptCache.content_key("world", "cl100k_base")
        assert key1 != key2

    def test_different_encoding_different_key(self):
        key1 = PromptCache.content_key("hello", "cl100k_base")
        key2 = PromptCache.content_key("hello", "o200k_base")
        assert key1 != key2

    def test_key_is_hex_string(self):
        key = PromptCache.content_key("test", "enc")
        assert len(key) == 64  # SHA256 hex
        assert all(c in "0123456789abcdef" for c in key)


class TestInvalidate:
    def test_invalidate_removes_key(self, tmp_path):
        cache = PromptCache(cache_dir=tmp_path / "cache")
        cache.set("key", "value")
        assert cache.get("key") == "value"
        cache.invalidate("key")
        assert cache.get("key") is None

    def test_invalidate_nonexistent_key_no_error(self, tmp_path):
        cache = PromptCache(cache_dir=tmp_path / "cache")
        cache.invalidate("nonexistent")  # Should not raise


class TestClear:
    def test_clear_removes_cache_dir(self, tmp_path):
        cache_dir = tmp_path / "cache"
        cache = PromptCache(cache_dir=cache_dir)
        cache.set("key", "value")
        assert cache_dir.is_dir()
        cache.clear()
        assert not cache_dir.is_dir()

    def test_clear_then_get_returns_none(self, tmp_path):
        cache = PromptCache(cache_dir=tmp_path / "cache")
        cache.set("key", "value")
        cache.clear()
        assert cache.get("key") is None

    def test_clear_nonexistent_dir_no_error(self, tmp_path):
        cache = PromptCache(cache_dir=tmp_path / "nonexistent")
        cache.clear()  # Should not raise
