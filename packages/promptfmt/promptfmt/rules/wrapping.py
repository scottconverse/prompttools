"""Line wrapping rules for promptfmt."""

from __future__ import annotations

import re

# Patterns that should not be broken
_URL_RE = re.compile(r"https?://\S+")
_VAR_RE = re.compile(r"\{\{[^}]+\}\}|\{[^}]+\}|<\w+>")
_CODE_BLOCK_RE = re.compile(r"^```")
_INLINE_CODE_RE = re.compile(r"`[^`]+`")


def _wrap_line(line: str, max_length: int) -> list[str]:
    """Wrap a single line respecting word boundaries and special tokens."""
    if len(line) <= max_length:
        return [line]

    # Don't wrap lines that are URLs, code, or delimiters
    stripped = line.strip()
    if _URL_RE.match(stripped):
        return [line]
    if stripped.startswith("|"):  # table row
        return [line]
    if stripped.startswith("#"):  # heading
        return [line]

    # Preserve leading whitespace
    indent = len(line) - len(line.lstrip())
    indent_str = line[:indent]

    words = line.strip().split()
    if not words:
        return [line]

    lines: list[str] = []
    current_line = indent_str

    for word in words:
        test_line = f"{current_line} {word}" if current_line.strip() else f"{indent_str}{word}"
        if len(test_line) <= max_length or not current_line.strip():
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = f"{indent_str}{word}"

    if current_line.strip():
        lines.append(current_line)

    return lines


def apply(content: str, max_length: int = 120) -> str:
    """Wrap lines exceeding max_length at word boundaries.

    Parameters
    ----------
    content:
        The file content.
    max_length:
        Maximum line length. 0 = disabled.
    """
    if max_length <= 0:
        return content

    lines = content.split("\n")
    result: list[str] = []
    in_code_block = False

    for line in lines:
        if _CODE_BLOCK_RE.match(line):
            in_code_block = not in_code_block
            result.append(line)
            continue

        if in_code_block:
            result.append(line)
            continue

        result.extend(_wrap_line(line, max_length))

    return "\n".join(result)
