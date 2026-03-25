"""CLI interface for promptvault."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table

from promptvault.lockfile import (
    generate_lockfile,
    read_lockfile,
    verify_lockfile,
    write_lockfile,
)
from promptvault.models import PackageManifest, QualityConfig
from promptvault.registry import LocalRegistry, _read_manifest
from promptvault.resolver import DependencyConflictError, resolve_dependencies

app = typer.Typer(
    name="promptvault",
    help="Version control and registry for prompt assets.",
    no_args_is_help=True,
)
console = Console()


def _get_registry(registry_path: Optional[Path]) -> LocalRegistry:
    """Create a LocalRegistry, optionally overriding the default path."""
    if registry_path:
        return LocalRegistry(registry_dir=registry_path)
    return LocalRegistry()


@app.command()
def init(
    directory: Path = typer.Argument(
        ".", help="Directory to scaffold the manifest in"
    ),
    name: str = typer.Option(
        "@my-org/my-prompts", "--name", "-n", help="Package name"
    ),
    description: str = typer.Option(
        "A prompt package", "--description", "-d", help="Package description"
    ),
    author: str = typer.Option(
        "Author", "--author", "-a", help="Package author"
    ),
) -> None:
    """Scaffold a new promptvault.yaml manifest."""
    directory = directory.resolve()
    manifest_path = directory / "promptvault.yaml"

    if manifest_path.exists():
        console.print(
            f"[yellow]promptvault.yaml already exists in {directory}[/yellow]"
        )
        raise typer.Exit(code=1)

    manifest_data = {
        "name": name,
        "version": "0.1.0",
        "description": description,
        "author": author,
        "license": "MIT",
        "model": None,
        "prompts": [],
        "dependencies": {},
        "quality": {"lint": "optional", "test": "optional", "format": "optional"},
    }

    directory.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        yaml.dump(manifest_data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    console.print(f"[green]Created promptvault.yaml in {directory}[/green]")


@app.command()
def publish(
    directory: Path = typer.Argument(
        ".", help="Directory containing promptvault.yaml"
    ),
    registry: Optional[Path] = typer.Option(
        None, "--registry", "-r", help="Override registry path"
    ),
    format: str = typer.Option(
        "text", "--format", "-f", help="Output format: text, json"
    ),
) -> None:
    """Publish a package to the local registry."""
    directory = directory.resolve()
    reg = _get_registry(registry)

    try:
        entry = reg.publish(directory)
    except FileNotFoundError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1)
    except ValueError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1)

    if format == "json":
        console.print(entry.model_dump_json(indent=2))
    else:
        console.print(f"[green]Published {entry.name}@{entry.latest_version}[/green]")
        console.print(f"  Prompts: {entry.total_prompts}")
        console.print(f"  Integrity: {entry.integrity[:16]}...")


@app.command()
def install(
    directory: Path = typer.Argument(
        ".", help="Directory containing promptvault.yaml"
    ),
    registry: Optional[Path] = typer.Option(
        None, "--registry", "-r", help="Override registry path"
    ),
    format: str = typer.Option(
        "text", "--format", "-f", help="Output format: text, json"
    ),
) -> None:
    """Install dependencies and generate a lockfile."""
    directory = directory.resolve()
    reg = _get_registry(registry)

    try:
        manifest = _read_manifest(directory)
    except FileNotFoundError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1)

    if not manifest.dependencies:
        console.print("[yellow]No dependencies to install.[/yellow]")
        return

    try:
        resolved = resolve_dependencies(manifest, reg)
    except DependencyConflictError as exc:
        console.print(f"[red]Dependency error: {exc}[/red]")
        raise typer.Exit(code=1)

    lockfile = generate_lockfile(manifest, resolved, reg)
    lockfile_path = directory / "promptvault.lock"
    write_lockfile(lockfile, lockfile_path)

    if format == "json":
        console.print(lockfile.model_dump_json(indent=2))
    else:
        console.print(f"[green]Installed {len(resolved)} dependencies[/green]")
        for dep_name, dep_version in resolved.items():
            console.print(f"  {dep_name}@{dep_version}")
        console.print(f"  Lockfile written to {lockfile_path}")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    registry: Optional[Path] = typer.Option(
        None, "--registry", "-r", help="Override registry path"
    ),
    format: str = typer.Option(
        "text", "--format", "-f", help="Output format: text, json"
    ),
) -> None:
    """Search the registry catalog."""
    reg = _get_registry(registry)
    results = reg.search(query)

    if not results:
        console.print(f"[yellow]No packages matching '{query}'[/yellow]")
        return

    if format == "json":
        console.print(json.dumps([r.model_dump() for r in results], indent=2))
    else:
        table = Table(title=f"Search results for '{query}'")
        table.add_column("Name", style="cyan")
        table.add_column("Version", style="green")
        table.add_column("Description")
        table.add_column("Prompts", justify="right")

        for entry in results:
            table.add_row(
                entry.name,
                entry.latest_version,
                entry.description,
                str(entry.total_prompts),
            )
        console.print(table)


@app.command()
def info(
    package: str = typer.Argument(..., help="Package name"),
    registry: Optional[Path] = typer.Option(
        None, "--registry", "-r", help="Override registry path"
    ),
    format: str = typer.Option(
        "text", "--format", "-f", help="Output format: text, json"
    ),
) -> None:
    """Show details for a specific package."""
    reg = _get_registry(registry)

    try:
        entry = reg.info(package)
    except KeyError:
        console.print(f"[red]Package '{package}' not found[/red]")
        raise typer.Exit(code=1)

    if format == "json":
        console.print(entry.model_dump_json(indent=2))
    else:
        console.print(f"[bold]{entry.name}[/bold]")
        console.print(f"  Latest: {entry.latest_version}")
        console.print(f"  Versions: {', '.join(entry.versions)}")
        console.print(f"  Description: {entry.description}")
        console.print(f"  Prompts: {entry.total_prompts}")
        console.print(f"  Published: {entry.published_at}")
        if entry.model:
            console.print(f"  Model: {entry.model}")


@app.command(name="list")
def list_packages(
    registry: Optional[Path] = typer.Option(
        None, "--registry", "-r", help="Override registry path"
    ),
    format: str = typer.Option(
        "text", "--format", "-f", help="Output format: text, json"
    ),
) -> None:
    """List all packages in the registry."""
    reg = _get_registry(registry)
    packages = reg.list_packages()

    if not packages:
        console.print("[yellow]No packages in registry[/yellow]")
        return

    if format == "json":
        console.print(json.dumps([p.model_dump() for p in packages], indent=2))
    else:
        table = Table(title="Registry packages")
        table.add_column("Name", style="cyan")
        table.add_column("Version", style="green")
        table.add_column("Description")
        table.add_column("Prompts", justify="right")

        for pkg in packages:
            table.add_row(
                pkg.name,
                pkg.latest_version,
                pkg.description,
                str(pkg.total_prompts),
            )
        console.print(table)


@app.command()
def verify(
    directory: Path = typer.Argument(
        ".", help="Directory containing promptvault.lock"
    ),
    registry: Optional[Path] = typer.Option(
        None, "--registry", "-r", help="Override registry path"
    ),
    format: str = typer.Option(
        "text", "--format", "-f", help="Output format: text, json"
    ),
) -> None:
    """Verify lockfile integrity against the registry."""
    directory = directory.resolve()
    reg = _get_registry(registry)
    lockfile_path = directory / "promptvault.lock"

    try:
        lockfile = read_lockfile(lockfile_path)
    except FileNotFoundError:
        console.print("[red]No promptvault.lock found[/red]")
        raise typer.Exit(code=1)

    valid = verify_lockfile(lockfile, reg)

    if format == "json":
        console.print(json.dumps({"valid": valid}))
    else:
        if valid:
            console.print("[green]Lockfile verification passed[/green]")
        else:
            console.print("[red]Lockfile verification failed[/red]")
            raise typer.Exit(code=1)
