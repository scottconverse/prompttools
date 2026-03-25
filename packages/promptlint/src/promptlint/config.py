"""Configuration loading and merging for promptlint.

Walks up the directory tree to find ``.promptlint.yaml``, parses it,
merges with built-in defaults and CLI overrides, and optionally applies
a model profile.

Uses prompttools-core for profile lookups.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from promptlint.models import LintConfig
from prompttools_core.profiles import BUILTIN_PROFILES, get_profile

_CONFIG_FILENAME = ".promptlint.yaml"


def get_default_config() -> LintConfig:
    """Return a ``LintConfig`` populated with built-in defaults only."""
    return LintConfig()


def _find_config_file(start: Path) -> Path | None:
    """Walk *start* and its ancestors looking for ``.promptlint.yaml``.

    Returns the first matching path, or ``None`` if none is found.
    """
    current = start.resolve()
    if current.is_file():
        current = current.parent

    for directory in [current, *current.parents]:
        candidate = directory / _CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    return None


def _parse_yaml_config(path: Path) -> dict[str, Any]:
    """Read and parse a YAML config file, returning a raw dict."""
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file {path} must contain a YAML mapping, got {type(data).__name__}")
    return data


def _apply_yaml_to_config(raw: dict[str, Any], config: LintConfig) -> LintConfig:
    """Merge a raw YAML config dict into a ``LintConfig`` instance.

    Only keys present in the YAML are applied; everything else keeps
    its current value (default or previously merged).
    """
    updates: dict[str, Any] = {}

    # Top-level scalar fields
    if "model" in raw:
        updates["model"] = raw["model"]

    # Tokenizer section
    tokenizer_section = raw.get("tokenizer", {})
    if isinstance(tokenizer_section, dict) and "encoding" in tokenizer_section:
        updates["tokenizer_encoding"] = tokenizer_section["encoding"]

    # Token budget section
    budget = raw.get("token_budget", {})
    if isinstance(budget, dict):
        if "warn_threshold" in budget:
            updates["token_warn_threshold"] = int(budget["warn_threshold"])
        if "error_threshold" in budget:
            updates["token_error_threshold"] = int(budget["error_threshold"])
        if "system_prompt_threshold" in budget:
            updates["system_prompt_threshold"] = int(budget["system_prompt_threshold"])
        if "stop_word_ratio" in budget:
            updates["stop_word_ratio"] = float(budget["stop_word_ratio"])

    # Formatting section
    formatting = raw.get("formatting", {})
    if isinstance(formatting, dict):
        if "max_line_length" in formatting:
            updates["max_line_length"] = int(formatting["max_line_length"])
        if "repetition_threshold" in formatting:
            updates["repetition_threshold"] = int(formatting["repetition_threshold"])

    # Rule severity overrides
    rules_section = raw.get("rules", {})
    if isinstance(rules_section, dict):
        overrides = dict(config.rule_overrides)
        for rule_key, severity_val in rules_section.items():
            overrides[str(rule_key)] = str(severity_val)
        updates["rule_overrides"] = overrides

    # Ignored rules
    if "ignore" in raw:
        ignore_list = raw["ignore"]
        if isinstance(ignore_list, list):
            updates["ignored_rules"] = [str(r) for r in ignore_list]

    # Exclude patterns
    if "exclude" in raw:
        exclude_list = raw["exclude"]
        if isinstance(exclude_list, list):
            updates["exclude_patterns"] = [str(p) for p in exclude_list]

    # Plugin directories
    if "plugins" in raw:
        plugin_list = raw["plugins"]
        if isinstance(plugin_list, list):
            updates["plugin_dirs"] = [Path(p) for p in plugin_list]

    # Context window (manual override)
    if "context_window" in raw:
        updates["context_window"] = int(raw["context_window"])

    return config.model_copy(update=updates)


def _apply_model_profile(config: LintConfig) -> LintConfig:
    """If ``config.model`` is set, apply the matching model profile.

    The profile sets ``tokenizer_encoding``, ``context_window``, and
    adjusts token thresholds (50%/80% of context window) unless they
    were explicitly overridden in the YAML.
    """
    if config.model is None:
        return config

    profile = get_profile(config.model)
    if profile is None:
        return config

    updates: dict[str, Any] = {
        "tokenizer_encoding": profile.encoding,
        "context_window": profile.context_window,
        "token_warn_threshold": int(profile.context_window * 0.5),
        "token_error_threshold": int(profile.context_window * 0.8),
    }

    return config.model_copy(update=updates)


def _apply_cli_overrides(config: LintConfig, overrides: dict[str, Any]) -> LintConfig:
    """Apply CLI flag overrides on top of the current config."""
    if not overrides:
        return config

    updates: dict[str, Any] = {}

    simple_keys = {
        "model",
        "tokenizer_encoding",
        "token_warn_threshold",
        "token_error_threshold",
        "system_prompt_threshold",
        "stop_word_ratio",
        "max_line_length",
        "repetition_threshold",
        "context_window",
    }
    for key in simple_keys:
        if key in overrides and overrides[key] is not None:
            updates[key] = overrides[key]

    # --ignore adds to the ignored list
    if "ignore" in overrides and overrides["ignore"]:
        existing = list(config.ignored_rules)
        if isinstance(overrides["ignore"], str):
            existing.extend(r.strip() for r in overrides["ignore"].split(","))
        elif isinstance(overrides["ignore"], list):
            existing.extend(overrides["ignore"])
        updates["ignored_rules"] = existing

    # --select restricts to only the listed rules
    if "select" in overrides and overrides["select"]:
        pass  # handled at engine level, not config level

    if "exclude_patterns" in overrides and overrides["exclude_patterns"]:
        updates["exclude_patterns"] = overrides["exclude_patterns"]

    if "plugin_dirs" in overrides and overrides["plugin_dirs"]:
        updates["plugin_dirs"] = [Path(p) for p in overrides["plugin_dirs"]]

    result = config.model_copy(update=updates)

    # If model was overridden via CLI, re-apply model profile
    if "model" in updates:
        result = _apply_model_profile(result)

    return result


def load_config(
    target_path: Path,
    cli_overrides: dict[str, Any] | None = None,
) -> LintConfig:
    """Load, merge, and return the final ``LintConfig``.

    Merge priority (highest to lowest):
      1. CLI flags (``cli_overrides``)
      2. ``.promptlint.yaml`` found by walking up from *target_path*
      3. Model profile defaults (if ``model`` is specified)
      4. Built-in defaults
    """
    config = get_default_config()

    # Discover and apply YAML config file
    config_path = _find_config_file(target_path)
    if config_path is not None:
        raw = _parse_yaml_config(config_path)
        config = _apply_yaml_to_config(raw, config)

    # Apply model profile (sets tokenizer, thresholds from profile)
    config = _apply_model_profile(config)

    # Apply CLI overrides last (highest priority)
    if cli_overrides:
        config = _apply_cli_overrides(config, cli_overrides)

    return config
