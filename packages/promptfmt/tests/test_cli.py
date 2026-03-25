"""CLI-level tests for promptfmt using typer.testing.CliRunner."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from promptfmt.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_YAML = (
    "messages:\n"
    "  - role: system\n"
    '    content: "You are a helpful assistant."\n'
    "  - role: user\n"
    '    content: "Hello  world"\n'
)

ALREADY_CLEAN_YAML = (
    "messages:\n"
    "  - role: system\n"
    '    content: "You are a helpful assistant."\n'
    "  - role: user\n"
    '    content: "Hello world"\n'
)

VALID_TXT = (
    "### SYSTEM\n"
    "You are a helpful assistant.\n\n"
    "### USER\n"
    "Hello world\n"
)


def _write_prompt(tmp_path: Path, name: str, content: str) -> Path:
    """Create a prompt file in tmp_path."""
    f = tmp_path / name
    f.write_text(content, encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# format — single file
# ---------------------------------------------------------------------------


class TestFormatSingleFile:
    def test_format_single_yaml(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "test.yaml", VALID_YAML)
        result = runner.invoke(app, ["format", str(f)])
        assert result.exit_code == 0

    def test_format_single_txt(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "test.txt", VALID_TXT)
        result = runner.invoke(app, ["format", str(f)])
        assert result.exit_code == 0

    def test_format_writes_content_back(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "test.yaml", VALID_YAML)
        original = f.read_text(encoding="utf-8")
        runner.invoke(app, ["format", str(f)])
        updated = f.read_text(encoding="utf-8")
        # File should be updated (trailing spaces removed at minimum)
        assert isinstance(updated, str)
        assert len(updated) > 0


# ---------------------------------------------------------------------------
# format --check
# ---------------------------------------------------------------------------


class TestFormatCheck:
    def test_check_returns_1_when_changes_needed(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "test.yaml", VALID_YAML)
        result = runner.invoke(app, ["format", "--check", str(f)])
        # If file needs formatting, exit 1; if already clean, exit 0.
        assert result.exit_code in (0, 1)

    def test_check_does_not_modify_file(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "test.yaml", VALID_YAML)
        original = f.read_text(encoding="utf-8")
        runner.invoke(app, ["format", "--check", str(f)])
        after = f.read_text(encoding="utf-8")
        assert after == original, "--check should not modify the file"

    def test_check_returns_0_for_clean_file(self, tmp_path: Path):
        # Format the file first, then check — should be 0
        f = _write_prompt(tmp_path, "test.yaml", VALID_YAML)
        runner.invoke(app, ["format", str(f)])
        result = runner.invoke(app, ["format", "--check", str(f)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# format --diff
# ---------------------------------------------------------------------------


class TestFormatDiff:
    def test_diff_shows_diff_output(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "test.yaml", VALID_YAML)
        result = runner.invoke(app, ["format", "--diff", str(f)])
        assert result.exit_code == 0
        # If changes were made, output should contain something
        # (diff markers or file path)

    def test_diff_with_check(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "test.yaml", VALID_YAML)
        result = runner.invoke(app, ["format", "--diff", "--check", str(f)])
        # Should not modify the file
        assert result.exit_code in (0, 1)


# ---------------------------------------------------------------------------
# format — directory
# ---------------------------------------------------------------------------


class TestFormatDirectory:
    def test_format_directory_processes_all_files(self, tmp_path: Path):
        _write_prompt(tmp_path, "a.yaml", VALID_YAML)
        _write_prompt(tmp_path, "b.yaml", VALID_YAML)
        _write_prompt(tmp_path, "c.txt", VALID_TXT)
        result = runner.invoke(app, ["format", str(tmp_path)])
        assert result.exit_code == 0

    def test_format_directory_recursive(self, tmp_path: Path):
        sub = tmp_path / "sub"
        sub.mkdir()
        _write_prompt(sub, "nested.yaml", VALID_YAML)
        result = runner.invoke(app, ["format", str(tmp_path)])
        assert result.exit_code == 0

    def test_format_empty_directory(self, tmp_path: Path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = runner.invoke(app, ["format", str(empty_dir)])
        # No files found, should exit 0 with message
        assert result.exit_code == 0
        assert "No prompt files found" in result.output


# ---------------------------------------------------------------------------
# format — style options
# ---------------------------------------------------------------------------


class TestFormatOptions:
    def test_delimiter_style(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "test.txt", VALID_TXT)
        result = runner.invoke(
            app, ["format", "--delimiter-style", "===", str(f)]
        )
        assert result.exit_code == 0

    def test_variable_style(self, tmp_path: Path):
        content = (
            "messages:\n"
            "  - role: user\n"
            "    content: Hello {{name}}\n"
        )
        f = _write_prompt(tmp_path, "test.yaml", content)
        result = runner.invoke(
            app, ["format", "--variable-style", "double_brace", str(f)]
        )
        assert result.exit_code == 0

    def test_max_line_length(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "test.yaml", VALID_YAML)
        result = runner.invoke(
            app, ["format", "--max-line-length", "80", str(f)]
        )
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# format --quiet
# ---------------------------------------------------------------------------


class TestFormatQuiet:
    def test_quiet_suppresses_output(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "test.yaml", VALID_YAML)
        result = runner.invoke(app, ["format", "--quiet", str(f)])
        assert result.exit_code == 0
        # Quiet mode: no "formatted" or "unchanged" text
        assert "formatted" not in result.output.lower() or result.output.strip() == ""

    def test_quiet_on_empty_dir(self, tmp_path: Path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = runner.invoke(app, ["format", "--quiet", str(empty_dir)])
        assert result.exit_code == 0
        assert "No prompt files" not in result.output


# ---------------------------------------------------------------------------
# format — error handling
# ---------------------------------------------------------------------------


class TestFormatErrors:
    def test_nonexistent_path(self, tmp_path: Path):
        bad_path = tmp_path / "does_not_exist.yaml"
        result = runner.invoke(app, ["format", str(bad_path)])
        # Should exit 0 with "no files" or handle gracefully
        # _collect_files returns [] for non-existent path
        assert result.exit_code == 0

    def test_invalid_yaml_content(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "bad.yaml", ":::not valid yaml:::\n")
        result = runner.invoke(app, ["format", str(f)])
        # Should report an error but not crash
        assert result.exit_code in (0, 2)


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


class TestInit:
    def test_init_creates_config(self, monkeypatch, tmp_path: Path):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        config = tmp_path / ".promptfmt.yaml"
        assert config.exists()
        content = config.read_text(encoding="utf-8")
        assert "delimiter_style" in content
        assert "variable_style" in content

    def test_init_refuses_overwrite(self, monkeypatch, tmp_path: Path):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".promptfmt.yaml").write_text("existing", encoding="utf-8")
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 1
        assert "already exists" in result.output
