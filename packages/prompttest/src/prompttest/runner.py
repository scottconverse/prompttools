"""Test execution engine for prompttest.

Discovers, loads, and runs YAML test files against prompt files,
producing structured test reports.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import yaml

from prompttools_core import PromptFile, parse_file
from prompttools_core.errors import ParseError

from prompttest.assertions import run_assertion
from prompttest.models import (
    AssertionResult,
    AssertionType,
    TestCase,
    TestReport,
    TestStatus,
    TestSuite,
)


def load_test_suite(path: Path) -> TestSuite:
    """Parse a YAML test file into a TestSuite.

    Parameters
    ----------
    path:
        Path to the YAML test file.

    Returns
    -------
    TestSuite

    Raises
    ------
    FileNotFoundError
        If the test file does not exist.
    ValueError
        If the YAML is malformed or missing required fields.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Test file not found: {path}")

    content = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in test file {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Test file {path} must be a YAML mapping")

    suite_name = data.get("suite", path.stem)
    prompt_path_str = data.get("prompt")
    if not prompt_path_str:
        raise ValueError(f"Test file {path} is missing required 'prompt' field")

    # Resolve prompt path relative to the test file's directory
    prompt_path = Path(prompt_path_str)
    if not prompt_path.is_absolute():
        prompt_path = path.parent / prompt_path

    suite_model = data.get("model")

    tests_raw = data.get("tests", [])
    if not isinstance(tests_raw, list):
        raise ValueError(f"'tests' in {path} must be a list")

    test_cases: list[TestCase] = []
    for entry in tests_raw:
        if not isinstance(entry, dict):
            raise ValueError(f"Each test in {path} must be a mapping, got: {type(entry)}")
        try:
            tc = TestCase.model_validate(entry)
            test_cases.append(tc)
        except Exception as exc:
            raise ValueError(
                f"Invalid test case in {path}: {entry.get('name', '???')}: {exc}"
            ) from exc

    return TestSuite(
        name=suite_name,
        prompt_path=prompt_path,
        model=suite_model,
        tests=test_cases,
    )


def run_test_suite(
    suite: TestSuite,
    fail_fast: bool = False,
    model_override: Optional[str] = None,
) -> list[AssertionResult]:
    """Execute all tests in a suite against its prompt file.

    Parameters
    ----------
    suite:
        The test suite to run.
    fail_fast:
        If True, stop after the first failure.
    model_override:
        If provided, overrides the suite-level model for cost/token assertions.

    Returns
    -------
    list[AssertionResult]
    """
    # Parse the prompt file
    try:
        prompt_file = parse_file(suite.prompt_path)
    except (ParseError, FileNotFoundError) as exc:
        # Return ERROR results for all tests if the prompt can't be parsed
        return [
            AssertionResult(
                test_name=tc.name,
                status=TestStatus.ERROR,
                assert_type=tc.assert_type,
                message=f"Failed to parse prompt file: {exc}",
            )
            for tc in suite.tests
        ]

    effective_model = model_override or suite.model

    results: list[AssertionResult] = []
    for tc in suite.tests:
        result = run_assertion(prompt_file, tc, effective_model)
        results.append(result)

        if fail_fast and result.status == TestStatus.FAILED:
            # Mark remaining tests as skipped
            for remaining_tc in suite.tests[len(results):]:
                results.append(
                    AssertionResult(
                        test_name=remaining_tc.name,
                        status=TestStatus.SKIPPED,
                        assert_type=remaining_tc.assert_type,
                        message="Skipped due to --fail-fast",
                    )
                )
            break

    return results


def _build_report(
    suite_results: list[tuple[TestSuite, list[AssertionResult]]],
    total_duration_ms: float,
) -> TestReport:
    """Build a TestReport from suite results."""
    suites_data: list[dict] = []
    total = passed = failed = errors = skipped = 0

    for suite, results in suite_results:
        suite_dict = {
            "suite_name": suite.name,
            "prompt_path": str(suite.prompt_path),
            "results": [r.model_dump() for r in results],
        }
        suites_data.append(suite_dict)

        for r in results:
            total += 1
            if r.status == TestStatus.PASSED:
                passed += 1
            elif r.status == TestStatus.FAILED:
                failed += 1
            elif r.status == TestStatus.ERROR:
                errors += 1
            elif r.status == TestStatus.SKIPPED:
                skipped += 1

    return TestReport(
        suites=suites_data,
        total=total,
        passed=passed,
        failed=failed,
        errors=errors,
        skipped=skipped,
        duration_ms=total_duration_ms,
    )


def run_test_file(
    path: Path,
    fail_fast: bool = False,
    model_override: Optional[str] = None,
) -> TestReport:
    """Load and run a single test file.

    Parameters
    ----------
    path:
        Path to a YAML test file.
    fail_fast:
        Stop after first failure.
    model_override:
        If provided, overrides the suite-level model.

    Returns
    -------
    TestReport
    """
    start = time.perf_counter()
    suite = load_test_suite(path)
    results = run_test_suite(suite, fail_fast=fail_fast, model_override=model_override)
    elapsed = (time.perf_counter() - start) * 1000

    return _build_report([(suite, results)], elapsed)


def discover_test_files(path: Path, pattern: str = "test_*.yaml") -> list[Path]:
    """Find test files matching a pattern within a directory.

    Parameters
    ----------
    path:
        Directory to search.
    pattern:
        Glob pattern for test files. Default: ``test_*.yaml``.

    Returns
    -------
    list[Path]
        Sorted list of matching test file paths.
    """
    path = Path(path)
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []

    files: list[Path] = []
    # Always search both .yaml and .yml variants
    patterns = {pattern}
    if ".yaml" in pattern:
        patterns.add(pattern.replace(".yaml", ".yml"))
    elif ".yml" in pattern:
        patterns.add(pattern.replace(".yml", ".yaml"))
    else:
        # Pattern doesn't specify extension; search both common extensions
        patterns.add(pattern.rstrip("*") + "*.yaml" if not pattern.endswith(".yaml") else pattern)
        patterns.add(pattern.rstrip("*") + "*.yml" if not pattern.endswith(".yml") else pattern)

    for pat in patterns:
        files.extend(path.rglob(pat))

    return sorted(set(files))


def run_test_directory(
    path: Path,
    fail_fast: bool = False,
    pattern: str = "test_*.yaml",
    model_override: Optional[str] = None,
) -> TestReport:
    """Discover and run all test files in a directory.

    Parameters
    ----------
    path:
        Directory to scan for test files.
    fail_fast:
        Stop after first failure in each suite.
    pattern:
        Glob pattern for test files.
    model_override:
        If provided, overrides the suite-level model.

    Returns
    -------
    TestReport
    """
    start = time.perf_counter()

    test_files = discover_test_files(path, pattern)
    suite_results: list[tuple[TestSuite, list[AssertionResult]]] = []

    for test_file in test_files:
        try:
            suite = load_test_suite(test_file)
        except (FileNotFoundError, ValueError) as exc:
            # Create a synthetic error suite
            error_suite = TestSuite(
                name=test_file.stem,
                prompt_path=Path("unknown"),
                tests=[],
            )
            error_result = AssertionResult(
                test_name=f"load:{test_file.name}",
                status=TestStatus.ERROR,
                assert_type=AssertionType.VALID_FORMAT,
                message=f"Failed to load test file: {exc}",
            )
            suite_results.append((error_suite, [error_result]))
            continue

        results = run_test_suite(suite, fail_fast=fail_fast, model_override=model_override)
        suite_results.append((suite, results))

    elapsed = (time.perf_counter() - start) * 1000
    return _build_report(suite_results, elapsed)
