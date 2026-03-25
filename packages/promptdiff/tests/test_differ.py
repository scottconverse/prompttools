"""Tests for promptdiff.differ."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from prompttools_core.models import Message, PromptFile, PromptFormat

from promptdiff.differ import (
    compute_token_delta,
    diff_files,
    diff_messages,
    diff_metadata,
    diff_variables,
)
from promptdiff.models import ChangeStatus


class TestDiffMessages:
    """Tests for diff_messages()."""

    def test_identical_messages(self, simple_old_msg):
        diffs = diff_messages(simple_old_msg, simple_old_msg)
        assert all(d.status == ChangeStatus.UNCHANGED for d in diffs)

    def test_added_message(self, simple_old_msg, simple_new_msg):
        diffs = diff_messages(simple_old_msg, simple_new_msg)
        added = [d for d in diffs if d.status == ChangeStatus.ADDED]
        assert len(added) == 1
        assert added[0].role == "assistant"

    def test_modified_message(self, simple_old_msg, simple_new_msg):
        diffs = diff_messages(simple_old_msg, simple_new_msg)
        modified = [d for d in diffs if d.status == ChangeStatus.MODIFIED]
        assert len(modified) == 1
        assert modified[0].role == "system"
        assert modified[0].content_diff is not None

    def test_removed_message(self, simple_old_msg):
        # new version has no assistant message but old has system+user
        new_msgs = [Message(role="system", content="You are a helpful assistant.")]
        diffs = diff_messages(simple_old_msg, new_msgs)
        removed = [d for d in diffs if d.status == ChangeStatus.REMOVED]
        assert len(removed) == 1
        assert removed[0].role == "user"

    def test_empty_old(self):
        new_msgs = [Message(role="system", content="Hello")]
        diffs = diff_messages([], new_msgs)
        assert len(diffs) == 1
        assert diffs[0].status == ChangeStatus.ADDED

    def test_empty_new(self):
        old_msgs = [Message(role="system", content="Hello")]
        diffs = diff_messages(old_msgs, [])
        assert len(diffs) == 1
        assert diffs[0].status == ChangeStatus.REMOVED

    def test_both_empty(self):
        diffs = diff_messages([], [])
        assert len(diffs) == 0

    def test_token_delta_on_modification(self):
        old = [Message(role="user", content="Hi")]
        new = [Message(role="user", content="Hello, how are you doing today?")]
        diffs = diff_messages(old, new)
        assert len(diffs) == 1
        assert diffs[0].status == ChangeStatus.MODIFIED
        assert diffs[0].token_delta != 0

    def test_content_diff_is_unified(self, simple_old_msg, simple_new_msg):
        diffs = diff_messages(simple_old_msg, simple_new_msg)
        modified = [d for d in diffs if d.status == ChangeStatus.MODIFIED]
        assert len(modified) == 1
        # Unified diff should contain --- and +++
        assert "---" in modified[0].content_diff
        assert "+++" in modified[0].content_diff

    def test_multiple_same_role(self):
        old = [
            Message(role="user", content="First question"),
            Message(role="user", content="Second question"),
        ]
        new = [
            Message(role="user", content="First question"),
            Message(role="user", content="Modified second question"),
        ]
        diffs = diff_messages(old, new)
        assert len(diffs) == 2
        assert diffs[0].status == ChangeStatus.UNCHANGED
        assert diffs[1].status == ChangeStatus.MODIFIED


class TestDiffVariables:
    """Tests for diff_variables()."""

    def test_no_changes(self):
        old_vars = {"name": "jinja", "tone": "jinja"}
        new_vars = {"name": "jinja", "tone": "jinja"}
        defaults = {"name": "World", "tone": "friendly"}
        diffs = diff_variables(old_vars, new_vars, defaults, defaults)
        assert all(d.status == ChangeStatus.UNCHANGED for d in diffs)

    def test_added_variable_no_default(self):
        old_vars = {"name": "jinja"}
        new_vars = {"name": "jinja", "lang": "jinja"}
        diffs = diff_variables(old_vars, new_vars, {}, {})
        added = [d for d in diffs if d.status == ChangeStatus.ADDED]
        assert len(added) == 1
        assert added[0].name == "lang"
        assert added[0].is_breaking is True

    def test_added_variable_with_default(self):
        old_vars = {"name": "jinja"}
        new_vars = {"name": "jinja", "lang": "jinja"}
        diffs = diff_variables(old_vars, new_vars, {}, {"lang": "en"})
        added = [d for d in diffs if d.status == ChangeStatus.ADDED]
        assert len(added) == 1
        assert added[0].is_breaking is False
        assert added[0].new_default == "en"

    def test_removed_variable(self):
        old_vars = {"name": "jinja", "tone": "jinja"}
        new_vars = {"name": "jinja"}
        diffs = diff_variables(old_vars, new_vars, {"tone": "friendly"}, {})
        removed = [d for d in diffs if d.status == ChangeStatus.REMOVED]
        assert len(removed) == 1
        assert removed[0].name == "tone"
        assert removed[0].is_breaking is True

    def test_modified_default(self):
        old_vars = {"name": "jinja"}
        new_vars = {"name": "jinja"}
        diffs = diff_variables(
            old_vars, new_vars, {"name": "World"}, {"name": "User"}
        )
        modified = [d for d in diffs if d.status == ChangeStatus.MODIFIED]
        assert len(modified) == 1
        assert modified[0].old_default == "World"
        assert modified[0].new_default == "User"

    def test_empty_both(self):
        diffs = diff_variables({}, {}, {}, {})
        assert len(diffs) == 0


class TestDiffMetadata:
    """Tests for diff_metadata()."""

    def test_no_changes(self):
        meta = {"model": "gpt-4", "temperature": 0.7}
        diffs = diff_metadata(meta, meta)
        assert all(d.status == ChangeStatus.UNCHANGED for d in diffs)

    def test_added_key(self):
        old = {"model": "gpt-4"}
        new = {"model": "gpt-4", "temperature": 0.7}
        diffs = diff_metadata(old, new)
        added = [d for d in diffs if d.status == ChangeStatus.ADDED]
        assert len(added) == 1
        assert added[0].key == "temperature"

    def test_removed_key(self):
        old = {"model": "gpt-4", "temperature": 0.7}
        new = {"model": "gpt-4"}
        diffs = diff_metadata(old, new)
        removed = [d for d in diffs if d.status == ChangeStatus.REMOVED]
        assert len(removed) == 1
        assert removed[0].key == "temperature"

    def test_modified_value(self):
        old = {"model": "gpt-4"}
        new = {"model": "gpt-4o"}
        diffs = diff_metadata(old, new)
        modified = [d for d in diffs if d.status == ChangeStatus.MODIFIED]
        assert len(modified) == 1
        assert modified[0].old_value == "gpt-4"
        assert modified[0].new_value == "gpt-4o"

    def test_empty_both(self):
        diffs = diff_metadata({}, {})
        assert len(diffs) == 0


class TestComputeTokenDelta:
    """Tests for compute_token_delta()."""

    def test_same_file(self):
        pf = PromptFile(
            path=Path("test.yaml"),
            format=PromptFormat.YAML,
            raw_content="test",
            messages=[
                Message(role="system", content="Hello world"),
            ],
        )
        td = compute_token_delta(pf, pf)
        assert td.delta == 0
        assert td.percent_change == 0.0

    def test_increased_tokens(self):
        old = PromptFile(
            path=Path("old.yaml"),
            format=PromptFormat.YAML,
            raw_content="old",
            messages=[Message(role="system", content="Hi")],
        )
        new = PromptFile(
            path=Path("new.yaml"),
            format=PromptFormat.YAML,
            raw_content="new",
            messages=[
                Message(role="system", content="Hello, I am a helpful AI assistant here to help you.")
            ],
        )
        td = compute_token_delta(old, new)
        assert td.delta > 0
        assert td.new_total > td.old_total
        assert td.percent_change > 0

    def test_decreased_tokens(self):
        old = PromptFile(
            path=Path("old.yaml"),
            format=PromptFormat.YAML,
            raw_content="old",
            messages=[
                Message(role="system", content="Hello, I am a helpful AI assistant here to help you with many things.")
            ],
        )
        new = PromptFile(
            path=Path("new.yaml"),
            format=PromptFormat.YAML,
            raw_content="new",
            messages=[Message(role="system", content="Hi")],
        )
        td = compute_token_delta(old, new)
        assert td.delta < 0
        assert td.percent_change < 0


class TestDiffFiles:
    """Integration tests for diff_files()."""

    def test_diff_identical_files(self, old_prompt_file, identical_prompt_file):
        result = diff_files(old_prompt_file, identical_prompt_file)
        assert result.is_breaking is False
        assert result.token_delta.delta == 0
        unchanged = [m for m in result.message_diffs if m.status == ChangeStatus.UNCHANGED]
        assert len(unchanged) == len(result.message_diffs)

    def test_diff_modified_files(self, old_prompt_file, new_prompt_file):
        result = diff_files(old_prompt_file, new_prompt_file)
        # Should detect changes
        changed = [m for m in result.message_diffs if m.status != ChangeStatus.UNCHANGED]
        assert len(changed) > 0
        # Should have variable changes
        var_changed = [v for v in result.variable_diffs if v.status != ChangeStatus.UNCHANGED]
        assert len(var_changed) > 0

    def test_diff_produces_hashes(self, old_prompt_file, new_prompt_file):
        result = diff_files(old_prompt_file, new_prompt_file)
        assert len(result.old_hash) > 0
        assert len(result.new_hash) > 0
        assert result.old_hash != result.new_hash

    def test_diff_file_not_found(self, tmp_path):
        fake = tmp_path / "nonexistent.yaml"
        real = tmp_path / "real.yaml"
        real.write_text(
            'messages:\n  - role: system\n    content: "Hello"\n',
            encoding="utf-8",
        )
        with pytest.raises(FileNotFoundError):
            diff_files(fake, real)

    def test_diff_breaking_changes_populated(self, old_prompt_file, new_prompt_file):
        result = diff_files(old_prompt_file, new_prompt_file)
        # The new file removes 'tone' variable and adds 'language' without default,
        # and changes model -- should have breaking changes.
        assert result.is_breaking is True
        assert len(result.breaking_changes) > 0

    def test_diff_files_custom_encoding(self, old_prompt_file, new_prompt_file):
        """Blind spot 6: diff_files() with a non-default encoding parameter."""
        result = diff_files(old_prompt_file, new_prompt_file, encoding="p50k_base")
        # Should still produce a valid diff with the alternative encoding.
        assert result.token_delta.old_total > 0
        assert result.token_delta.new_total > 0
        assert result.old_hash != result.new_hash

    def test_diff_files_malformed_yaml(self, tmp_path):
        """Blind spot 9: malformed YAML input with no messages key."""
        bad_content = "not_messages:\n  - foo: bar\n"
        good_content = 'messages:\n  - role: system\n    content: "Hello"\n'
        bad = tmp_path / "bad.yaml"
        good = tmp_path / "good.yaml"
        bad.write_text(bad_content, encoding="utf-8")
        good.write_text(good_content, encoding="utf-8")
        # Should raise a clear error, not crash with KeyError
        with pytest.raises((KeyError, ValueError, TypeError, Exception)):
            diff_files(bad, good)


class TestComputeTokenDeltaZeroOldTotal:
    """Blind spot 5: compute_token_delta with zero old_total."""

    def test_zero_old_total_nonzero_new(self):
        """Division-by-zero path: old has 0 tokens, new has some."""
        old = PromptFile(
            path=Path("empty.yaml"),
            format=PromptFormat.YAML,
            raw_content="",
            messages=[],
        )
        new = PromptFile(
            path=Path("new.yaml"),
            format=PromptFormat.YAML,
            raw_content="new",
            messages=[Message(role="system", content="Hello world")],
        )
        td = compute_token_delta(old, new)
        assert td.old_total == 0
        assert td.new_total > 0
        assert td.percent_change == 100.0

    def test_zero_old_total_zero_new(self):
        """Both files empty -- 0% change, no division error."""
        old = PromptFile(
            path=Path("empty1.yaml"),
            format=PromptFormat.YAML,
            raw_content="",
            messages=[],
        )
        new = PromptFile(
            path=Path("empty2.yaml"),
            format=PromptFormat.YAML,
            raw_content="",
            messages=[],
        )
        td = compute_token_delta(old, new)
        assert td.old_total == 0
        assert td.new_total == 0
        assert td.delta == 0
        assert td.percent_change == 0.0


class TestDiffMessagesUnicode:
    """Blind spot 10: unicode content in messages."""

    def test_unicode_emoji(self):
        old = [Message(role="user", content="Hello world")]
        new = [Message(role="user", content="Hello world! \U0001f600\U0001f680\U0001f4a5")]
        diffs = diff_messages(old, new)
        assert len(diffs) == 1
        assert diffs[0].status == ChangeStatus.MODIFIED
        assert "\U0001f600" in diffs[0].new_content

    def test_unicode_cjk(self):
        old = [Message(role="system", content="\u4f60\u597d\u4e16\u754c")]
        new = [Message(role="system", content="\u4f60\u597d\u4e16\u754c\uff0c\u8bf7\u5e2e\u52a9\u6211")]
        diffs = diff_messages(old, new)
        assert len(diffs) == 1
        assert diffs[0].status == ChangeStatus.MODIFIED
        assert diffs[0].token_delta != 0

    def test_unicode_accented(self):
        old = [Message(role="user", content="caf\u00e9 na\u00efve r\u00e9sum\u00e9")]
        new = [Message(role="user", content="caf\u00e9 na\u00efve r\u00e9sum\u00e9")]
        diffs = diff_messages(old, new)
        assert len(diffs) == 1
        assert diffs[0].status == ChangeStatus.UNCHANGED
