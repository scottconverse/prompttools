"""Plain text prompt parser."""

from __future__ import annotations

from pathlib import Path

from prompttools_core.models import Message, PromptFile, PromptFormat
from prompttools_core.formats._variables import extract_variables


def parse_text(path: Path, content: str) -> PromptFile:
    """Parse a plain text file as a single user message."""
    variables = extract_variables(content)
    return PromptFile(
        path=path.resolve(),
        format=PromptFormat.TEXT,
        raw_content=content,
        messages=[
            Message(role="user", content=content, line_start=1),
        ],
        variables=variables,
    )
