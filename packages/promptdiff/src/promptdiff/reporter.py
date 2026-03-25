"""Output formatters for promptdiff.

Supports text (Rich terminal), JSON, and Markdown output formats.
"""

from __future__ import annotations

import json
from typing import Any

from promptdiff.models import (
    ChangeStatus,
    PromptDiff,
)


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def format_json(diff: PromptDiff) -> str:
    """Format a PromptDiff as JSON.

    Parameters
    ----------
    diff:
        The prompt diff to format.

    Returns
    -------
    str
        JSON string.
    """
    return diff.model_dump_json(indent=2)


# ---------------------------------------------------------------------------
# Text output (Rich-ready, but returns plain strings with markup)
# ---------------------------------------------------------------------------

_STATUS_STYLE: dict[ChangeStatus, tuple[str, str]] = {
    ChangeStatus.ADDED: ("[green]+[/green]", "green"),
    ChangeStatus.REMOVED: ("[red]-[/red]", "red"),
    ChangeStatus.MODIFIED: ("[yellow]~[/yellow]", "yellow"),
    ChangeStatus.UNCHANGED: (" ", "dim"),
}


def format_text(diff: PromptDiff, show_token_detail: bool = False) -> str:
    """Format a PromptDiff as rich-markup terminal text.

    Parameters
    ----------
    diff:
        The prompt diff to format.
    show_token_detail:
        If True, include per-message token breakdowns.

    Returns
    -------
    str
        Text with Rich markup suitable for Console.print().
    """
    lines: list[str] = []

    # Header
    lines.append("")
    lines.append(f"[bold]Prompt Diff:[/bold] {diff.file_path}")
    lines.append(f"  old: {diff.old_hash[:12]}  new: {diff.new_hash[:12]}")
    lines.append("")

    # Breaking changes summary
    if diff.is_breaking:
        lines.append(
            f"[bold red]BREAKING CHANGES ({len(diff.breaking_changes)}):[/bold red]"
        )
        for bc in diff.breaking_changes:
            severity_color = {"high": "red", "medium": "yellow", "low": "blue"}.get(
                bc.severity, "white"
            )
            lines.append(
                f"  [{severity_color}]{bc.severity.upper()}[/{severity_color}] "
                f"[{bc.category}] {bc.description}"
            )
        lines.append("")
    else:
        lines.append("[green]No breaking changes detected.[/green]")
        lines.append("")

    # Token summary
    td = diff.token_delta
    delta_str = f"+{td.delta}" if td.delta > 0 else str(td.delta)
    pct_str = f"+{td.percent_change}%" if td.percent_change > 0 else f"{td.percent_change}%"
    delta_color = "red" if td.delta > 0 else "green" if td.delta < 0 else "dim"
    lines.append("[bold]Token Delta:[/bold]")
    lines.append(
        f"  {td.old_total} -> {td.new_total} "
        f"([{delta_color}]{delta_str}[/{delta_color}], {pct_str})"
    )
    lines.append("")

    # Message diffs
    msg_changes = [m for m in diff.message_diffs if m.status != ChangeStatus.UNCHANGED]
    if msg_changes:
        lines.append(f"[bold]Messages ({len(msg_changes)} changed):[/bold]")
        for md in diff.message_diffs:
            marker, color = _STATUS_STYLE[md.status]
            if md.status == ChangeStatus.UNCHANGED and not show_token_detail:
                continue
            lines.append(f"  {marker} [{color}]{md.role}[/{color}]")
            for change in md.changes:
                lines.append(f"      {change}")
            if show_token_detail and md.token_delta != 0:
                sign = "+" if md.token_delta > 0 else ""
                lines.append(f"      tokens: {sign}{md.token_delta}")
            if md.content_diff and md.status == ChangeStatus.MODIFIED:
                for dl in md.content_diff.splitlines()[:10]:
                    if dl.startswith("+") and not dl.startswith("+++"):
                        lines.append(f"      [green]{dl}[/green]")
                    elif dl.startswith("-") and not dl.startswith("---"):
                        lines.append(f"      [red]{dl}[/red]")
                    else:
                        lines.append(f"      {dl}")
        lines.append("")

    # Variable diffs
    var_changes = [v for v in diff.variable_diffs if v.status != ChangeStatus.UNCHANGED]
    if var_changes:
        lines.append(f"[bold]Variables ({len(var_changes)} changed):[/bold]")
        for vd in var_changes:
            marker, color = _STATUS_STYLE[vd.status]
            breaking_tag = " [red](BREAKING)[/red]" if vd.is_breaking else ""
            lines.append(f"  {marker} [{color}]{vd.name}[/{color}]{breaking_tag}")
            if vd.status == ChangeStatus.ADDED and vd.new_default is not None:
                lines.append(f"      default: {vd.new_default!r}")
            elif vd.status == ChangeStatus.MODIFIED:
                lines.append(
                    f"      default: {vd.old_default!r} -> {vd.new_default!r}"
                )
        lines.append("")

    # Metadata diffs
    meta_changes = [m for m in diff.metadata_diffs if m.status != ChangeStatus.UNCHANGED]
    if meta_changes:
        lines.append(f"[bold]Metadata ({len(meta_changes)} changed):[/bold]")
        for md in meta_changes:
            marker, color = _STATUS_STYLE[md.status]
            lines.append(f"  {marker} [{color}]{md.key}[/{color}]")
            if md.status == ChangeStatus.ADDED:
                lines.append(f"      value: {md.new_value!r}")
            elif md.status == ChangeStatus.REMOVED:
                lines.append(f"      was: {md.old_value!r}")
            elif md.status == ChangeStatus.MODIFIED:
                lines.append(
                    f"      {md.old_value!r} -> {md.new_value!r}"
                )
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Markdown output (for GitHub PR comments)
# ---------------------------------------------------------------------------

