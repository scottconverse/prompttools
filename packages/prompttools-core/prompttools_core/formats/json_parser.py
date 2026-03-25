"""JSON prompt file parser."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from prompttools_core.errors import ParseError
from prompttools_core.models import Message, PromptFile, PromptFormat
from prompttools_core.formats._variables import extract_variables


def parse_json(path: Path, content: str) -> PromptFile:
    """Parse a JSON prompt file.

    Supports two layouts:
      - ``{"messages": [...]}`` — OpenAI chat format
      - ``{"prompt": "..."}`` — single prompt string
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Invalid JSON in {path}: {exc}") from exc

    metadata: dict[str, Any] = {}

    if isinstance(data, dict):
        if "messages" in data:
            messages_raw = data["messages"]
            if not isinstance(messages_raw, list):
                raise ParseError(
                    f"JSON prompt file {path}: 'messages' must be an array"
                )
            metadata = {k: v for k, v in data.items() if k not in ("messages", "defaults")}

            # Variable defaults
            variable_defaults: dict[str, str] = {}
            defaults_raw = data.get("defaults", {})
            if isinstance(defaults_raw, dict):
                variable_defaults = {str(k): str(v) for k, v in defaults_raw.items()}

            _VALID_ROLES = {"system", "user", "assistant", "tool"}

            messages: list[Message] = []
            for i, msg_raw in enumerate(messages_raw):
                if not isinstance(msg_raw, dict):
                    raise ParseError(
                        f"Each message in {path} must be an object "
                        f"with 'role' and 'content'"
                    )
                role = str(msg_raw.get("role", "user"))
                if role not in _VALID_ROLES:
                    raise ParseError(
                        f"Invalid role '{role}' in message {i + 1} of {path}. "
                        f"Valid roles: {', '.join(sorted(_VALID_ROLES))}"
                    )
                msg_content = str(msg_raw.get("content", ""))
                messages.append(
                    Message(role=role, content=msg_content, line_start=i + 1)
                )

            all_content = " ".join(m.content for m in messages)
            variables = extract_variables(all_content)
            return PromptFile(
                path=path.resolve(),
                format=PromptFormat.JSON,
                raw_content=content,
                messages=messages,
                variables=variables,
                variable_defaults=variable_defaults,
                metadata=metadata,
            )

        elif "prompt" in data:
            prompt_text = str(data["prompt"])
            metadata = {k: v for k, v in data.items() if k not in ("prompt", "defaults")}
            variable_defaults = {}
            defaults_raw = data.get("defaults", {})
            if isinstance(defaults_raw, dict):
                variable_defaults = {str(k): str(v) for k, v in defaults_raw.items()}
            variables = extract_variables(prompt_text)
            return PromptFile(
                path=path.resolve(),
                format=PromptFormat.JSON,
                raw_content=content,
                messages=[Message(role="user", content=prompt_text, line_start=1)],
                variables=variables,
                variable_defaults=variable_defaults,
                metadata=metadata,
            )

    raise ParseError(
        f"JSON prompt file {path} must contain a 'messages' array or 'prompt' string"
    )
