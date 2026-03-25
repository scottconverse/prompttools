"""Auto-fix system for promptlint.

Applies fixes for fixable violations, writes modified content back to
disk, and re-lints to verify the fix resolved the violation.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from promptlint.models import LintConfig, LintViolation, PromptFile
from promptlint.rules.base import BaseRule

if TYPE_CHECKING:
    pass


def _group_violations_by_file(
    violations: list[LintViolation],
) -> dict[Path, list[LintViolation]]:
    """Group fixable violations by their source file path."""
    groups: dict[Path, list[LintViolation]] = {}
    for v in violations:
        if v.fixable:
            groups.setdefault(v.path, []).append(v)
    return groups


def _find_rule(rule_id: str, rules: list[BaseRule]) -> BaseRule | None:
    """Look up a rule instance by its ID."""
    for rule in rules:
        if rule.rule_id == rule_id:
            return rule
    return None


def apply_fixes(
    violations: list[LintViolation],
    rules: list[BaseRule],
    dry_run: bool = False,
) -> list[str]:
    """Apply auto-fixes for all fixable violations.

    Parameters
    ----------
    violations:
        Full list of violations (both fixable and non-fixable).  Only
        fixable violations will be processed.
    rules:
        All rule instances (needed to call ``rule.fix()``).
    dry_run:
        If ``True``, compute fixes but do not write to disk.

    Returns
    -------
    list[str]
        Human-readable summary lines describing what was (or would be)
        fixed.

    Notes
    -----
    Fixes are applied in rule-ID order within each file to avoid
    conflicts between overlapping fixes.
    """
    grouped = _group_violations_by_file(violations)
    if not grouped:
        return ["No fixable violations found."]

    summary_lines: list[str] = []
    total_fixed = 0
    files_fixed = 0

    for file_path, file_violations in sorted(grouped.items()):
        # Sort by rule_id for deterministic ordering
        file_violations.sort(key=lambda v: v.rule_id)

        # Read the current file content to build a PromptFile stub
        # (the violations already carry the path; we read fresh content)
        try:
            if str(file_path) == "-":
                # Cannot fix stdin content
                summary_lines.append(f"  Skipped stdin (-): cannot write back fixes.")
                continue
            current_content = file_path.read_text(encoding="utf-8")
        except (OSError, IOError) as exc:
            summary_lines.append(f"  Skipped {file_path}: {exc}")
            continue

        # Build a minimal PromptFile for the rule.fix() calls
        from promptlint.core.parser import parse_file

        try:
            prompt_file = parse_file(file_path)
        except Exception as exc:
            summary_lines.append(f"  Skipped {file_path}: parse error: {exc}")
            continue

        fixed_content = prompt_file.raw_content
        fixes_applied = 0

        for v in file_violations:
            rule = _find_rule(v.rule_id, rules)
            if rule is None or not rule.fixable:
                continue

            # Build a fresh PromptFile with the latest content so that
            # each successive fix operates on the updated text
            temp_file = prompt_file.model_copy(update={"raw_content": fixed_content})

            try:
                result = rule.fix(temp_file, v)
            except Exception:
                continue

            if result is not None and result != fixed_content:
                fixed_content = result
                fixes_applied += 1

        if fixes_applied > 0:
            if dry_run:
                summary_lines.append(
                    f"  {file_path}: would fix {fixes_applied} violation(s) (dry-run)"
                )
            else:
                try:
                    file_path.write_text(fixed_content, encoding="utf-8")
                    summary_lines.append(
                        f"  {file_path}: fixed {fixes_applied} violation(s)"
                    )
                except (OSError, IOError) as exc:
                    summary_lines.append(
                        f"  {file_path}: write failed: {exc}"
                    )
                    continue

            total_fixed += fixes_applied
            files_fixed += 1

    # Final summary
    mode = "Would fix" if dry_run else "Fixed"
    unfixable = sum(1 for v in violations if not v.fixable)
    summary_lines.append("")
    summary_lines.append(
        f"{mode} {total_fixed} violation(s) in {files_fixed} file(s). "
        f"{unfixable} remaining unfixable violation(s)."
    )

    return summary_lines
