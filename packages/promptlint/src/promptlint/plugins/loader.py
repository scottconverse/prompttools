"""Plugin discovery and loading for custom promptlint rules.

Uses prompttools-core's generic plugin discovery mechanism,
adding promptlint-specific validation (PLX prefix requirement).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

from prompttools_core.plugins import discover_plugins as _discover_plugins

from promptlint.rules.base import BasePipelineRule, BaseRule

logger = logging.getLogger(__name__)


def _validate_plugin_rule_id(rule_cls: type) -> bool:
    """Ensure plugin rule IDs start with PLX."""
    rule_id: str = getattr(rule_cls, "rule_id", "")
    if not rule_id.startswith("PLX"):
        logger.warning(
            "Plugin rule %s has rule_id '%s' which does not start with 'PLX'. "
            "Skipping.",
            rule_cls.__name__,
            rule_id,
        )
        return False
    return True


def load_plugins_from_directory(
    directory: Path,
) -> list[Union[BaseRule, BasePipelineRule]]:
    """Scan a single directory for plugin rule classes and return instances."""
    # Use core's generic discovery for BaseRule
    base_classes = _discover_plugins([directory], BaseRule)
    pipeline_classes = _discover_plugins([directory], BasePipelineRule)

    all_classes = list(set(base_classes + pipeline_classes))
    instances: list[Union[BaseRule, BasePipelineRule]] = []

    for cls in all_classes:
        if _validate_plugin_rule_id(cls):
            try:
                instance = cls()
                instances.append(instance)
                logger.debug(
                    "Loaded plugin rule %s (%s)",
                    getattr(instance, "rule_id", "?"),
                    cls.__name__,
                )
            except Exception:
                logger.exception("Failed to instantiate plugin rule %s", cls.__name__)

    return instances


def load_plugins(
    plugin_dirs: list[Path],
) -> list[Union[BaseRule, BasePipelineRule]]:
    """Load plugin rules from all configured directories."""
    all_plugins: list[Union[BaseRule, BasePipelineRule]] = []
    seen_ids: set[str] = set()

    for directory in plugin_dirs:
        plugins = load_plugins_from_directory(directory)
        for plugin in plugins:
            if plugin.rule_id in seen_ids:
                logger.warning(
                    "Duplicate plugin rule_id '%s' from %s. Skipping.",
                    plugin.rule_id,
                    directory,
                )
                continue
            seen_ids.add(plugin.rule_id)
            all_plugins.append(plugin)

    return all_plugins
