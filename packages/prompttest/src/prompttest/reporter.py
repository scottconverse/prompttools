"""Output formatters for prompttest reports.

Supports text (Rich colored terminal), JSON, and JUnit XML output.
"""

from __future__ import annotations

import json
from xml.etree.ElementTree import Element, SubElement, tostring

from prompttest.models import AssertionResult, PromptTestReport, PromptTestStatus


def format_text(report: PromptTestReport) -> str:
    """Format a test report as Rich-compatible colored terminal output.

    Parameters
    ----------
    report:
        The test report to format.

    Returns
    -------
    str
        Rich markup string for console display.
    """
    lines: list[str] = []
    lines.append("")

    for suite_data in report.suites:
        suite_name = suite_data["suite_name"]
        prompt_path = suite_data["prompt_path"]
        results = suite_data["results"]

        lines.append(f"[bold]Suite:[/bold] {suite_name}")
        lines.append(f"[dim]Prompt:[/dim] {prompt_path}")
        lines.append("")

        for r in results:
            status = r["status"]
            name = r["test_name"]
            message = r["message"]
            duration = r.get("duration_ms", 0)

            if status == "passed":
                icon = "[green]PASS[/green]"
            elif status == "failed":
                icon = "[red]FAIL[/red]"
            elif status == "error":
                icon = "[yellow]ERR [/yellow]"
            elif status == "skipped":
                icon = "[dim]SKIP[/dim]"
            else:
                icon = "[dim]?   [/dim]"

            lines.append(f"  {icon}  {name}")
            if status in ("failed", "error"):
                lines.append(f"         {message}")
            if duration > 0:
                lines.append(f"         [dim]({duration:.1f}ms)[/dim]")

        lines.append("")

    # Summary
    lines.append("[bold]Results:[/bold]")
    parts = []
    if report.passed:
        parts.append(f"[green]{report.passed} passed[/green]")
    if report.failed:
        parts.append(f"[red]{report.failed} failed[/red]")
    if report.errors:
        parts.append(f"[yellow]{report.errors} errors[/yellow]")
    if report.skipped:
        parts.append(f"[dim]{report.skipped} skipped[/dim]")

    if parts:
        lines.append(f"  {', '.join(parts)} ({report.total} total)")
    else:
        lines.append(f"  0 tests ({report.total} total)")
    lines.append(f"  [dim]Duration: {report.duration_ms:.0f}ms[/dim]")
    lines.append("")

    return "\n".join(lines)


def format_json(report: PromptTestReport) -> str:
    """Format a test report as JSON.

    Parameters
    ----------
    report:
        The test report to format.

    Returns
    -------
    str
        Pretty-printed JSON string.
    """
    data = {
        "total": report.total,
        "passed": report.passed,
        "failed": report.failed,
        "errors": report.errors,
        "skipped": report.skipped,
        "duration_ms": report.duration_ms,
        "suites": report.suites,
    }
    return json.dumps(data, indent=2, default=str)


def format_junit(report: PromptTestReport) -> str:
    """Format a test report as JUnit XML for CI integration.

    Parameters
    ----------
    report:
        The test report to format.

    Returns
    -------
    str
        JUnit-compatible XML string.
    """
    testsuites = Element("testsuites")
    testsuites.set("tests", str(report.total))
    testsuites.set("failures", str(report.failed))
    testsuites.set("errors", str(report.errors))
    testsuites.set("skipped", str(report.skipped))
    testsuites.set("time", f"{report.duration_ms / 1000:.3f}")

    for suite_data in report.suites:
        suite_name = suite_data["suite_name"]
        results = suite_data["results"]

        suite_el = SubElement(testsuites, "testsuite")
        suite_el.set("name", suite_name)
        suite_el.set("tests", str(len(results)))

        suite_failures = sum(1 for r in results if r["status"] == "failed")
        suite_errors = sum(1 for r in results if r["status"] == "error")
        suite_skipped = sum(1 for r in results if r["status"] == "skipped")
        suite_time = sum(r.get("duration_ms", 0) for r in results) / 1000

        suite_el.set("failures", str(suite_failures))
        suite_el.set("errors", str(suite_errors))
        suite_el.set("skipped", str(suite_skipped))
        suite_el.set("time", f"{suite_time:.3f}")

        for r in results:
            tc_el = SubElement(suite_el, "testcase")
            tc_el.set("name", r["test_name"])
            tc_el.set("classname", f"{suite_name}.{r['assert_type']}")
            tc_el.set("time", f"{r.get('duration_ms', 0) / 1000:.3f}")

            status = r["status"]
            if status == "failed":
                failure = SubElement(tc_el, "failure")
                failure.set("message", r["message"])
                failure.set("type", r["assert_type"])
                details = []
                if r.get("expected") is not None:
                    details.append(f"Expected: {r['expected']}")
                if r.get("actual") is not None:
                    details.append(f"Actual: {r['actual']}")
                failure.text = "\n".join(details) if details else r["message"]
            elif status == "error":
                error = SubElement(tc_el, "error")
                error.set("message", r["message"])
                error.set("type", "AssertionError")
                error.text = r["message"]
            elif status == "skipped":
                skipped_el = SubElement(tc_el, "skipped")
                skipped_el.set("message", r["message"])

    xml_bytes = tostring(testsuites, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_bytes}'
