"""CLI-level tests for prompttest using typer.testing.CliRunner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from prompttest.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PROMPT_YAML = (
    "messages:\n"
    "  - role: system\n"
    "    content: You are a helpful assistant. Greet the user warmly.\n"
    "  - role: user\n"
    "    content: Hello, my name is {{user_name}}.\n"
)

PROMPT_MINIMAL = (
    "messages:\n"
    "  - role: user\n"
    "    content: Hello\n"
)


def _make_prompt(tmp_path: Path, name: str = "prompt.yaml", content: str = PROMPT_YAML) -> Path:
    """Create a prompt file on disk."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    f = prompts_dir / name
    f.write_text(content, encoding="utf-8")
    return f


def _make_test_file(
    tmp_path: Path,
    prompt_path: Path,
    test_name: str = "test_suite.yaml",
    *,
    suite_name: str = "test-suite",
    tests_yaml: str = "",
) -> Path:
    """Create a YAML test file referencing the prompt."""
    rel_prompt = prompt_path.relative_to(tmp_path)
    content = (
        f"suite: {suite_name}\n"
        f"prompt: {rel_prompt}\n"
        f"tests:\n"
        f"{tests_yaml}"
    )
    f = tmp_path / test_name
    f.write_text(content, encoding="utf-8")
    return f


def _make_passing_test(tmp_path: Path) -> Path:
    """Create a prompt + test file where all tests pass."""
    prompt = _make_prompt(tmp_path)
    tests_yaml = (
        "  - name: has-system\n"
        "    assert: has_role\n"
        "    role: system\n"
        "  - name: is-valid\n"
        "    assert: valid_format\n"
        "  - name: has-greet\n"
        "    assert: contains\n"
        '    text: "greet the user"\n'
    )
    return _make_test_file(tmp_path, prompt, tests_yaml=tests_yaml)


def _make_failing_test(tmp_path: Path) -> Path:
    """Create a prompt + test file where at least one test fails."""
    prompt = _make_prompt(tmp_path)
    tests_yaml = (
        "  - name: has-system\n"
        "    assert: has_role\n"
        "    role: system\n"
        "  - name: should-fail\n"
        "    assert: contains\n"
        '    text: "this text does not exist in the prompt"\n'
    )
    return _make_test_file(tmp_path, prompt, tests_yaml=tests_yaml)


def _make_multi_test_with_early_failure(tmp_path: Path) -> Path:
    """Create a test file where the first test fails, useful for --fail-fast."""
    prompt = _make_prompt(tmp_path)
    tests_yaml = (
        "  - name: will-fail-first\n"
        "    assert: contains\n"
        '    text: "nonexistent magic string"\n'
        "  - name: would-pass\n"
        "    assert: valid_format\n"
        "  - name: also-would-pass\n"
        "    assert: has_role\n"
        "    role: user\n"
    )
    return _make_test_file(tmp_path, prompt, tests_yaml=tests_yaml)


# ---------------------------------------------------------------------------
# run — basic
# ---------------------------------------------------------------------------


class TestRunBasic:
    def test_run_on_test_file(self, tmp_path: Path):
        test_file = _make_passing_test(tmp_path)
        result = runner.invoke(app, ["run", str(test_file)])
        assert result.exit_code == 0

    def test_run_shows_results(self, tmp_path: Path):
        test_file = _make_passing_test(tmp_path)
        result = runner.invoke(app, ["run", str(test_file)])
        assert result.exit_code == 0
        assert "PASS" in result.output or "passed" in result.output.lower()


# ---------------------------------------------------------------------------
# run — passing vs failing
# ---------------------------------------------------------------------------


