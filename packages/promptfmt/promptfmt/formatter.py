"""Formatter pipeline orchestrator for promptfmt."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from prompttools_core import PromptFile, PromptFormat, ToolConfig, parse_file
from prompttools_core.parser import parse_stdin

from promptfmt.equivalence import is_equivalent
from promptfmt.rules import whitespace, delimiters, variables, wrapping, structure


_VALID_DELIMITER_STYLES = {"###", "---", "===", "***", "~~~"}
_VALID_VARIABLE_STYLES = {"double_brace", "single_brace", "angle_bracket"}


@dataclass
class FmtConfig:
    """Configuration for the formatter."""

    delimiter_style: str = "###"
    variable_style: str = "double_brace"
    max_line_length: int = 120
    wrap_style: str = "soft"
    sort_metadata_keys: bool = True
    indent: int = 2

    def __post_init__(self) -> None:
        if self.delimiter_style not in _VALID_DELIMITER_STYLES:
            raise ValueError(
                f"Invalid delimiter_style '{self.delimiter_style}'. "
                f"Valid options: {', '.join(sorted(_VALID_DELIMITER_STYLES))}"
            )
        if self.variable_style not in _VALID_VARIABLE_STYLES:
            raise ValueError(
                f"Invalid variable_style '{self.variable_style}'. "
                f"Valid options: {', '.join(sorted(_VALID_VARIABLE_STYLES))}"
            )


@dataclass
class FormattedResult:
    """Result of formatting a file."""

    path: Path
    original_content: str
    formatted_content: str
    changed: bool
    equivalent: bool
    error: Optional[str] = None


def format_content(
    content: str,
    fmt: PromptFormat,
    config: FmtConfig,
) -> str:
    """Apply all formatting rules to content.

    Pipeline order:
    1. Whitespace normalization
    2. Delimiter normalization
    3. Variable syntax normalization
    4. Line wrapping
    5. Structure normalization (YAML/JSON only)
    """
    # 1. Whitespace
    result = whitespace.apply(content)

    # 2. Delimiters
    result = delimiters.apply(result, style=config.delimiter_style)

    # 3. Variables
    result = variables.apply(result, style=config.variable_style)

    # 4. Line wrapping
    if config.max_line_length > 0:
        result = wrapping.apply(result, max_length=config.max_line_length)

    # 5. Structure (YAML/JSON only)
    if fmt in (PromptFormat.YAML, PromptFormat.JSON):
        result = structure.apply(
            result,
            fmt=fmt,
            indent=config.indent,
            sort_keys=config.sort_metadata_keys,
        )
        # Re-apply whitespace after structure normalization
        result = whitespace.apply(result)

    return result


def format_file(
    path: Path,
    config: Optional[FmtConfig] = None,
) -> FormattedResult:
    """Format a single prompt file.

    Parameters
    ----------
    path:
        Path to the prompt file.
    config:
        Formatting configuration. Uses defaults if None.

    Returns
    -------
    FormattedResult
        Contains original and formatted content, change status,
        and semantic equivalence check result.
    """
    if config is None:
        config = FmtConfig()

    # Parse original
    original = parse_file(path)
    original_content = original.raw_content

    # Determine format
    fmt = original.format

    # Apply formatting
    formatted_content = format_content(original_content, fmt, config)

    # Check if anything changed
    changed = formatted_content != original_content

    # Verify semantic equivalence
    equivalent = True
    error = None
    if changed:
        try:
            # Re-parse formatted content
            fmt_name_map = {
                PromptFormat.TEXT: "text",
                PromptFormat.MARKDOWN: "md",
                PromptFormat.YAML: "yaml",
                PromptFormat.JSON: "json",
            }
            formatted_pf = parse_stdin(formatted_content, fmt_name_map[fmt])
            equivalent = is_equivalent(original, formatted_pf)
            if not equivalent:
                error = "Formatting altered semantic content — aborting"
        except Exception as exc:
            equivalent = False
            error = f"Formatted content failed to re-parse: {exc}"

    return FormattedResult(
        path=path,
        original_content=original_content,
        formatted_content=formatted_content,
        changed=changed,
        equivalent=equivalent,
        error=error,
    )
