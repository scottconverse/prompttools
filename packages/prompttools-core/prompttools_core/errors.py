"""Shared exception hierarchy for the prompttools suite."""

from __future__ import annotations


class PromptToolsError(Exception):
    """Base exception for all prompttools errors."""


class ParseError(PromptToolsError, ValueError):
    """Raised when a prompt file cannot be parsed."""


class ConfigError(PromptToolsError):
    """Raised when configuration is invalid or cannot be loaded."""


class TokenizerError(PromptToolsError):
    """Raised when tokenization fails."""


class ProfileNotFoundError(PromptToolsError):
    """Raised when an unknown model profile is requested."""


class PluginError(PromptToolsError):
    """Raised when plugin loading or execution fails."""


class CacheError(PromptToolsError):
    """Raised when cache read/write operations fail."""