_STATUS_EMOJI: dict[ChangeStatus, str] = {
    ChangeStatus.ADDED: "+",
    ChangeStatus.REMOVED: "-",
    ChangeStatus.MODIFIED: "~",
    ChangeStatus.UNCHANGED: " ",
}


def format_markdown(diff: PromptDiff) -> str:
    """Format a PromptDiff as Markdown.

    Parameters
    ----------
    diff:
        The prompt diff to format.

    Returns
    -------
    str
        Markdown string suitable for GitHub PR comments.
    """
    lines: list[str] = []

    # Header
    lines.append(f"## Prompt Diff: `{diff.file_path}`")
    lines.append("")
    lines.append(f"**Old:** `{diff.old_hash[:12]}` | **New:** `{diff.new_hash[:12]}`")
    lines.append("")

    # Breaking changes
    if diff.is_breaking:
        lines.append(
            f"### Breaking Changes ({len(diff.breaking_changes)})"
        )
        lines.append("")
        for bc in diff.breaking_changes:
            severity_badge = {
                "high": "**HIGH**",
                "medium": "MEDIUM",
                "low": "low",
            }.get(bc.severity, bc.severity)
            lines.append(
                f"- {severity_badge} [{bc.category}]: {bc.description}"
            )
        lines.append("")
    else:
        lines.append("No breaking changes detected.")
        lines.append("")

    # Token delta
    td = diff.token_delta
    delta_str = f"+{td.delta}" if td.delta > 0 else str(td.delta)
    pct_str = f"+{td.percent_change}%" if td.percent_change > 0 else f"{td.percent_change}%"
    lines.append("### Token Delta")
    lines.append("")
    lines.append(f"| Old | New | Delta | Change |")
    lines.append(f"|-----|-----|-------|--------|")
    lines.append(f"| {td.old_total} | {td.new_total} | {delta_str} | {pct_str} |")
    lines.append("")

    # Messages
    msg_changes = [m for m in diff.message_diffs if m.status != ChangeStatus.UNCHANGED]
    if msg_changes:
        lines.append(f"### Messages ({len(msg_changes)} changed)")
        lines.append("")
        for md in msg_changes:
            status_marker = _STATUS_EMOJI[md.status]
            lines.append(f"- `{status_marker}` **{md.role}**: {md.status.value}")
            for change in md.changes:
                lines.append(f"  - {change}")
            if md.content_diff:
                lines.append("")
                lines.append("  ```diff")
                for dl in md.content_diff.splitlines()[:15]:
                    lines.append(f"  {dl}")
                lines.append("  ```")
        lines.append("")

    # Variables
    var_changes = [v for v in diff.variable_diffs if v.status != ChangeStatus.UNCHANGED]
    if var_changes:
        lines.append(f"### Variables ({len(var_changes)} changed)")
        lines.append("")
        for vd in var_changes:
            status_marker = _STATUS_EMOJI[vd.status]
            breaking = " **(BREAKING)**" if vd.is_breaking else ""
            lines.append(f"- `{status_marker}` `{vd.name}`: {vd.status.value}{breaking}")
        lines.append("")

    # Metadata
    meta_changes = [m for m in diff.metadata_diffs if m.status != ChangeStatus.UNCHANGED]
    if meta_changes:
        lines.append(f"### Metadata ({len(meta_changes)} changed)")
        lines.append("")
        for md in meta_changes:
            status_marker = _STATUS_EMOJI[md.status]
            lines.append(f"- `{status_marker}` `{md.key}`: {md.status.value}")
        lines.append("")

    return "\n".join(lines)
