"""CLI interface for promptcost."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from prompttools_core import (
    get_profile,
    list_profiles,
    parse_directory,
    parse_file,
    parse_pipeline,
)

from promptcost.budget import check_budget
from promptcost.comparator import compare_models
from promptcost.estimator import estimate_file, estimate_pipeline
from promptcost.projector import project_cost

app = typer.Typer(
    name="promptcost",
    help="Token budget and cost estimator for LLM prompts.",
    no_args_is_help=True,
)
console = Console()


def _format_cost(cost: float) -> str:
    """Format a cost value for display."""
    if cost < 0.01:
        return f"${cost:.4f}"
    if cost >= 1000:
        return f"${cost:,.2f}"
    return f"${cost:.2f}"


@app.command()
def estimate(
    path: Path = typer.Argument(..., help="Prompt file or directory"),
    model: str = typer.Option("claude-4-sonnet", "--model", "-m", help="Model profile"),
    output_tokens: Optional[int] = typer.Option(None, "--output-tokens", help="Override output tokens"),
    volume: Optional[str] = typer.Option(None, "--project", help="Project at volume (e.g. 1000/day)"),
    compare: bool = typer.Option(False, "--compare", help="Compare across models"),
    models: Optional[str] = typer.Option(None, "--models", help="Comma-separated model list for comparison"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
) -> None:
    """Estimate costs for prompt files."""
    if output_tokens is not None and output_tokens <= 0:
        console.print("[red]Error:[/red] --output-tokens must be a positive integer")
        raise typer.Exit(2)

    if compare or models:
        model_list = models.split(",") if models else [
            "gpt-4o", "gpt-4o-mini", "claude-4-sonnet", "gemini-2.0-flash"
        ]
        if path.is_file():
            pf = parse_file(path)
            result = compare_models(pf, model_list, output_tokens)

            if format == "json":
                console.print_json(result.model_dump_json(indent=2))
                return

            table = Table(title=f"Cost Comparison: {path.name}")
            table.add_column("Model", style="cyan")
            table.add_column("Input $/Mtok", justify="right")
            table.add_column("Output $/Mtok", justify="right")
            table.add_column("Cost/Call", justify="right", style="green")
            table.add_column("Monthly @1K/day", justify="right")

            for m, est in result.estimates.items():
                profile = get_profile(m)
                table.add_row(
                    m,
                    f"${profile.input_price_per_mtok:.2f}" if profile else "?",
                    f"${profile.output_price_per_mtok:.2f}" if profile else "?",
                    _format_cost(est.total_cost),
                    _format_cost(est.total_cost * 1000 * 30),
                )

            console.print(table)
            console.print(
                f"\n[green]Cheapest:[/green] {result.cheapest} | "
                f"[red]Most expensive:[/red] {result.most_expensive} | "
                f"Savings: {_format_cost(result.savings_vs_most_expensive)}/call"
            )
        return

    # Single model estimation
    if path.is_file():
        pf = parse_file(path)
        est = estimate_file(pf, model, output_tokens)

        if format == "json":
            console.print_json(est.model_dump_json(indent=2))
            return

        console.print(f"\n  [bold]File:[/bold] {path.name}")
        console.print(f"  [bold]Model:[/bold] {model}")
        console.print(f"  [bold]Input tokens:[/bold] {est.input_tokens:,}")
        console.print(
            f"  [bold]Est. output tokens:[/bold] {est.estimated_output_tokens:,} "
            f"({est.output_estimation_method})"
        )
        console.print(f"  [bold]Cost per invocation:[/bold] {_format_cost(est.total_cost)}")

        if volume:
            try:
                proj = project_cost(est, volume)
            except ValueError:
                console.print(
                    "[red]Error:[/red] Invalid volume format. "
                    "Use: N/hour, N/day, N/week, or N/month"
                )
                raise typer.Exit(2)
            console.print(f"\n  [bold]Projections ({volume}):[/bold]")
            console.print(f"    Daily:   {_format_cost(proj.daily_cost)}")
            console.print(f"    Monthly: {_format_cost(proj.monthly_cost)}")
            console.print(f"    Annual:  {_format_cost(proj.annual_cost)}")

    elif path.is_dir():
        files = parse_directory(path)
        if not files:
            console.print("[yellow]No prompt files found.[/yellow]")
            raise typer.Exit(0)

        table = Table(title=f"Cost Estimates ({model})")
        table.add_column("File", style="cyan")
        table.add_column("Input Tokens", justify="right")
        table.add_column("Est. Output", justify="right")
        table.add_column("Cost/Call", justify="right", style="green")

        total_cost = 0.0
        for pf in files:
            est = estimate_file(pf, model, output_tokens)
            total_cost += est.total_cost
            table.add_row(
                pf.path.name,
                f"{est.input_tokens:,}",
                f"{est.estimated_output_tokens:,}",
                _format_cost(est.total_cost),
            )

        console.print(table)
        console.print(f"\n  [bold]Total per-call cost:[/bold] {_format_cost(total_cost)}")

        if volume:
            calls = int(volume.split("/")[0])
            monthly = total_cost * calls * 30
            console.print(f"  [bold]Monthly @{volume}:[/bold] {_format_cost(monthly)}")
    else:
        console.print(f"[red]Path not found: {path}[/red]")
        raise typer.Exit(2)


@app.command()
def budget(
    path: Path = typer.Argument(..., help="Prompt file or directory"),
    limit: float = typer.Option(..., "--limit", "-l", help="Per-invocation cost ceiling in USD"),
    model: str = typer.Option("claude-4-sonnet", "--model", "-m", help="Model profile"),
    output_tokens: Optional[int] = typer.Option(None, "--output-tokens"),
    format: str = typer.Option("text", "--format", "-f", help="Output format"),
) -> None:
    """Check prompt costs against a budget ceiling."""
    if limit <= 0:
        raise typer.BadParameter("Budget limit must be greater than 0", param_hint="--limit")

    if output_tokens is not None and output_tokens <= 0:
        raise typer.BadParameter("Output tokens must be a positive integer", param_hint="--output-tokens")

    if path.is_file():
        files = [parse_file(path)]
    elif path.is_dir():
        files = parse_directory(path)
    else:
        console.print(f"[red]Path not found: {path}[/red]")
        raise typer.Exit(2)

    estimates = [estimate_file(pf, model, output_tokens) for pf in files]
    results = check_budget(estimates, limit)

    any_over = False
    for r in results:
        status = "[red]OVER BUDGET[/red]" if r.over_budget else "[green]OK[/green]"
        if r.over_budget:
            any_over = True
        console.print(
            f"  {r.file_path.name}: {_format_cost(r.estimated_cost)} "
            f"(limit: {_format_cost(r.budget)}) {status}"
        )

    if any_over:
        raise typer.Exit(1)


@app.command()
def delta(
    old_path: Path = typer.Argument(..., help="Old prompt file"),
    new_path: Path = typer.Argument(..., help="New prompt file"),
    model: str = typer.Option("claude-4-sonnet", "--model", "-m"),
    volume: Optional[str] = typer.Option(None, "--volume"),
    output_tokens: Optional[int] = typer.Option(None, "--output-tokens"),
) -> None:
    """Show cost impact of a prompt change."""
    old_pf = parse_file(old_path)
    new_pf = parse_file(new_path)

    old_est = estimate_file(old_pf, model, output_tokens)
    new_est = estimate_file(new_pf, model, output_tokens)

    cost_change = new_est.total_cost - old_est.total_cost
    pct = (cost_change / old_est.total_cost * 100) if old_est.total_cost > 0 else 0

    console.print(f"\n  [bold]Cost Delta:[/bold] {old_path.name} -> {new_path.name}")
    console.print(f"  [bold]Model:[/bold] {model}")
    console.print(
        f"  Input tokens: {old_est.input_tokens:,} -> {new_est.input_tokens:,} "
        f"({new_est.input_tokens - old_est.input_tokens:+,})"
    )
    console.print(
        f"  Cost/call: {_format_cost(old_est.total_cost)} -> "
        f"{_format_cost(new_est.total_cost)} "
        f"({_format_cost(cost_change)}, {pct:+.1f}%)"
    )

    if volume:
        try:
            proj_old = project_cost(old_est, volume)
            proj_new = project_cost(new_est, volume)
        except ValueError:
            console.print(
                "[red]Error:[/red] Invalid volume format. "
                "Use: N/hour, N/day, N/week, or N/month"
            )
            raise typer.Exit(2)
        monthly_delta = proj_new.monthly_cost - proj_old.monthly_cost
        console.print(
            f"  Monthly @{volume}: {_format_cost(proj_old.monthly_cost)} -> "
            f"{_format_cost(proj_new.monthly_cost)} "
            f"({_format_cost(monthly_delta)}/month)"
        )


@app.command(name="models")
def list_models() -> None:
    """List all available model profiles with pricing."""
    profiles = list_profiles()

    table = Table(title="Available Model Profiles")
    table.add_column("Model", style="cyan")
    table.add_column("Provider")
    table.add_column("Context Window", justify="right")
    table.add_column("Input $/Mtok", justify="right")
    table.add_column("Output $/Mtok", justify="right")
    table.add_column("Encoding")

    for name, profile in sorted(profiles.items()):
        table.add_row(
            name,
            profile.provider,
            f"{profile.context_window:,}",
            f"${profile.input_price_per_mtok:.2f}" if profile.input_price_per_mtok else "—",
            f"${profile.output_price_per_mtok:.2f}" if profile.output_price_per_mtok else "—",
            profile.encoding,
        )

    console.print(table)


if __name__ == "__main__":
    app()
