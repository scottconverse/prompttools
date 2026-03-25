"""prompttest: Test framework for LLM prompt files.

Public API exports for convenience imports::

    from prompttest import TestCase, TestSuite, TestReport, run_test_file
"""

from prompttest.models import (
    AssertionResult,
    AssertionType,
    TestCase,
    TestReport,
    TestStatus,
    TestSuite,
)
from prompttest.assertions import run_assertion
from prompttest.runner import (
    discover_test_files,
    load_test_suite,
    run_test_directory,
    run_test_file,
    run_test_suite,
)
from prompttest.reporter import format_json, format_junit, format_text

__version__ = "1.0.0"

__all__ = [
    # Models
    "AssertionResult",
    "AssertionType",
    "TestCase",
    "TestReport",
    "TestStatus",
    "TestSuite",
    # Assertions
    "run_assertion",
    # Runner
    "discover_test_files",
    "load_test_suite",
    "run_test_directory",
    "run_test_file",
    "run_test_suite",
    # Reporter
    "format_json",
    "format_junit",
    "format_text",
]
