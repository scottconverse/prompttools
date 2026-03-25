"""Tests for promptlint.cli (Typer CLI)."""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from promptlint.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# check command — single file
# ---------------------------------------------------------------------------


class TestCheckFile:
    def test_clean_file_exit_0(self, tmp_path: Path) -> None:
        f = tmp_path / "prompt.yaml"
        content = yaml.dump({
            "messages": [
                {"role": "system", "content": "You are helpful. Do not hallucinate."},
                {"role": "user", "content": "Respond in JSON. What is 2+2?"},
            ]
        })
        f.write_text(content, encoding="utf-8")
        result = runner.invoke(app, ["check", str(f)])
        # Exit 0 (clean) or 1 (some rules fire) — main thing is no crash (exit 2)
        assert result.exit_code in (0, 1)

    def test_violations_exit_1(self, tmp_path: Path) -> None:
        f = tmp_path / "prompt.txt"
        f.write_text("hello   \n", encoding="utf-8")
        result = runner.invoke(app, ["check", str(f)])
        assert result.exit_code == 1

    def test_nonexistent_exit_2(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["check", str(tmp_path / "nope.txt")])
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# check command — directory
# ---------------------------------------------------------------------------


class TestCheckDirectory:
    def test_lint_directory(self, tmp_path: Path) -> None:
        f = tmp_path / "prompt.txt"
        f.write_text("hello   \n", encoding="utf-8")
        result = runner.invoke(app, ["check", str(tmp_path)])
        assert result.exit_code == 1

    def test_empty_directory_exit_0(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["check", str(tmp_path)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# check command — stdin
# ---------------------------------------------------------------------------


class TestCheckStdin:
    def test_stdin_text(self) -> None:
        result = runner.invoke(app, ["check", "-"], input="hello world")
        # Should run without crashing; exit 0 or 1 depending on violations
        assert result.exit_code in (0, 1)

    def test_stdin_yaml(self) -> None:
        content = yaml.dump({"messages": [{"role": "user", "content": "Hi"}]})
        result = runner.invoke(
            app, ["check", "-", "--input-format", "yaml"], input=content
        )
        assert result.exit_code in (0, 1)


# ---------------------------------------------------------------------------
# check command — JSON output
# ---------------------------------------------------------------------------


class TestCheckJsonFormat:
    def test_json_output(self, tmp_path: Path) -> None:
        f = tmp_path / "prompt.txt"
        f.write_text("hello   \n", encoding="utf-8")
        result = runner.invoke(app, ["check", str(f), "--format", "json", "--no-color"])
        assert result.exit_code == 1
        # Rich console may embed ANSI escapes or control chars; strip them
        import re
        output = re.sub(r"\x1b\[[0-9;]*m", "", result.output).strip()
        start = output.index("[")
        end = output.rindex("]") + 1
        raw_json = output[start:end]
        data = json.loads(raw_json, strict=False)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "rule_id" in data[0]


# ---------------------------------------------------------------------------
# rules command
# ---------------------------------------------------------------------------


class TestRulesCommand:
    def test_rules_text(self) -> None:
        result = runner.invoke(app, ["rules"])
        assert result.exit_code == 0
        assert "PL001" in result.output

    def test_rules_json(self) -> None:
        result = runner.invoke(app, ["rules", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        ids = [e["rule_id"] for e in data]
        assert "PL001" in ids

    def test_rules_category_filter(self) -> None:
        result = runner.invoke(app, ["rules", "--format", "json", "--category", "token"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert all(e["category"] == "token" for e in data)


# ---------------------------------------------------------------------------
# init command
# ---------------------------------------------------------------------------


class TestInitCommand:
    def test_init_creates_config(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert (tmp_path / ".promptlint.yaml").exists()

    def test_init_refuses_overwrite(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".promptlint.yaml").write_text("existing", encoding="utf-8")
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 1
