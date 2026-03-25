"""Tests for the prompttest runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from prompttest.models import AssertionType, TestStatus
from prompttest.runner import (
    discover_test_files,
    load_test_suite,
    run_test_directory,
    run_test_file,
    run_test_suite,
)


class TestLoadTestSuite:
    """Tests for load_test_suite."""

    def test_load_valid_file(self, tmp_test_file: Path) -> None:
        suite = load_test_suite(tmp_test_file)
        assert suite.name == "greeting-tests"
        assert len(suite.tests) == 3
        assert suite.tests[0].assert_type == AssertionType.HAS_ROLE

    def test_load_nonexistent_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_test_suite(Path("nonexistent.yaml"))

    def test_load_invalid_yaml(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "test_bad.yaml"
        bad_file.write_text("{{invalid yaml", encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid YAML"):
            load_test_suite(bad_file)

    def test_load_missing_prompt_field(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_no_prompt.yaml"
        test_file.write_text(
            "suite: test\ntests:\n  - name: t\n    assert: valid_format\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="missing required 'prompt'"):
            load_test_suite(test_file)

    def test_load_not_a_mapping(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_list.yaml"
        test_file.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="must be a YAML mapping"):
            load_test_suite(test_file)

    def test_suite_name_defaults_to_stem(self, tmp_path: Path) -> None:
        prompt = tmp_path / "p.yaml"
        prompt.write_text(
            "messages:\n  - role: user\n    content: hi\n",
            encoding="utf-8",
        )
        test_file = tmp_path / "test_no_name.yaml"
        test_file.write_text(
            f"prompt: {prompt}\ntests:\n  - name: t\n    assert: valid_format\n",
            encoding="utf-8",
        )
        suite = load_test_suite(test_file)
        assert suite.name == "test_no_name"

    def test_relative_prompt_path(self, tmp_test_file: Path) -> None:
        suite = load_test_suite(tmp_test_file)
        # The prompt path should be resolved relative to the test file
        assert suite.prompt_path.is_absolute() or suite.prompt_path.parts[0] != ".."


class TestRunTestSuite:
    """Tests for run_test_suite."""

    def test_run_valid_suite(self, tmp_test_file: Path) -> None:
        suite = load_test_suite(tmp_test_file)
        results = run_test_suite(suite)
        assert len(results) == 3
        # has_role: system should pass, valid_format should pass, contains should pass
        for r in results:
            assert r.status == TestStatus.PASSED

    def test_run_missing_prompt(self, tmp_path: Path) -> None:
        """When the prompt file doesn't exist, all tests should error."""
        test_file = tmp_path / "test_missing.yaml"
        test_file.write_text(
            "suite: missing\n"
            "prompt: nonexistent.yaml\n"
            "tests:\n"
            "  - name: t1\n"
            "    assert: valid_format\n"
            "  - name: t2\n"
            "    assert: has_role\n"
            "    role: system\n",
            encoding="utf-8",
        )
        suite = load_test_suite(test_file)
        results = run_test_suite(suite)
        assert len(results) == 2
        assert all(r.status == TestStatus.ERROR for r in results)

    def test_fail_fast(self, tmp_path: Path) -> None:
        prompt = tmp_path / "p.yaml"
        prompt.write_text(
            "messages:\n  - role: user\n    content: hi\n",
            encoding="utf-8",
        )
        test_file = tmp_path / "test_ff.yaml"
        test_file.write_text(
            f"suite: ff\n"
            f"prompt: {prompt}\n"
            f"tests:\n"
            f"  - name: t1\n"
            f"    assert: has_role\n"
            f"    role: system\n"  # will fail - no system message
            f"  - name: t2\n"
            f"    assert: valid_format\n"
            f"  - name: t3\n"
            f"    assert: valid_format\n",
            encoding="utf-8",
        )
        suite = load_test_suite(test_file)
        results = run_test_suite(suite, fail_fast=True)
        assert len(results) == 3
        assert results[0].status == TestStatus.FAILED
        assert results[1].status == TestStatus.SKIPPED
        assert results[2].status == TestStatus.SKIPPED


class TestDiscoverTestFiles:
    """Tests for discover_test_files."""

    def test_discover_in_directory(self, tmp_path: Path) -> None:
        (tmp_path / "test_a.yaml").write_text("", encoding="utf-8")
        (tmp_path / "test_b.yaml").write_text("", encoding="utf-8")
        (tmp_path / "not_a_test.yaml").write_text("", encoding="utf-8")
        files = discover_test_files(tmp_path)
        assert len(files) == 2

    def test_discover_yml_extension(self, tmp_path: Path) -> None:
        (tmp_path / "test_c.yml").write_text("", encoding="utf-8")
        files = discover_test_files(tmp_path)
        assert len(files) == 1

    def test_discover_single_file(self, tmp_test_file: Path) -> None:
        files = discover_test_files(tmp_test_file)
        assert files == [tmp_test_file]

    def test_discover_nonexistent(self) -> None:
        files = discover_test_files(Path("nonexistent"))
        assert files == []

    def test_discover_nested(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "test_nested.yaml").write_text("", encoding="utf-8")
        files = discover_test_files(tmp_path)
        assert len(files) == 1


class TestRunTestFile:
    """Tests for run_test_file."""

    def test_run_file(self, tmp_test_file: Path) -> None:
        report = run_test_file(tmp_test_file)
        assert report.total == 3
        assert report.passed == 3
        assert report.failed == 0
        assert report.errors == 0
        assert report.duration_ms > 0


class TestRunTestDirectory:
    """Tests for run_test_directory."""

    def test_run_directory(self, tmp_path: Path, tmp_prompt_file: Path) -> None:
        # Create two test files
        rel_prompt = tmp_prompt_file.relative_to(tmp_path)
        for name in ["test_a.yaml", "test_b.yaml"]:
            (tmp_path / name).write_text(
                f"suite: {name}\n"
                f"prompt: {rel_prompt}\n"
                f"tests:\n"
                f"  - name: valid\n"
                f"    assert: valid_format\n",
                encoding="utf-8",
            )
        report = run_test_directory(tmp_path)
        assert report.total == 2
        assert report.passed == 2
        assert len(report.suites) == 2

    def test_run_empty_directory(self, tmp_path: Path) -> None:
        report = run_test_directory(tmp_path)
        assert report.total == 0

    def test_run_directory_with_bad_file(self, tmp_path: Path) -> None:
        """A broken test file should produce an error result, not crash."""
        (tmp_path / "test_broken.yaml").write_text(
            "not a valid test file\n",
            encoding="utf-8",
        )
        report = run_test_directory(tmp_path)
        assert report.errors >= 1
