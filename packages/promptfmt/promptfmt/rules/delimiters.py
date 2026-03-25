"""Delimiter normalization rules for promptfmt."""

from __future__ import annotations

import re

# Patterns that match section delimiters (not inside code blocks)
_DELIMITER_PATTERNS = [
    re.compile(r"^-{3,}\s*$"),       # --- or ----
    re.compile(r"^={3,}\s*$"),       # === or ====
    re.compile(r"^\*{3,}\s*$"),      # *** or ****
    re.compile(r"^~{3,}\s*$"),       # ~~~ or ~~~~
    re.compile(r"^#{1,6}\s+.+$"),    # ### Heading
]

# Code block markers
_CODE_BLOCK_RE = re.compile(r"^```")


def apply(content: str, style: str = "###") -> str:
    """Normalize section delimiters to a single consistent style.

    Parameters
    ----------
    content:
        The file content.
    style:
        Target delimiter style: ``"###"``, ``"---"``, ``"==="``, ``"***"``, ``"~~~"``.
    """
    lines = content.split("\n")
    result: list[str] = []
    in_code_block = False

    for line in lines:
        # Track code block state
        if _CODE_BLOCK_RE.match(line):
            in_code_block = not in_code_block
            result.append(line)
            continue

        if in_code_block:
            result.append(line)
            continue

        # Check if this is a delimiter line
        stripped = line.strip()

        # Pure delimiter lines (---, ===, ***, ~~~)
        if re.match(r"^-{3,}$", stripped):
            result.append(style if not style.startswith("#") else style)
            continue
        if re.match(r"^={3,}$", stripped):
            result.append(style if not style.startswith("#") else style)
            continue
        if re.match(r"^\*{3,}$", stripped):
            result.append(style if not style.startswith("#") else style)
            continue
        if re.match(r"^~{3,}$", stripped):
            result.append(style if not style.startswith("#") else style)
            continue

        # Heading-style delimiters: ### Title -> normalized
        if style.startswith("#"):
            # Convert other delimiters to heading style
            # (This only applies if the target is heading-style)
            pass

        result.append(line)

    return "\n".join(result)
