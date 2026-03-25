"""Breaking change detection for promptdiff.

Analyzes a PromptDiff and classifies changes by severity.

Breaking changes:
  - New required variable (no default) -- high severity
  - Removed variable -- high severity
  - Removed message -- high severity
  - Changed role ordering -- medium severity
  - Model change (in metadata) -- medium severity

Non-breaking changes:
  - Added variable with default
  - Added messages
  - Content modifications
  - Metadata changes (except model)
"""

from __future__ import annotations

from promptdiff.models import (
    BreakingChange,
    ChangeStatus,
    PromptDiff,
)


def analyze_breaking_changes(diff: PromptDiff) -> list[BreakingChange]:
    """Analyze a diff for breaking changes.

    Parameters
    ----------
    diff:
        The prompt diff to analyze.

    Returns
    -------
    list[BreakingChange]
        All detected breaking changes sorted by severity.
    """
    changes: list[BreakingChange] = []
    changes.extend(_check_variable_changes(diff))
    changes.extend(_check_message_changes(diff))
    changes.extend(_check_metadata_changes(diff))
    changes.extend(_check_role_ordering(diff))

    # Sort by severity: high first, then medium, then low.
    severity_order = {"high": 0, "medium": 1, "low": 2}
    changes.sort(key=lambda c: severity_order.get(c.severity, 3))

    return changes


def _check_variable_changes(diff: PromptDiff) -> list[BreakingChange]:
    """Detect breaking variable changes."""
    changes: list[BreakingChange] = []

    for vd in diff.variable_diffs:
        if vd.status == ChangeStatus.REMOVED:
            changes.append(
                BreakingChange(
                    category="variable",
                    description=f"Variable '{vd.name}' was removed",
                    severity="high",
                )
            )
        elif vd.status == ChangeStatus.ADDED and vd.is_breaking:
            changes.append(
                BreakingChange(
                    category="variable",
                    description=(
                        f"New required variable '{vd.name}' added without a default value"
                    ),
                    severity="high",
                )
            )

    return changes


def _check_message_changes(diff: PromptDiff) -> list[BreakingChange]:
    """Detect breaking message changes."""
    changes: list[BreakingChange] = []

    for md in diff.message_diffs:
        if md.status == ChangeStatus.REMOVED:
            changes.append(
                BreakingChange(
                    category="message",
                    description=f"{md.role.capitalize()} message was removed",
                    severity="high",
                )
            )

    return changes


def _check_metadata_changes(diff: PromptDiff) -> list[BreakingChange]:
    """Detect breaking metadata changes (model changes)."""
    changes: list[BreakingChange] = []

    for md in diff.metadata_diffs:
        if md.key == "model" and md.status == ChangeStatus.MODIFIED:
            changes.append(
                BreakingChange(
                    category="model",
                    description=(
                        f"Model changed from '{md.old_value}' to '{md.new_value}'"
                    ),
                    severity="medium",
                )
            )
        elif md.key == "model" and md.status == ChangeStatus.REMOVED:
            changes.append(
                BreakingChange(
                    category="model",
                    description="Model specification was removed",
                    severity="medium",
                )
            )

    return changes


def _check_role_ordering(diff: PromptDiff) -> list[BreakingChange]:
    """Detect role ordering changes.

    If the sequence of roles (ignoring unchanged content) changes between
    old and new, this is potentially breaking.
    """
    changes: list[BreakingChange] = []

    # Reconstruct old and new role sequences from the message diffs.
    old_roles: list[str] = []
    new_roles: list[str] = []

    for md in diff.message_diffs:
        if md.status == ChangeStatus.REMOVED:
            old_roles.append(md.role)
        elif md.status == ChangeStatus.ADDED:
            new_roles.append(md.role)
        elif md.status in (ChangeStatus.MODIFIED, ChangeStatus.UNCHANGED):
            old_roles.append(md.role)
            new_roles.append(md.role)

    if old_roles != new_roles and len(old_roles) > 0 and len(new_roles) > 0:
        # Only flag if neither list is a subset scenario (pure additions/removals
        # are already caught above). Check if the common elements changed order.
        common_old = [r for r in old_roles if r in new_roles]
        common_new = [r for r in new_roles if r in old_roles]
        if common_old != common_new:
            changes.append(
                BreakingChange(
                    category="role",
                    description=(
                        f"Message role ordering changed: "
                        f"{' -> '.join(old_roles)} to {' -> '.join(new_roles)}"
                    ),
                    severity="medium",
                )
            )

    return changes
