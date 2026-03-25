"""Typer CLI application for promptdiff.

Provides the ``promptdiff`` entry point for comparing two prompt files
and reporting differences in text, JSON, or Markdown format.
"""

from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from promptdiff.differ import diff_files
from promptdiff.reporter import format_json, format_markdown, format_text

# ---------------------------------------------------------------------------
# Console
# ---------------------------------------------------------------------------

_console = Console()
_err_console = Console(stderr=True)


class OutputFormat(str, Enum):
    """Supported output formats."""

    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"


# ---------------------------------------------------------------------------
# Version callback
# ---------------------------------------------------------------------------


def _version_callback(value: bool) -> None:
    if value:
        from promptdiff import __version__

        _console.print(f"promptdiff {__version__}")
        raise typer.Exit()


# ---------------------------------------------------------------------------
# Main command — single-command app (no subcommands needed)
# ---------------------------------------------------------------------------


def main(
    file_a: Path = typer.Argument(..., help="Path to the old prompt file"),
    file_b: Path = typer.Argument(..., help="Path to the new prompt file"),
    output_format: OutputFormat = typer.Option(
        OutputFormat.TEXT,
        "--format",
        "-f",
        help="Output format: text, json, markdown",
    ),
    exit_on_breaking: bool = typer.Option(
        False,
        "--exit-on-breaking",
        help="Exit with code 1 if breaking changes are found",
    ),
    token_detail: bool = typer.Option(
        False,
        "--token-detail",
        help="Show per-message token breakdowns",
    ),
    encoding: str = typer.Option(
        "cl100k_base",
        "--encoding",
        "-e",
        help="tiktoken encoding for token counting",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """Semantic diff for LLM prompt changes.

    Compare two prompt files and show structured diff with message-level
    changes, variable changes, token deltas, and breaking change classification.
    """
    try:
        result = diff_files(file_a, file_b, encoding=encoding)
    except FileNotFoundError as exc:
        _err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(2)
    except Exception as exc:
        _err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(2)

    if output_format == OutputFormat.TEXT:
        output = format_text(result, show_token_detail=token_detail)
        _console.print(output)
    elif output_format == OutputFormat.JSON:
        output = format_json(result)
        # Use print() to avoid Rich adding ANSI codes to raw JSON.
        print(output)
    elif output_format == OutputFormat.MARKDOWN:
        output = format_markdown(result)
        print(output)

    if exit_on_breaking and result.is_breaking:
        raise typer.Exit(1)


app = typer.Typer(
    name="promptdiff",
    help="Semantic diff for LLM prompt files.",
    add_completion=False,
    no_args_is_help=True,
)
app.command()(main)
