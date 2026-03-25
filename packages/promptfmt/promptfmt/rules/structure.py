"""YAML/JSON structure normalization for promptfmt."""

from __future__ import annotations

import json
import logging
from collections import OrderedDict
from typing import Any

import yaml

from prompttools_core.models import PromptFormat

logger = logging.getLogger(__name__)


def _to_plain_dict(obj: Any) -> Any:
    """Recursively convert OrderedDicts to plain dicts."""
    if isinstance(obj, dict):
        return {k: _to_plain_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_plain_dict(item) for item in obj]
    return obj


def _sort_dict(d: dict, priority_keys: list[str] | None = None) -> OrderedDict:
    """Sort a dict, with priority keys first in order."""
    if priority_keys is None:
        priority_keys = []

    result = OrderedDict()
    # Add priority keys first (in order)
    for key in priority_keys:
        if key in d:
            result[key] = d[key]
    # Add remaining keys sorted
    for key in sorted(d.keys()):
        if key not in result:
            result[key] = d[key]
    return result


def apply_yaml(content: str, indent: int = 2, sort_keys: bool = True) -> str:
    """Normalize YAML structure: sorted keys, consistent indentation."""
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        logger.warning("YAML parsing failed during structure normalization: %s", exc)
        return content
    if not isinstance(data, dict):
        logger.warning("YAML content is not a mapping; skipping structure normalization")
        return content

    if sort_keys:
        # Sort top-level keys with messages last
        priority = ["model", "name", "description", "defaults"]
        sorted_data = _sort_dict(data, priority)

        # Sort message objects: role before content
        if "messages" in sorted_data:
            messages = sorted_data["messages"]
            if isinstance(messages, list):
                sorted_msgs = []
                for msg in messages:
                    if isinstance(msg, dict):
                        sorted_msgs.append(_sort_dict(msg, ["role", "content"]))
                    else:
                        sorted_msgs.append(msg)
                sorted_data["messages"] = sorted_msgs
    else:
        sorted_data = data

    # Dump with consistent formatting
    # Convert OrderedDicts to plain dicts recursively for clean YAML output
    result = yaml.dump(
        _to_plain_dict(sorted_data),
        default_flow_style=False,
        allow_unicode=True,
        indent=indent,
        sort_keys=False,  # We already sorted
        width=1000,  # Don't let yaml wrap
    )

    return result


def apply_json(content: str, indent: int = 2, sort_keys: bool = True) -> str:
    """Normalize JSON structure: sorted keys, consistent indentation."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        logger.warning("JSON parsing failed during structure normalization: %s", exc)
        return content
    if not isinstance(data, dict):
        logger.warning("JSON content is not an object; skipping structure normalization")
        return content

    if sort_keys:
        priority = ["model", "name", "description", "defaults"]
        sorted_data = _sort_dict(data, priority)

        if "messages" in sorted_data:
            messages = sorted_data["messages"]
            if isinstance(messages, list):
                sorted_msgs = []
                for msg in messages:
                    if isinstance(msg, dict):
                        sorted_msgs.append(_sort_dict(msg, ["role", "content"]))
                    else:
                        sorted_msgs.append(msg)
                sorted_data["messages"] = sorted_msgs
    else:
        sorted_data = data

    return json.dumps(dict(sorted_data), indent=indent, ensure_ascii=False) + "\n"


def apply(content: str, fmt: PromptFormat, indent: int = 2, sort_keys: bool = True) -> str:
    """Apply structure normalization for structured formats."""
    if fmt == PromptFormat.YAML:
        return apply_yaml(content, indent, sort_keys)
    elif fmt == PromptFormat.JSON:
        return apply_json(content, indent, sort_keys)
    return content
