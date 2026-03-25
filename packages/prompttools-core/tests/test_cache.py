"""Tests for prompttools_core.cache."""

import json

import pytest

from prompttools_core.cache import PromptCache
from prompttools_core.errors import CacheError


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


class TestCacheTTL:
    def test_ttl_zero_causes_immediate_expiry(self, tmp_path):
        cache = PromptCache(cache_dir=tmp_path / "cache")
        cache.set("key", "value", ttl=0)
        # TTL=0 means it expires at the moment it was set; next get() returns None
        result = cache.get("key")
        assert result is None

    def test_no_ttl_does_not_expire(self, tmp_path):
        cache = PromptCache(cache_dir=tmp_path / "cache")
        cache.set("key", "value")  # No TTL
        # Without TTL, value should persist
        assert cache.get("key") == "value"
        assert cache.get("key") == "value"  # Multiple gets still work


class TestCachePersistence:
    def test_survives_reload_from_disk(self, tmp_path):
        cache_dir = tmp_path / "cache"
        cache1 = PromptCache(cache_dir=cache_dir)
        cache1.set("key1", "value1")
        cache1.set("key2", {"nested": True})

        # Create a new instance pointing at the same directory
        cache2 = PromptCache(cache_dir=cache_dir)
        assert cache2.get("key1") == "value1"
        assert cache2.get("key2") == {"nested": True}

    def test_corrupted_json_returns_fresh_cache(self, tmp_path):
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "cache.json"
        cache_file.write_text("{{not valid json!!", encoding="utf-8")

        cache = PromptCache(cache_dir=cache_dir)
        # Should not raise; returns fresh empty cache
        assert cache.get("anything") is None
        # Should be able to write
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_version_mismatch_returns_fresh_cache(self, tmp_path):
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "cache.json"
        # Write cache with wrong version
        data = {"version": 999, "entries": {"old": {"value": "stale"}}}
        cache_file.write_text(json.dumps(data), encoding="utf-8")

        cache = PromptCache(cache_dir=cache_dir)
        assert cache.get("old") is None  # Old data discarded

    def test_write_failure_raises_cache_error(self, tmp_path):
        # Use a path that will fail to write (directory as file)
        cache_dir = tmp_path / "cache"
        cache = PromptCache(cache_dir=cache_dir)
        cache.set("key", "value")  # This creates the cache dir

        # Make cache file read-only to provoke error
        cache_file = cache_dir / "cache.json"
        import os
        import stat
        os.chmod(cache_file, stat.S_IREAD)
        try:
            with pytest.raises(CacheError, match="Failed to write"):
                cache._data = None  # Force reload
                cache.set("key2", "value2")
        finally:
            os.chmod(cache_file, stat.S_IWRITE | stat.S_IREAD)
