"""Built-in model profiles for the prompttools suite.

Each profile maps a model name to its context window, tokenizer encoding,
pricing, and capabilities.
"""

from __future__ import annotations

from typing import Optional

from prompttools_core.models import ModelProfile

BUILTIN_PROFILES: dict[str, ModelProfile] = {
    "gpt-4": ModelProfile(
        name="gpt-4",
        context_window=8_192,
        encoding="cl100k_base",
        provider="openai",
        max_output_tokens=4_096,
        input_price_per_mtok=30.00,
        output_price_per_mtok=60.00,
        supports_tools=True,
    ),
    "gpt-4-turbo": ModelProfile(
        name="gpt-4-turbo",
        context_window=128_000,
        encoding="cl100k_base",
        provider="openai",
        max_output_tokens=4_096,
        input_price_per_mtok=10.00,
        output_price_per_mtok=30.00,
        supports_tools=True,
    ),
    "gpt-4o": ModelProfile(
        name="gpt-4o",
        context_window=128_000,
        encoding="o200k_base",
        provider="openai",
        max_output_tokens=16_384,
        input_price_per_mtok=2.50,
        output_price_per_mtok=10.00,
        supports_tools=True,
    ),
    "gpt-4o-mini": ModelProfile(
        name="gpt-4o-mini",
        context_window=128_000,
        encoding="o200k_base",
        provider="openai",
        max_output_tokens=16_384,
        input_price_per_mtok=0.15,
        output_price_per_mtok=0.60,
        supports_tools=True,
    ),
    "claude-3-haiku": ModelProfile(
        name="claude-3-haiku",
        context_window=200_000,
        encoding="cl100k_base",
        provider="anthropic",
        max_output_tokens=4_096,
        input_price_per_mtok=0.25,
        output_price_per_mtok=1.25,
        approximate_tokenizer=True,
        supports_tools=True,
    ),
    "claude-3-sonnet": ModelProfile(
        name="claude-3-sonnet",
        context_window=200_000,
        encoding="cl100k_base",
        provider="anthropic",
        max_output_tokens=8_192,
        input_price_per_mtok=3.00,
        output_price_per_mtok=15.00,
        approximate_tokenizer=True,
        supports_tools=True,
    ),
    "claude-3-opus": ModelProfile(
        name="claude-3-opus",
        context_window=200_000,
        encoding="cl100k_base",
        provider="anthropic",
        max_output_tokens=4_096,
        input_price_per_mtok=15.00,
        output_price_per_mtok=75.00,
        approximate_tokenizer=True,
        supports_tools=True,
    ),
    "claude-4-sonnet": ModelProfile(
        name="claude-4-sonnet",
        context_window=200_000,
        encoding="cl100k_base",
        provider="anthropic",
        max_output_tokens=64_000,
        input_price_per_mtok=3.00,
        output_price_per_mtok=15.00,
        approximate_tokenizer=True,
        supports_tools=True,
    ),
    "gemini-1.5-pro": ModelProfile(
        name="gemini-1.5-pro",
        context_window=1_000_000,
        encoding="cl100k_base",
        provider="google",
        max_output_tokens=8_192,
        input_price_per_mtok=1.25,
        output_price_per_mtok=5.00,
        approximate_tokenizer=True,
        supports_tools=True,
    ),
    "gemini-2.0-flash": ModelProfile(
        name="gemini-2.0-flash",
        context_window=1_048_576,
        encoding="cl100k_base",
        provider="google",
        max_output_tokens=8_192,
        input_price_per_mtok=0.10,
        output_price_per_mtok=0.40,
        approximate_tokenizer=True,
        supports_tools=True,
    ),
}

# Mutable registry for custom profiles
_custom_profiles: dict[str, ModelProfile] = {}


def get_profile(name: str) -> Optional[ModelProfile]:
    """Look up a model profile by name.

    Checks custom profiles first, then built-in profiles.
    """
    return _custom_profiles.get(name) or BUILTIN_PROFILES.get(name)


def list_profiles() -> dict[str, ModelProfile]:
    """Return all registered profiles (built-in + custom)."""
    merged = dict(BUILTIN_PROFILES)
    merged.update(_custom_profiles)
    return merged


def register_profile(profile: ModelProfile) -> None:
    """Register a custom model profile."""
    _custom_profiles[profile.name] = profile
