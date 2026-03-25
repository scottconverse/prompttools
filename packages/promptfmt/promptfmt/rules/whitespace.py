"""Whitespace normalization rules for promptfmt."""

from __future__ import annotations

import re


def apply(content: str) -> str:
    """Apply whitespace normalization rules.

    - Strip trailing whitespace from every line
    - Normalize line endings to LF
    - Remove leading blank lines at file start
    - Collapse 3+ consecutive blank lines to 2
    - Ensure file ends with exactly one newline
    """
    # Normalize line endings to LF
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    # Strip trailing whitespace from each line
    lines = content.split("\n")
    lines = [line.rstrip() for line in lines]

    # Remove leading blank lines
    while lines and lines[0] == "":
        lines.pop(0)

    # Collapse 3+ consecutive blank lines to 2
    result: list[str] = []
    blank_count = 0
    for line in lines:
        if line == "":
            blank_count += 1
            if blank_count <= 2:
                result.append(line)
        else:
            blank_count = 0
            result.append(line)

    # Ensure exactly one trailing newline
    # Remove trailing blank lines
    while result and result[-1] == "":
        result.pop()

    # Join and add final newline
    if result:
        return "\n".join(result) + "\n"
    return ""
