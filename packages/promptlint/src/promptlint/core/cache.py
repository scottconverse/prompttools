"""Token-count caching for promptlint.

Wraps prompttools-core's PromptCache class to maintain the original
function-based API for backward compatibility.
"""

from __future__ import annotations

from pathlib import Path

from prompttools_core.cache import PromptCache

_CACHE_VERSION = 1
_CACHE_DIR_NAME = ".promptlint-cache"
_CACHE_FILE_NAME = "cache.json"


def _cache_key(content: str, encoding: str) -> str:
    """Compute a SHA256 cache key from file content + encoding name."""
    return PromptCache.content_key(content, encoding)


def _default_cache_dir(path: Path) -> Path:
    """Resolve the default cache directory relative to the target path."""
    base = path.resolve()
    if base.is_file():
        base = base.parent
    return base / _CACHE_DIR_NAME


def get_cached(
    path: Path,
    content: str,
    encoding: str,
    cache_dir: Path | None = None,
) -> int | None:
    """Look up a cached token count."""
    if cache_dir is None:
        cache_dir = _default_cache_dir(path)

    cache = PromptCache(cache_dir)
    key = _cache_key(content, encoding)
    return cache.get(key)


def set_cached(
    path: Path,
    content: str,
    encoding: str,
    token_count: int,
    cache_dir: Path | None = None,
) -> None:
    """Store a token count in the cache."""
    if cache_dir is None:
        cache_dir = _default_cache_dir(path)

    cache = PromptCache(cache_dir)
    key = _cache_key(content, encoding)
    cache.set(key, token_count)


def clear_cache(cache_dir: Path) -> None:
    """Remove the entire cache directory."""
    cache = PromptCache(cache_dir)
    cache.clear()
