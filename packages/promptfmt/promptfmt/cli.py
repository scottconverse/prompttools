"""CLI interface for promptfmt."""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.syntax import Syntax

from prompttools_core import parse_directory
from prompttools_core.models import PromptFormat

from promptfmt.formatter import FmtConfig, format_file

app = typer.Typer(
    name="promptfmt",
    help="Auto-formatter for LLM prompt files.",
    no_args_is_help=True,
)
console = Console()

_FORMAT_MAP: dict[str, str] = {
    ".txt": "text",
    ".md": "md",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
}


def _collect_files(path: Path) -> list[Path]:
    """Collect all prompt files from a path."""
    if path.is_file():
        return [path]
    elif path.is_dir():
        extensions = list(_FORMAT_MAP.keys())
        files = []
        for ext in extensions:
            files.extend(sorted(path.rglob(f"*{ext}")))
        return files
    return []


@app.command()
def format(
    path: Path = typer.Argument(..., help="File or directory to format"),
    check: bool = typer.Option(False, "--check", help="Check only, don't write"),
    diff: bool = typer.Option(False, "--diff", help="Show diff of changes"),
    delimiter_style: str = typer.Option("###", "--delimiter-style", help="Delimiter style: ###, ---, ===, ***, ~~~"),
    variable_style: str = typer.Option("double_brace", "--variable-style", help="Variable style: double_brace, single_brace, angle_bracket"),
    max_line_length: int = typer.Option(120, "--max-line-length", help="Maximum line length before wrapping (0 to disable)"),
    quiet: bool = typer.Option(False, "--quiet", "-q"),
) -> None:
    """Format prompt files."""
    config = FmtConfig(
        delimiter_style=delimiter_style,
        variable_style=variable_style,
        max_line_length=max_line_length,
    )

    files = _collect_files(path)
    if not files:
        if not quiet:
            console.print("[yellow]No prompt files found.[/yellow]")
        raise typer.Exit(0)

    changed_count = 0
    error_count = 0

    for file_path in files:
        try:
            result = format_file(file_path, config)
        except Exception as exc:
            if not quiet:
                console.print(f"[red]Error:[/red] {file_path}: {exc}")
            error_count += 1
            continue

        if result.error:
            console.print(f"[red]Error:[/red] {file_path}: {result.error}")
            error_count += 1
            continue

        if result.changed:
            changed_count += 1

            if diff:
                # Show unified diff
                orig_lines = result.original_content.splitlines(keepends=True)
                fmt_lines = result.formatted_content.splitlines(keepends=True)
                diff_lines = difflib.unified_diff(
                    orig_lines, fmt_lines,
                    fromfile=str(file_path),
                    tofile=str(file_path),
                )
                diff_text = "".join(diff_lines)
                if diff_text:
                    console.print(Syntax(diff_text, "diff"))

            if not check:
                # Write formatted content
                try:
                    file_path.write_text(result.formatted_content, encoding="utf-8")
                except OSError as exc:
                    console.print(
                        f"[red]Error:[/red] Failed to write {file_path}: {exc}"
                    )
                    error_count += 1
                    continue
                if not quiet:
                    console.print(f"  [green]formatted[/green] {file_path}")
            else:
                if not quiet:
                    console.print(f"  [yellow]would format[/yellow] {file_path}")
        else:
            if not quiet and not check:
                console.print(f"  [dim]unchanged[/dim] {file_path}")

    if not quiet:
        console.print(
            f"\n  {changed_count} file(s) {'would be ' if check else ''}formatted, "
            f"{error_count} error(s)"
        )

    if check and changed_count > 0:
        raise typer.Exit(1)
    if error_count > 0:
        raise typer.Exit(2)


@app.command()
def init() -> None:
    """Generate a default .promptfmt.yaml config file."""
    config_content = """# promptfmt configuration
delimiter_style: '###'
variable_style: double_brace
max_line_length: 120
wrap_style: soft
sort_metadata_keys: true
indent: 2
exclude:
  - 'vendor/**'
  - '*.generated.*'
"""
    config_path = Path(".promptfmt.yaml")
    if config_path.exists():
        console.print("[yellow].promptfmt.yaml already exists[/yellow]")
        raise typer.Exit(1)

    config_path.write_text(config_content, encoding="utf-8")
    console.print("[green]Created .promptfmt.yaml[/green]")


if __name__ == "__main__":
    app()
