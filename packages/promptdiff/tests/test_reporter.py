"""Tests for promptdiff.reporter."""

from __future__ import annotations

import json
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
from promptdiff.reporter import format_json, format_markdown, format_text


class TestFormatText:
    """Tests for format_text()."""

    def test_contains_file_path(self, sample_diff):
        output = format_text(sample_diff)
        assert "test_prompt.yaml" in output

    def test_contains_hashes(self, sample_diff):
        output = format_text(sample_diff)
        # Hashes are 18 chars but reporter truncates to [:12]
        assert "aaa111bbb222" in output
        assert "ddd444eee555" in output
        # Full 18-char hash should NOT appear (truncation exercised)
        assert "aaa111bbb222ccc333" not in output
        assert "ddd444eee555fff666" not in output

    def test_shows_breaking_changes(self, sample_diff):
        output = format_text(sample_diff)
        assert "BREAKING CHANGES" in output
        assert "tone" in output

    def test_shows_token_delta(self, sample_diff):
        output = format_text(sample_diff)
        assert "100" in output
        assert "115" in output
        assert "+15" in output

    def test_shows_message_changes(self, sample_diff):
        output = format_text(sample_diff)
        assert "system" in output.lower()
        assert "assistant" in output.lower()

    def test_shows_variable_changes(self, sample_diff):
        output = format_text(sample_diff)
        assert "tone" in output
        assert "language" in output

    def test_shows_metadata_changes(self, sample_diff):
        output = format_text(sample_diff)
        assert "model" in output.lower()
        assert "gpt-4o" in output

    def test_no_breaking_changes_message(self):
        diff = PromptDiff(
            file_path=Path("ok.yaml"),
            old_hash="aaa",
            new_hash="bbb",
            token_delta=TokenDelta(
                old_total=50, new_total=50, delta=0, percent_change=0.0
            ),
        )
        output = format_text(diff)
        assert "No breaking changes" in output

    def test_token_detail_flag(self, sample_diff):
        output_no_detail = format_text(sample_diff, show_token_detail=False)
        output_with_detail = format_text(sample_diff, show_token_detail=True)
        # With detail should have more content
        assert len(output_with_detail) >= len(output_no_detail)

    def test_content_diff_coloring(self, sample_diff):
        output = format_text(sample_diff)
        # Should contain rich markup for diff lines
        assert "[green]" in output or "[red]" in output


class TestFormatJson:
    """Tests for format_json()."""

    def test_valid_json(self, sample_diff):
        output = format_json(sample_diff)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_contains_all_fields(self, sample_diff):
        output = format_json(sample_diff)
        parsed = json.loads(output)
        assert "file_path" in parsed
        assert "old_hash" in parsed
        assert "new_hash" in parsed
        assert "message_diffs" in parsed
        assert "variable_diffs" in parsed
        assert "metadata_diffs" in parsed
        assert "token_delta" in parsed
        assert "breaking_changes" in parsed
        assert "is_breaking" in parsed

    def test_is_breaking_true(self, sample_diff):
        output = format_json(sample_diff)
        parsed = json.loads(output)
        assert parsed["is_breaking"] is True

    def test_message_diffs_count(self, sample_diff):
        output = format_json(sample_diff)
        parsed = json.loads(output)
        assert len(parsed["message_diffs"]) == 3

    def test_breaking_changes_count(self, sample_diff):
        output = format_json(sample_diff)
        parsed = json.loads(output)
        assert len(parsed["breaking_changes"]) == 3

    def test_token_delta_values(self, sample_diff):
        output = format_json(sample_diff)
        parsed = json.loads(output)
        td = parsed["token_delta"]
        assert td["old_total"] == 100
        assert td["new_total"] == 115
        assert td["delta"] == 15


class TestFormatMarkdown:
    """Tests for format_markdown()."""

    def test_starts_with_header(self, sample_diff):
        output = format_markdown(sample_diff)
        assert output.startswith("## Prompt Diff:")

    def test_contains_file_path(self, sample_diff):
        output = format_markdown(sample_diff)
        assert "test_prompt.yaml" in output

    def test_contains_breaking_changes_section(self, sample_diff):
        output = format_markdown(sample_diff)
        assert "### Breaking Changes" in output

    def test_contains_token_delta_table(self, sample_diff):
        output = format_markdown(sample_diff)
        assert "| Old | New | Delta | Change |" in output
        assert "| 100 | 115 |" in output

    def test_contains_messages_section(self, sample_diff):
        output = format_markdown(sample_diff)
        assert "### Messages" in output

    def test_contains_variables_section(self, sample_diff):
        output = format_markdown(sample_diff)
        assert "### Variables" in output

    def test_contains_metadata_section(self, sample_diff):
        output = format_markdown(sample_diff)
        assert "### Metadata" in output

    def test_contains_diff_block(self, sample_diff):
        output = format_markdown(sample_diff)
        assert "```diff" in output

    def test_no_breaking_message(self):
        diff = PromptDiff(
            file_path=Path("ok.yaml"),
            old_hash="aaa",
            new_hash="bbb",
            token_delta=TokenDelta(
                old_total=50, new_total=50, delta=0, percent_change=0.0
            ),
        )
        output = format_markdown(diff)
        assert "No breaking changes" in output

    def test_breaking_severity_badges(self, sample_diff):
        output = format_markdown(sample_diff)
        assert "**HIGH**" in output
        assert "MEDIUM" in output


class TestFormattersMetadataOnly:
    """Blind spot 7: formatters with only metadata changes (no messages or variables)."""

    @pytest.fixture
    def metadata_only_diff(self):
        return PromptDiff(
            file_path=Path("meta_only.yaml"),
            old_hash="aaaa1111bbbb2222",
            new_hash="cccc3333dddd4444",
            message_diffs=[],
            variable_diffs=[],
            metadata_diffs=[
                MetadataDiff(
                    key="temperature",
                    status=ChangeStatus.MODIFIED,
                    old_value=0.7,
                    new_value=0.9,
                ),
            ],
            token_delta=TokenDelta(
                old_total=50, new_total=50, delta=0, percent_change=0.0
            ),
            breaking_changes=[],
        )

    def test_format_text_metadata_only(self, metadata_only_diff):
        output = format_text(metadata_only_diff)
        assert "meta_only.yaml" in output
        assert "temperature" in output
        assert "No breaking changes" in output

    def test_format_json_metadata_only(self, metadata_only_diff):
        output = format_json(metadata_only_diff)
        parsed = json.loads(output)
        assert len(parsed["message_diffs"]) == 0
        assert len(parsed["variable_diffs"]) == 0
        assert len(parsed["metadata_diffs"]) == 1
        assert parsed["metadata_diffs"][0]["key"] == "temperature"
        assert parsed["is_breaking"] is False

    def test_format_markdown_metadata_only(self, metadata_only_diff):
        output = format_markdown(metadata_only_diff)
        assert "meta_only.yaml" in output
        assert "### Metadata" in output
        assert "temperature" in output
        assert "No breaking changes" in output
