"""Tests for promptdiff.analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from promptdiff.analyzer import analyze_breaking_changes
from promptdiff.models import (
    BreakingChange,
    ChangeStatus,
    MessageDiff,
    MetadataDiff,
    PromptDiff,
    TokenDelta,
    VariableDiff,
)


def _make_diff(**overrides) -> PromptDiff:
    """Helper to build a PromptDiff with defaults."""
    defaults = dict(
        file_path=Path("test.yaml"),
        old_hash="aaa",
        new_hash="bbb",
        message_diffs=[],
        variable_diffs=[],
        metadata_diffs=[],
        token_delta=TokenDelta(
            old_total=100, new_total=100, delta=0, percent_change=0.0
        ),
        breaking_changes=[],
    )
    defaults.update(overrides)
    return PromptDiff(**defaults)


class TestAnalyzeBreakingChanges:
    """Tests for analyze_breaking_changes()."""

    def test_no_changes(self):
        diff = _make_diff()
        result = analyze_breaking_changes(diff)
        assert len(result) == 0

    def test_removed_variable(self):
        diff = _make_diff(
            variable_diffs=[
                VariableDiff(
                    name="tone",
                    status=ChangeStatus.REMOVED,
                    old_default="friendly",
                    is_breaking=True,
                ),
            ]
        )
        result = analyze_breaking_changes(diff)
        assert len(result) == 1
        assert result[0].category == "variable"
        assert result[0].severity == "high"
        assert "tone" in result[0].description

    def test_added_required_variable(self):
        diff = _make_diff(
            variable_diffs=[
                VariableDiff(
                    name="api_key",
                    status=ChangeStatus.ADDED,
                    is_breaking=True,
                ),
            ]
        )
        result = analyze_breaking_changes(diff)
        assert len(result) == 1
        assert result[0].severity == "high"
        assert "api_key" in result[0].description

    def test_added_variable_with_default_not_breaking(self):
        diff = _make_diff(
            variable_diffs=[
                VariableDiff(
                    name="lang",
                    status=ChangeStatus.ADDED,
                    new_default="en",
                    is_breaking=False,
                ),
            ]
        )
        result = analyze_breaking_changes(diff)
        assert len(result) == 0

    def test_removed_message(self):
        diff = _make_diff(
            message_diffs=[
                MessageDiff(
                    status=ChangeStatus.REMOVED,
                    role="system",
                    old_content="Be helpful",
                ),
            ]
        )
        result = analyze_breaking_changes(diff)
        assert len(result) == 1
        assert result[0].category == "message"
        assert result[0].severity == "high"

    def test_added_message_not_breaking(self):
        diff = _make_diff(
            message_diffs=[
                MessageDiff(
                    status=ChangeStatus.ADDED,
                    role="assistant",
                    new_content="How can I help?",
                ),
            ]
        )
        result = analyze_breaking_changes(diff)
        assert len(result) == 0

    def test_modified_message_not_breaking(self):
        diff = _make_diff(
            message_diffs=[
                MessageDiff(
                    status=ChangeStatus.MODIFIED,
                    role="system",
                    old_content="Be helpful",
                    new_content="Be very helpful",
                ),
            ]
        )
        result = analyze_breaking_changes(diff)
        assert len(result) == 0

    def test_model_change(self):
        diff = _make_diff(
            metadata_diffs=[
                MetadataDiff(
                    key="model",
                    status=ChangeStatus.MODIFIED,
                    old_value="gpt-4",
                    new_value="gpt-4o",
                ),
            ]
        )
        result = analyze_breaking_changes(diff)
        assert len(result) == 1
        assert result[0].category == "model"
        assert result[0].severity == "medium"

    def test_model_removed(self):
        diff = _make_diff(
            metadata_diffs=[
                MetadataDiff(
                    key="model",
                    status=ChangeStatus.REMOVED,
                    old_value="gpt-4",
                ),
            ]
        )
        result = analyze_breaking_changes(diff)
        assert len(result) == 1
        assert result[0].category == "model"

    def test_non_model_metadata_change_not_breaking(self):
        diff = _make_diff(
            metadata_diffs=[
                MetadataDiff(
                    key="temperature",
                    status=ChangeStatus.MODIFIED,
                    old_value=0.7,
                    new_value=0.9,
                ),
            ]
        )
        result = analyze_breaking_changes(diff)
        assert len(result) == 0

    def test_role_ordering_change(self):
        diff = _make_diff(
            message_diffs=[
                MessageDiff(
                    status=ChangeStatus.UNCHANGED,
                    role="user",
                    old_content="Q",
                    new_content="Q",
                ),
                MessageDiff(
                    status=ChangeStatus.REMOVED,
                    role="system",
                    old_content="Be helpful",
                ),
                MessageDiff(
                    status=ChangeStatus.ADDED,
                    role="system",
                    new_content="Be helpful",
                ),
            ]
        )
        result = analyze_breaking_changes(diff)
        # Should have at least the removed message breaking change,
        # and potentially a role ordering change.
        categories = {c.category for c in result}
        assert "message" in categories

    def test_severity_sorting(self):
        diff = _make_diff(
            variable_diffs=[
                VariableDiff(
                    name="x",
                    status=ChangeStatus.REMOVED,
                    is_breaking=True,
                ),
            ],
            metadata_diffs=[
                MetadataDiff(
                    key="model",
                    status=ChangeStatus.MODIFIED,
                    old_value="gpt-4",
                    new_value="gpt-4o",
                ),
            ],
        )
        result = analyze_breaking_changes(diff)
        assert len(result) == 2
        # High severity should come first
        assert result[0].severity == "high"
        assert result[1].severity == "medium"

    def test_role_ordering_pure(self):
        """Same messages in different order -- no additions/removals.

        Old: system, user, assistant
        New: user, system, assistant

        The diff_messages alignment groups by role, so the diffs here
        simulate the result: all messages are UNCHANGED but the overall
        role ordering (system, user, assistant) vs (user, system, assistant)
        has changed.  We express that via MODIFIED placeholders whose
        reconstructed role sequences differ.
        """
        diff = _make_diff(
            message_diffs=[
                # Simulate reordering: old had system first, new has user first.
                # Use UNCHANGED for each role but order them differently in the
                # old vs new role sequences by using MODIFIED entries whose
                # role ordering differs.
                MessageDiff(
                    status=ChangeStatus.MODIFIED,
                    role="system",
                    old_content="Be helpful",
                    new_content="Be helpful!",
                ),
                MessageDiff(
                    status=ChangeStatus.MODIFIED,
                    role="user",
                    old_content="Q",
                    new_content="Q!",
                ),
            ]
        )
        # With same roles in same order, no role ordering change should fire
        result = analyze_breaking_changes(diff)
        role_changes = [c for c in result if c.category == "role"]
        assert len(role_changes) == 0

        # Now simulate reordering: old = [system, user], new = [user, system]
        # We need the reconstructed sequences to differ. We do this with
        # a removed system + added system at end, plus unchanged user.
        diff_reordered = _make_diff(
            message_diffs=[
                MessageDiff(
                    status=ChangeStatus.REMOVED,
                    role="system",
                    old_content="Be helpful",
                ),
                MessageDiff(
                    status=ChangeStatus.UNCHANGED,
                    role="user",
                    old_content="Q",
                    new_content="Q",
                ),
                MessageDiff(
                    status=ChangeStatus.ADDED,
                    role="system",
                    new_content="Be helpful",
                ),
            ]
        )
        result2 = analyze_breaking_changes(diff_reordered)
        role_changes2 = [c for c in result2 if c.category == "role"]
        assert len(role_changes2) == 1
        assert role_changes2[0].severity == "medium"
        assert "ordering" in role_changes2[0].description.lower()

    def test_multiple_breaking_changes(self):
        diff = _make_diff(
            variable_diffs=[
                VariableDiff(name="a", status=ChangeStatus.REMOVED, is_breaking=True),
                VariableDiff(name="b", status=ChangeStatus.ADDED, is_breaking=True),
            ],
            message_diffs=[
                MessageDiff(
                    status=ChangeStatus.REMOVED,
                    role="system",
                    old_content="test",
                ),
            ],
        )
        result = analyze_breaking_changes(diff)
        assert len(result) == 3
        assert all(r.severity == "high" for r in result)
