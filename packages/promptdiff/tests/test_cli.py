"""Tests for promptdiff.cli."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from promptdiff.cli import app

runner = CliRunner()


@pytest.fixture
def old_file(tmp_path):
    content = textwrap.dedent("""\
        model: gpt-4
        defaults:
          name: World
        messages:
          - role: system
            content: "You are a helpful assistant."
          - role: user
            content: "Hello {{name}}."
    """)
    p = tmp_path / "old.yaml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def new_file(tmp_path):
    content = textwrap.dedent("""\
        model: gpt-4o
        defaults:
          name: World
        messages:
          - role: system
            content: "You are a concise AI assistant."
          - role: user
            content: "Hello {{name}}, respond in {{lang}}."
    """)
    p = tmp_path / "new.yaml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def identical_file(tmp_path):
    content = textwrap.dedent("""\
        model: gpt-4
        defaults:
          name: World
        messages:
          - role: system
            content: "You are a helpful assistant."
          - role: user
            content: "Hello {{name}}."
    """)
    p = tmp_path / "identical.yaml"
    p.write_text(content, encoding="utf-8")
    return p


class TestCliDiff:
    """Tests for the main diff command."""

    def test_text_output(self, old_file, new_file):
        result = runner.invoke(app, [str(old_file), str(new_file)])
        assert result.exit_code == 0
        assert "Prompt Diff" in result.output

    def test_json_output(self, old_file, new_file):
        result = runner.invoke(
            app, [str(old_file), str(new_file), "--format", "json"]
        )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert "message_diffs" in parsed
        assert "token_delta" in parsed

    def test_markdown_output(self, old_file, new_file):
        result = runner.invoke(
            app, [str(old_file), str(new_file), "--format", "markdown"]
        )
        assert result.exit_code == 0
        assert "## Prompt Diff" in result.output

    def test_exit_on_breaking(self, old_file, new_file):
        result = runner.invoke(
            app, [str(old_file), str(new_file), "--exit-on-breaking"]
        )
        # Should exit 1 because model changed and new variable without default
        assert result.exit_code == 1

    def test_no_exit_on_breaking_identical(self, old_file, identical_file):
        result = runner.invoke(
            app, [str(old_file), str(identical_file), "--exit-on-breaking"]
        )
        assert result.exit_code == 0

    def test_token_detail_flag(self, old_file, new_file):
        result = runner.invoke(
            app, [str(old_file), str(new_file), "--token-detail"]
        )
        assert result.exit_code == 0

    def test_file_not_found(self, tmp_path):
        fake = tmp_path / "nonexistent.yaml"
        real = tmp_path / "real.yaml"
        real.write_text(
            'messages:\n  - role: system\n    content: "Hello"\n',
            encoding="utf-8",
        )
        result = runner.invoke(app, [str(fake), str(real)])
        assert result.exit_code == 2

    def test_no_args_shows_help(self):
        result = runner.invoke(app, [])
        # Typer with no_args_is_help may exit 0 or show help text
        assert "Usage" in result.output or "Semantic diff" in result.output or "promptdiff" in result.output

    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "promptdiff" in result.output


class TestCliJsonOutput:
    """Detailed tests for JSON output format."""

    def test_json_has_breaking_changes(self, old_file, new_file):
        result = runner.invoke(
            app, [str(old_file), str(new_file), "--format", "json"]
        )
        parsed = json.loads(result.output)
        assert parsed["is_breaking"] is True
        assert len(parsed["breaking_changes"]) > 0

    def test_json_has_variable_diffs(self, old_file, new_file):
        result = runner.invoke(
            app, [str(old_file), str(new_file), "--format", "json"]
        )
        parsed = json.loads(result.output)
        var_names = {v["name"] for v in parsed["variable_diffs"]}
        assert "lang" in var_names

    def test_json_has_metadata_diffs(self, old_file, new_file):
        result = runner.invoke(
            app, [str(old_file), str(new_file), "--format", "json"]
        )
        parsed = json.loads(result.output)
        meta_keys = {m["key"] for m in parsed["metadata_diffs"]}
        assert "model" in meta_keys


class TestCliEncodingFlag:
    """Blind spot 8: CLI --encoding flag passthrough."""

    def test_encoding_cl100k_base(self, old_file, new_file):
        result = runner.invoke(
            app, [str(old_file), str(new_file), "--encoding", "cl100k_base"]
        )
        assert result.exit_code == 0

    def test_encoding_p50k_base(self, old_file, new_file):
        result = runner.invoke(
            app, [str(old_file), str(new_file), "--encoding", "p50k_base"]
        )
        assert result.exit_code == 0

    def test_encoding_with_json_output(self, old_file, new_file):
        result = runner.invoke(
            app,
            [str(old_file), str(new_file), "--encoding", "p50k_base", "--format", "json"],
        )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["token_delta"]["old_total"] > 0
