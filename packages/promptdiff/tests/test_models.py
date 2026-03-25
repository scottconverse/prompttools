"""Tests for promptdiff.models."""

from __future__ import annotations

from pathlib import Path

import pytest

from promptdiff.models import (
    BreakingChange,
    ChangeStatus,
    MessageDiff,
    MetadataDiff,
    PromptDiff,
    TokenDelta,
    VariableDiff,
)


class TestChangeStatus:
    """Tests for the ChangeStatus enum."""

    def test_values(self):
        assert ChangeStatus.ADDED == "added"
        assert ChangeStatus.REMOVED == "removed"
        assert ChangeStatus.MODIFIED == "modified"
        assert ChangeStatus.UNCHANGED == "unchanged"

    def test_is_str_enum(self):
        assert isinstance(ChangeStatus.ADDED, str)


class TestMessageDiff:
    """Tests for MessageDiff."""

    def test_added_message(self):
        md = MessageDiff(
            status=ChangeStatus.ADDED,
            role="assistant",
            new_content="Hello!",
            token_delta=3,
            changes=["Added assistant message (3 tokens)"],
        )
        assert md.status == ChangeStatus.ADDED
        assert md.old_content is None
        assert md.new_content == "Hello!"
        assert md.token_delta == 3

    def test_removed_message(self):
        md = MessageDiff(
            status=ChangeStatus.REMOVED,
            role="system",
            old_content="Be helpful.",
            token_delta=-5,
        )
        assert md.status == ChangeStatus.REMOVED
        assert md.old_content == "Be helpful."
        assert md.new_content is None

    def test_modified_message(self):
        md = MessageDiff(
            status=ChangeStatus.MODIFIED,
            role="user",
            old_content="Hi",
            new_content="Hello there",
            content_diff="--- old\n+++ new\n-Hi\n+Hello there",
            token_delta=2,
            changes=["User message content modified"],
        )
        assert md.content_diff is not None
        assert "Hi" in md.content_diff

    def test_unchanged_defaults(self):
        md = MessageDiff(status=ChangeStatus.UNCHANGED, role="system")
        assert md.old_content is None
        assert md.new_content is None
        assert md.content_diff is None
        assert md.token_delta == 0
        assert md.changes == []

    def test_serialization_roundtrip(self):
        md = MessageDiff(
            status=ChangeStatus.ADDED,
            role="user",
            new_content="Test",
            token_delta=1,
        )
        data = md.model_dump()
        restored = MessageDiff(**data)
        assert restored == md


class TestVariableDiff:
    """Tests for VariableDiff."""

    def test_added_without_default_is_breaking(self):
        vd = VariableDiff(
            name="api_key",
            status=ChangeStatus.ADDED,
            is_breaking=True,
        )
        assert vd.is_breaking is True
        assert vd.new_default is None

    def test_added_with_default_not_breaking(self):
        vd = VariableDiff(
            name="language",
            status=ChangeStatus.ADDED,
            new_default="en",
            is_breaking=False,
        )
        assert vd.is_breaking is False

    def test_removed_variable(self):
        vd = VariableDiff(
            name="tone",
            status=ChangeStatus.REMOVED,
            old_default="friendly",
            is_breaking=True,
        )
        assert vd.status == ChangeStatus.REMOVED

    def test_modified_default(self):
        vd = VariableDiff(
            name="name",
            status=ChangeStatus.MODIFIED,
            old_default="World",
            new_default="User",
        )
        assert vd.old_default != vd.new_default


class TestMetadataDiff:
    """Tests for MetadataDiff."""

    def test_added_key(self):
        md = MetadataDiff(
            key="temperature",
            status=ChangeStatus.ADDED,
            new_value=0.7,
        )
        assert md.old_value is None
        assert md.new_value == 0.7

    def test_removed_key(self):
        md = MetadataDiff(
            key="model",
            status=ChangeStatus.REMOVED,
            old_value="gpt-4",
        )
        assert md.old_value == "gpt-4"
        assert md.new_value is None

    def test_modified_key(self):
        md = MetadataDiff(
            key="model",
            status=ChangeStatus.MODIFIED,
            old_value="gpt-4",
            new_value="gpt-4o",
        )
        assert md.old_value != md.new_value


class TestTokenDelta:
    """Tests for TokenDelta."""

    def test_positive_delta(self):
        td = TokenDelta(old_total=100, new_total=120, delta=20, percent_change=20.0)
        assert td.delta == 20
        assert td.percent_change == 20.0

    def test_negative_delta(self):
        td = TokenDelta(old_total=200, new_total=150, delta=-50, percent_change=-25.0)
        assert td.delta == -50

    def test_zero_delta(self):
        td = TokenDelta(old_total=100, new_total=100, delta=0, percent_change=0.0)
        assert td.delta == 0


class TestBreakingChange:
    """Tests for BreakingChange."""

    def test_high_severity(self):
        bc = BreakingChange(
            category="variable",
            description="Variable 'x' was removed",
            severity="high",
        )
        assert bc.severity == "high"
        assert bc.category == "variable"

    def test_medium_severity(self):
        bc = BreakingChange(
            category="model",
            description="Model changed",
            severity="medium",
        )
        assert bc.severity == "medium"


class TestPromptDiff:
    """Tests for the top-level PromptDiff model."""

    def test_is_breaking_with_changes(self):
        diff = PromptDiff(
            file_path=Path("test.yaml"),
            old_hash="abc",
            new_hash="def",
            token_delta=TokenDelta(
                old_total=10, new_total=10, delta=0, percent_change=0.0
            ),
            breaking_changes=[
                BreakingChange(
                    category="variable",
                    description="test",
                    severity="high",
                )
            ],
        )
        assert diff.is_breaking is True

    def test_is_not_breaking_empty(self):
        diff = PromptDiff(
            file_path=Path("test.yaml"),
            old_hash="abc",
            new_hash="def",
            token_delta=TokenDelta(
                old_total=10, new_total=10, delta=0, percent_change=0.0
            ),
        )
        assert diff.is_breaking is False

    def test_json_roundtrip(self):
        diff = PromptDiff(
            file_path=Path("test.yaml"),
            old_hash="abc",
            new_hash="def",
            message_diffs=[
                MessageDiff(status=ChangeStatus.UNCHANGED, role="system")
            ],
            token_delta=TokenDelta(
                old_total=10, new_total=12, delta=2, percent_change=20.0
            ),
        )
        json_str = diff.model_dump_json()
        restored = PromptDiff.model_validate_json(json_str)
        assert restored.old_hash == "abc"
        assert restored.is_breaking is False
        assert len(restored.message_diffs) == 1
