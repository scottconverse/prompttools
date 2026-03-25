"""YAML prompt file parser."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from prompttools_core.errors import ParseError
from prompttools_core.models import Message, PromptFile, PromptFormat
from prompttools_core.formats._variables import extract_variables


def parse_yaml(path: Path, content: str) -> PromptFile:
    """Parse a YAML prompt file expecting a ``messages`` list."""
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ParseError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ParseError(
            f"YAML prompt file {path} must contain a mapping at the top level"
        )

    messages_raw = data.get("messages")
    if not isinstance(messages_raw, list):
        raise ParseError(
            f"YAML prompt file {path} must contain a 'messages' list"
        )

    # Metadata is everything except "messages" and "defaults"
    metadata = {k: v for k, v in data.items() if k not in ("messages", "defaults")}

    # Variable defaults
    variable_defaults: dict[str, str] = {}
    defaults_raw = data.get("defaults", {})
    if isinstance(defaults_raw, dict):
        variable_defaults = {str(k): str(v) for k, v in defaults_raw.items()}

    messages: list[Message] = []
    # Approximate line numbers by scanning content for role keys
    content_lines = content.split("\n")
    role_line_indices: list[int] = []
    for idx, line in enumerate(content_lines, start=1):
        stripped = line.strip()
        if stripped.startswith("- role:") or stripped.startswith("role:"):
            role_line_indices.append(idx)

    _VALID_ROLES = {"system", "user", "assistant", "tool"}

    for i, msg_raw in enumerate(messages_raw):
        if not isinstance(msg_raw, dict):
            raise ParseError(
                f"Each message in {path} must be a mapping with 'role' and 'content'"
            )
        role = str(msg_raw.get("role", "user"))
        if role not in _VALID_ROLES:
            raise ParseError(
                f"Invalid role '{role}' in message {i + 1} of {path}. "
                f"Valid roles: {', '.join(sorted(_VALID_ROLES))}"
            )
        msg_content = str(msg_raw.get("content", ""))
        line_start = role_line_indices[i] if i < len(role_line_indices) else 1
        messages.append(Message(role=role, content=msg_content, line_start=line_start))

    all_content = " ".join(m.content for m in messages)
    variables = extract_variables(all_content)

    return PromptFile(
        path=path.resolve(),
        format=PromptFormat.YAML,
        raw_content=content,
        messages=messages,
        variables=variables,
        variable_defaults=variable_defaults,
        metadata=metadata,
    )
