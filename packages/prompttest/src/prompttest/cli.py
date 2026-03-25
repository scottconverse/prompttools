"""CLI interface for prompttest."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from prompttest.reporter import format_json, format_junit, format_text
from prompttest.runner import run_test_directory, run_test_file

app = typer.Typer(
    name="prompttest",
    help="Test framework for LLM prompt files.",
    no_args_is_help=True,
)
console = Console()


class OutputFormat(str, Enum):
    """Supported output formats."""

    TEXT = "text"
    JSON = "json"
    JUNIT = "junit"


@app.command()
def run(
    path: Path = typer.Argument(..., help="Test file or directory to run"),
    output_format: OutputFormat = typer.Option(
        OutputFormat.TEXT, "--format", "-f", help="Output format: text, json, junit"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Override model for cost/token assertions"
    ),
    fail_fast: bool = typer.Option(
        False, "--fail-fast", help="Stop after first failure"
    ),
    pattern: str = typer.Option(
        "test_*.yaml", "--pattern", "-p", help="Glob pattern for test files"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed output for each test"
    ),
) -> None:
    """Run prompt tests from a file or directory."""
    path = Path(path)

    if not path.exists():
        console.print(f"[red]Path not found: {path}[/red]")
        raise typer.Exit(2)

    if path.is_file():
        report = run_test_file(path, fail_fast=fail_fast, model_override=model)
    else:
        report = run_test_directory(
            path, fail_fast=fail_fast, pattern=pattern, model_override=model
        )

    if report.total == 0:
        console.print("[yellow]No tests found.[/yellow]")
        raise typer.Exit(0)

    # Format and display
    if output_format == OutputFormat.JSON:
        output = format_json(report)
        console.print_json(output)
    elif output_format == OutputFormat.JUNIT:
        output = format_junit(report)
        console.print(output, highlight=False)
    else:
        output = format_text(report)
        console.print(output)

    # Exit with error code if any tests failed or errored
    if report.failed > 0 or report.errors > 0:
        raise typer.Exit(1)


@app.command()
def init() -> None:
    """Create an example test file in the current directory."""
    example_content = """\
# Example prompttest file
# See https://github.com/scottconverse/prompttools for documentation
suite: example-tests
prompt: prompts/greeting.yaml
model: gpt-4o

tests:
  - name: has-system-message
    assert: has_role
    role: system

  - name: token-count-reasonable
    assert: max_tokens
    max: 2048

  - name: contains-greeting-instruction
    assert: contains
    text: "greet the user"

  - name: no-injection-risk
    assert: not_contains
    text: "ignore previous instructions"

  - name: format-is-valid
    assert: valid_format

  - name: cost-under-budget
    assert: max_cost
    max: 0.05
    model: gpt-4o
"""
    output_path = Path("test_example.yaml")
    if output_path.exists():
        console.print(f"[yellow]{output_path} already exists[/yellow]")
        raise typer.Exit(1)

    output_path.write_text(example_content, encoding="utf-8")
    console.print(f"[green]Created {output_path}[/green]")
    console.print("[dim]Edit the 'prompt' path and tests to match your project.[/dim]")


if __name__ == "__main__":
    app()
