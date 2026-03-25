"""SHA256-based caching layer for the prompttools suite.

Prevents redundant tokenization and parsing across all tools.
Cache entries are keyed by content hash + encoding name.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prompttools_core.errors import CacheError

logger = logging.getLogger(__name__)

_CACHE_VERSION = 1
_CACHE_FILE_NAME = "cache.json"


class PromptCache:
    """File-system based cache for token counts and other computed values."""

    def __init__(self, cache_dir: Path = Path(".prompttools-cache")) -> None:
        self._cache_dir = Path(cache_dir)
        self._data: dict[str, Any] | None = None
        self._ttl: dict[str, float] = {}  # key -> expiry timestamp (epoch seconds)

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def _cache_file(self) -> Path:
        return self._cache_dir / _CACHE_FILE_NAME

    def _load(self) -> dict[str, Any]:
        """Load cache from disk, or return fresh structure."""
        if self._data is not None:
            return self._data

        cf = self._cache_file()
        if not cf.is_file():
            self._data = {"version": _CACHE_VERSION, "entries": {}}
            return self._data

        try:
            data = json.loads(cf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load cache from %s: %s", cf, exc)
            self._data = {"version": _CACHE_VERSION, "entries": {}}
            return self._data

        if not isinstance(data, dict) or data.get("version") != _CACHE_VERSION:
            self._data = {"version": _CACHE_VERSION, "entries": {}}
            return self._data

        self._data = data
        return self._data

    def _save(self) -> None:
        """Write cache to disk."""
        if self._data is None:
            return
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            cf = self._cache_file()
            cf.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        except OSError as exc:
            raise CacheError(f"Failed to write cache: {exc}") from exc

    def get(self, key: str) -> Any | None:
        """Look up a cached value by key. Returns None if expired."""
        data = self._load()
        entry = data.get("entries", {}).get(key)
        if entry is None:
            return None
        # Check TTL expiry
        if key in self._ttl:
            if datetime.now(timezone.utc).timestamp() > self._ttl[key]:
                # Entry has expired — remove it
                self.invalidate(key)
                return None
        return entry.get("value")

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value in the cache.

        Parameters
        ----------
        key:
            Cache key.
        value:
            Value to store.
        ttl:
            Time-to-live in seconds. If provided, the entry will expire
            after this many seconds and subsequent get() calls will
            return None.
        """
        data = self._load()
        data.setdefault("entries", {})[key] = {
            "value": value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if ttl is not None:
            self._ttl[key] = datetime.now(timezone.utc).timestamp() + ttl
        elif key in self._ttl:
            del self._ttl[key]
        self._save()

    def invalidate(self, key: str) -> None:
        """Remove a specific key from the cache."""
        data = self._load()
        data.get("entries", {}).pop(key, None)
        self._save()

    def clear(self) -> None:
        """Remove the entire cache directory."""
        if self._cache_dir.is_dir():
            shutil.rmtree(self._cache_dir)
        self._data = None

    @staticmethod
    def content_key(content: str, encoding: str) -> str:
        """Generate a cache key from content hash and encoding."""
        raw = (content + encoding).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()
