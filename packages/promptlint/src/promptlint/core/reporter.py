"""Output formatting for promptlint violations.

Supports text (rich-formatted), JSON, and GitHub Actions annotation
formats.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from promptlint.models import LintViolation, Severity

# ---------------------------------------------------------------------------
# Severity styling for text output
# ---------------------------------------------------------------------------

_SEVERITY_STYLE = {
    Severity.ERROR: ("bold red", "error"),
    Severity.WARNING: ("bold yellow", "warning"),
    Severity.INFO: ("bold blue", "info"),
}

_GITHUB_SEVERITY = {
    Severity.ERROR: "error",
    Severity.WARNING: "warning",
    Severity.INFO: "notice",
}


# ---------------------------------------------------------------------------
# Text format
# ---------------------------------------------------------------------------

def _format_text(violations: list[LintViolation], stats: bool = False) -> str:
    """Format violations as human-readable text.

    Produces output like::

        path/to/prompt.yaml:12  [error]  PL012  injection-vector-detected
          -> Content matches injection pattern: "ignore all previous instructions"
          *  Suggestion: Remove or sanitize instruction-override language.

    """
    if not violations:
        return "No violations found."

    lines: list[str] = []
    for v in violations:
        # Location string
        path_str = str(v.path)
        if v.line is not None:
            location = f"{path_str}:{v.line}"
        else:
            location = path_str

        sev_label = v.severity.value
        lines.append(f"{location}  [{sev_label}]  {v.rule_id}  {v.rule_name}")
        lines.append(f"  -> {v.message}")
        if v.suggestion:
            lines.append(f"  *  Suggestion: {v.suggestion}")
        lines.append("")

    # Summary line
    error_count = sum(1 for v in violations if v.severity == Severity.ERROR)
    warn_count = sum(1 for v in violations if v.severity == Severity.WARNING)
    info_count = sum(1 for v in violations if v.severity == Severity.INFO)
    file_count = len({str(v.path) for v in violations})
    lines.append(
        f"Found {len(violations)} violation(s) "
        f"({error_count} error, {warn_count} warning, {info_count} info) "
        f"in {file_count} file(s)."
    )

    # Optional stats table
    if stats:
        lines.append("")
        lines.extend(_format_stats_table(violations))

    return "\n".join(lines)


def _format_stats_table(violations: list[LintViolation]) -> list[str]:
    """Build a rule-hit summary table."""
    lines: list[str] = ["Rule Summary:"]
    counter: Counter[tuple[str, str, Severity]] = Counter()
    for v in violations:
        counter[(v.rule_id, v.rule_name, v.severity)] += 1

    # Sort by rule_id
    for (rule_id, rule_name, severity), count in sorted(counter.items()):
        sev_label = severity.value
        lines.append(f"  {rule_id}  {rule_name:<35s} {count} {sev_label}")

    return lines


# ---------------------------------------------------------------------------
# JSON format
# ---------------------------------------------------------------------------

def _format_json(violations: list[LintViolation]) -> str:
    """Format violations as a JSON array."""
    items = []
    for v in violations:
        items.append({
            "rule_id": v.rule_id,
            "rule_name": v.rule_name,
            "severity": v.severity.value,
            "path": str(v.path),
            "line": v.line,
            "message": v.message,
            "suggestion": v.suggestion,
            "fixable": v.fixable,
        })
    return json.dumps(items, indent=2)


# ---------------------------------------------------------------------------
# GitHub Actions format
# ---------------------------------------------------------------------------

def _format_github(violations: list[LintViolation]) -> str:
    """Format violations as GitHub Actions annotations.

    Produces lines like::

        ::error file=path/to/prompt.yaml,line=12,title=PL012::injection-vector-detected: ...
    """
    if not violations:
        return ""

    lines: list[str] = []
    for v in violations:
        gh_level = _GITHUB_SEVERITY.get(v.severity, "notice")
        parts = [f"file={v.path}"]
        if v.line is not None:
            parts.append(f"line={v.line}")
        parts.append(f"title={v.rule_id}")
        annotation = ",".join(parts)
        lines.append(f"::{gh_level} {annotation}::{v.rule_name}: {v.message}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def report(
    violations: list[LintViolation],
    format: str = "text",
    stats: bool = False,
) -> str:
    """Format a list of violations into the requested output format.

    Parameters
    ----------
    violations:
        Violations to format.
    format:
        Output format: ``text``, ``json``, or ``github``.
    stats:
        If ``True``, append a rule-hit summary table (text format only).

    Returns
    -------
    str
        The formatted report string.

    Raises
    ------
    ValueError
        If *format* is not recognized.
    """
    format = format.strip().lower()
    if format == "text":
        return _format_text(violations, stats=stats)
    elif format == "json":
        return _format_json(violations)
    elif format == "github":
        return _format_github(violations)
    else:
        raise ValueError(
            f"Unsupported output format '{format}'. Supported: text, json, github"
        )
