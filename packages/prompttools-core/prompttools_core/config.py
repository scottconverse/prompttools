"""Configuration loading and merging for the prompttools suite.

Walks up the directory tree to find config files, parses them, and merges
with built-in defaults and CLI overrides.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml

from prompttools_core.errors import ConfigError
from prompttools_core.models import ToolConfig
from prompttools_core.profiles import get_profile


def find_config_file(
    start_dir: Path,
    tool_name: Optional[str] = None,
) -> Optional[Path]:
    """Walk up directory tree to find a config file.

    Search order at each directory level:
      1. ``.prompt{tool_name}.yaml`` (tool-specific, e.g. ``.promptfmt.yaml``)
      2. ``.prompttools.yaml`` (suite-wide)
      3. ``.promptlint.yaml`` (backward compat)

    Returns the first match, or None.
    """
    current = start_dir.resolve()
    if current.is_file():
        current = current.parent

    candidates = []
    if tool_name:
        candidates.append(f".prompt{tool_name}.yaml")
    candidates.append(".prompttools.yaml")
    candidates.append(".promptlint.yaml")

    for directory in [current, *current.parents]:
        for filename in candidates:
            candidate = directory / filename
            if candidate.is_file():
                return candidate
    return None


def _parse_yaml_config(path: Path) -> dict[str, Any]:
    """Read and parse a YAML config file."""
    text = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in config {path}: {exc}") from exc

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(
            f"Config file {path} must contain a YAML mapping, "
            f"got {type(data).__name__}"
        )
    return data


def _apply_yaml_to_config(
    raw: dict[str, Any],
    config: ToolConfig,
    tool_name: Optional[str] = None,
) -> ToolConfig:
    """Merge a raw YAML config dict into a ToolConfig."""
    updates: dict[str, Any] = {}

    # Top-level shared fields
    if "model" in raw:
        updates["model"] = raw["model"]

    if "exclude" in raw:
        exclude_list = raw["exclude"]
        if isinstance(exclude_list, list):
            updates["exclude"] = [str(p) for p in exclude_list]

    if "plugins" in raw:
        plugin_list = raw["plugins"]
        if isinstance(plugin_list, list):
            updates["plugins"] = [str(p) for p in plugin_list]

    # Cache section
    cache_section = raw.get("cache", {})
    if isinstance(cache_section, dict):
        if "enabled" in cache_section:
            updates["cache_enabled"] = bool(cache_section["enabled"])
        if "dir" in cache_section:
            updates["cache_dir"] = Path(cache_section["dir"])

    # Tokenizer encoding
    tokenizer_section = raw.get("tokenizer", {})
    if isinstance(tokenizer_section, dict) and "encoding" in tokenizer_section:
        updates["tokenizer_encoding"] = tokenizer_section["encoding"]

    # Tool-specific section (e.g., raw["fmt"] for promptfmt)
    if tool_name and tool_name in raw:
        tool_section = raw[tool_name]
        if isinstance(tool_section, dict):
            # Merge tool-specific keys into extra
            extra = dict(config.extra)
            extra.update(tool_section)
            updates["extra"] = extra

    result = config.model_copy(update=updates)
    return result


def load_config(
    tool_name: str,
    config_path: Optional[Path] = None,
    cli_overrides: Optional[dict[str, Any]] = None,
    start_dir: Optional[Path] = None,
) -> ToolConfig:
    """Load, merge, and return the final ToolConfig.

    Merge priority (highest to lowest):
      1. CLI overrides
      2. Config file (discovered or explicit)
      3. Model profile defaults
      4. Built-in defaults

    Parameters
    ----------
    tool_name:
        Tool identifier (e.g. ``"fmt"``, ``"cost"``, ``"lint"``).
    config_path:
        Explicit path to a config file. If None, auto-discover.
    cli_overrides:
        Optional dict of CLI flag values.
    start_dir:
        Starting directory for config file discovery.
        Defaults to current working directory.
    """
    config = ToolConfig()

    # Discover config file
    if config_path is None and start_dir:
        config_path = find_config_file(start_dir, tool_name)
    elif config_path is None:
        config_path = find_config_file(Path.cwd(), tool_name)

    # Apply config file
    if config_path is not None:
        raw = _parse_yaml_config(config_path)
        config = _apply_yaml_to_config(raw, config, tool_name)

    # Apply model profile
    if config.model:
        profile = get_profile(config.model)
        if profile and config.tokenizer_encoding is None:
            config = config.model_copy(
                update={"tokenizer_encoding": profile.encoding}
            )

    # Apply CLI overrides
    if cli_overrides:
        updates: dict[str, Any] = {}
        for key in ("model", "tokenizer_encoding", "cache_enabled", "cache_dir"):
            if key in cli_overrides and cli_overrides[key] is not None:
                updates[key] = cli_overrides[key]
        if "exclude" in cli_overrides and cli_overrides["exclude"]:
            updates["exclude"] = cli_overrides["exclude"]
        if "plugins" in cli_overrides and cli_overrides["plugins"]:
            updates["plugins"] = cli_overrides["plugins"]
        if updates:
            config = config.model_copy(update=updates)

    return config
