"""Markdown prompt parser with YAML frontmatter support."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from prompttools_core.models import Message, PromptFile, PromptFormat
from prompttools_core.formats._variables import extract_variables

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_markdown(path: Path, content: str) -> PromptFile:
    """Parse a Markdown file, extracting optional YAML frontmatter."""
    metadata: dict[str, Any] = {}
    body = content
    body_start_line = 1
    variable_defaults: dict[str, str] = {}

    fm_match = _FRONTMATTER_RE.match(content)
    if fm_match:
        fm_text = fm_match.group(1)
        parsed = yaml.safe_load(fm_text)
        if isinstance(parsed, dict):
            metadata = parsed
            # Extract variable defaults from frontmatter
            defaults = metadata.get("defaults", {})
            if isinstance(defaults, dict):
                variable_defaults = {str(k): str(v) for k, v in defaults.items()}
        body = content[fm_match.end():]
        body_start_line = content[: fm_match.end()].count("\n") + 1

    variables = extract_variables(body)
    return PromptFile(
        path=path.resolve(),
        format=PromptFormat.MARKDOWN,
        raw_content=content,
        messages=[
            Message(role="user", content=body, line_start=body_start_line),
        ],
        variables=variables,
        variable_defaults=variable_defaults,
        metadata=metadata,
    )