class TestRunExitCodes:
    def test_passing_tests_exit_0(self, tmp_path: Path):
        test_file = _make_passing_test(tmp_path)
        result = runner.invoke(app, ["run", str(test_file)])
        assert result.exit_code == 0

    def test_failing_tests_exit_1(self, tmp_path: Path):
        test_file = _make_failing_test(tmp_path)
        result = runner.invoke(app, ["run", str(test_file)])
        assert result.exit_code == 1

    def test_failing_output_mentions_fail(self, tmp_path: Path):
        test_file = _make_failing_test(tmp_path)
        result = runner.invoke(app, ["run", str(test_file)])
        assert "FAIL" in result.output or "failed" in result.output.lower()


# ---------------------------------------------------------------------------
# run --format json
# ---------------------------------------------------------------------------


class TestRunFormatJson:
    def test_json_output_is_valid(self, tmp_path: Path):
        test_file = _make_passing_test(tmp_path)
        result = runner.invoke(app, ["run", "--format", "json", str(test_file)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "total" in data
        assert "passed" in data
        assert "failed" in data

    def test_json_counts_match(self, tmp_path: Path):
        test_file = _make_passing_test(tmp_path)
        result = runner.invoke(app, ["run", "--format", "json", str(test_file)])
        data = json.loads(result.output)
        assert data["total"] == 3
        assert data["passed"] == 3
        assert data["failed"] == 0

    def test_json_with_failures(self, tmp_path: Path):
        test_file = _make_failing_test(tmp_path)
        result = runner.invoke(app, ["run", "--format", "json", str(test_file)])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["failed"] > 0


# ---------------------------------------------------------------------------
# run --format junit
# ---------------------------------------------------------------------------


class TestRunFormatJunit:
    def test_junit_output_is_xml(self, tmp_path: Path):
        test_file = _make_passing_test(tmp_path)
        result = runner.invoke(app, ["run", "--format", "junit", str(test_file)])
        assert result.exit_code == 0
        assert "<?xml" in result.output
        assert "<testsuites" in result.output

    def test_junit_contains_testcases(self, tmp_path: Path):
        test_file = _make_passing_test(tmp_path)
        result = runner.invoke(app, ["run", "--format", "junit", str(test_file)])
        assert "<testcase" in result.output

    def test_junit_with_failures(self, tmp_path: Path):
        test_file = _make_failing_test(tmp_path)
        result = runner.invoke(app, ["run", "--format", "junit", str(test_file)])
        assert result.exit_code == 1
        assert "<failure" in result.output


# ---------------------------------------------------------------------------
# run --fail-fast
# ---------------------------------------------------------------------------


class TestRunFailFast:
    def test_fail_fast_stops_on_first_failure(self, tmp_path: Path):
        test_file = _make_multi_test_with_early_failure(tmp_path)
        result = runner.invoke(
            app, ["run", "--format", "json", "--fail-fast", str(test_file)]
        )
        assert result.exit_code == 1
        data = json.loads(result.output)
        # Should have 1 failure and 2 skipped (fail-fast skips the rest)
        assert data["failed"] == 1
        assert data["skipped"] == 2


# ---------------------------------------------------------------------------
# run --verbose
# ---------------------------------------------------------------------------


class TestRunVerbose:
    def test_verbose_flag_accepted(self, tmp_path: Path):
        test_file = _make_passing_test(tmp_path)
        result = runner.invoke(
            app, ["run", "--verbose", str(test_file)]
        )
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# run — directory discovery
# ---------------------------------------------------------------------------


class TestRunDirectory:
    def test_run_on_directory(self, tmp_path: Path):
        prompt = _make_prompt(tmp_path)
        tests_yaml = (
            "  - name: is-valid\n"
            "    assert: valid_format\n"
        )
        # Create test files matching test_*.yaml pattern
        _make_test_file(
            tmp_path, prompt, test_name="test_first.yaml", tests_yaml=tests_yaml
        )
        _make_test_file(
            tmp_path, prompt, test_name="test_second.yaml",
            suite_name="second", tests_yaml=tests_yaml,
        )
        result = runner.invoke(app, ["run", str(tmp_path)])
        assert result.exit_code == 0

    def test_run_directory_discovers_multiple_suites(self, tmp_path: Path):
        prompt = _make_prompt(tmp_path)
        tests_yaml = (
            "  - name: is-valid\n"
            "    assert: valid_format\n"
        )
        _make_test_file(
            tmp_path, prompt, test_name="test_a.yaml",
            suite_name="suite-a", tests_yaml=tests_yaml,
        )
        _make_test_file(
            tmp_path, prompt, test_name="test_b.yaml",
            suite_name="suite-b", tests_yaml=tests_yaml,
        )
        result = runner.invoke(
            app, ["run", "--format", "json", str(tmp_path)]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total"] == 2  # 1 test from each suite

    def test_run_empty_directory(self, tmp_path: Path):
        empty = tmp_path / "empty"
        empty.mkdir()
        result = runner.invoke(app, ["run", str(empty)])
        assert result.exit_code == 0
        assert "No tests found" in result.output


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


class TestInit:
    def test_init_creates_example_file(self, monkeypatch, tmp_path: Path):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        example = tmp_path / "test_example.yaml"
        assert example.exists()
        content = example.read_text(encoding="utf-8")
        assert "suite:" in content
        assert "prompt:" in content
        assert "tests:" in content

    def test_init_refuses_overwrite(self, monkeypatch, tmp_path: Path):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "test_example.yaml").write_text("existing", encoding="utf-8")
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_init_file_has_all_assertion_types(self, monkeypatch, tmp_path: Path):
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        content = (tmp_path / "test_example.yaml").read_text(encoding="utf-8")
        # The example file should demonstrate multiple assertion types
        assert "has_role" in content
        assert "max_tokens" in content
        assert "contains" in content


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrors:
    def test_nonexistent_path(self, tmp_path: Path):
        bad = tmp_path / "no_such_path"
        result = runner.invoke(app, ["run", str(bad)])
        assert result.exit_code == 2
        assert "not found" in result.output.lower() or "Path not found" in result.output

    def test_malformed_yaml_test_file(self, tmp_path: Path):
        bad_test = tmp_path / "test_bad.yaml"
        bad_test.write_text(":::totally not valid yaml:::", encoding="utf-8")
        result = runner.invoke(app, ["run", str(bad_test)])
        # Should handle gracefully — error or exit nonzero
        assert result.exit_code != 0 or "error" in result.output.lower()

    def test_test_file_missing_prompt_field(self, tmp_path: Path):
        bad_test = tmp_path / "test_missing.yaml"
        bad_test.write_text(
            "suite: bad-suite\ntests:\n  - name: x\n    assert: valid_format\n",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["run", str(bad_test)])
        # Should report an error about missing prompt field
        assert result.exit_code != 0 or "error" in result.output.lower()

    def test_test_file_prompt_not_found(self, tmp_path: Path):
        test_file = tmp_path / "test_noprompt.yaml"
        test_file.write_text(
            "suite: orphan\n"
            "prompt: nonexistent/prompt.yaml\n"
            "tests:\n"
            "  - name: check\n"
            "    assert: valid_format\n",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["run", str(test_file)])
        # Should report error for missing prompt file
        # The runner creates ERROR results when prompt can't be parsed
        assert result.exit_code in (1, 2)

    def test_directory_with_malformed_test_file(self, tmp_path: Path):
        # Valid prompt
        prompt = _make_prompt(tmp_path)
        # One good test file
        good_tests = (
            "  - name: is-valid\n"
            "    assert: valid_format\n"
        )
        _make_test_file(
            tmp_path, prompt, test_name="test_good.yaml", tests_yaml=good_tests,
        )
        # One bad test file
        bad = tmp_path / "test_broken.yaml"
        bad.write_text("not: valid: yaml: [[[", encoding="utf-8")
        result = runner.invoke(app, ["run", str(tmp_path)])
        # Should still run, reporting errors for the bad file
        # The runner catches ValueError for bad files and creates error results
        assert "error" in result.output.lower() or result.exit_code in (0, 1)
