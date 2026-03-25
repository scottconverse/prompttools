"""Tests for prompttest report formatters."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import pytest

from prompttest.models import AssertionResult, AssertionType, TestReport, TestStatus
from prompttest.reporter import format_json, format_junit, format_text


@pytest.fixture
def sample_report() -> TestReport:
    """A report with mixed results for formatter testing."""
    return TestReport(
        suites=[
            {
                "suite_name": "greeting-tests",
                "prompt_path": "prompts/greeting.yaml",
                "results": [
                    {
                        "test_name": "has-system",
                        "status": "passed",
                        "assert_type": "has_role",
                        "message": "Prompt has 'system' message",
                        "expected": "system",
                        "actual": ["system", "user"],
                        "duration_ms": 0.5,
                    },
                    {
                        "test_name": "token-limit",
                        "status": "failed",
                        "assert_type": "max_tokens",
                        "message": "Token count 3000 exceeds limit of 2048",
                        "expected": 2048,
                        "actual": 3000,
                        "duration_ms": 1.2,
                    },
                    {
                        "test_name": "format-ok",
                        "status": "passed",
                        "assert_type": "valid_format",
                        "message": "Prompt has valid format",
                        "expected": None,
                        "actual": "yaml",
                        "duration_ms": 0.1,
                    },
                    {
                        "test_name": "cost-check",
                        "status": "error",
                        "assert_type": "max_cost",
                        "message": "Cost estimation failed: unknown model",
                        "expected": None,
                        "actual": None,
                        "duration_ms": 0.3,
                    },
                    {
                        "test_name": "future-test",
                        "status": "skipped",
                        "assert_type": "contains",
                        "message": "Not implemented yet",
                        "expected": None,
                        "actual": None,
                        "duration_ms": 0.0,
                    },
                ],
            },
        ],
        total=5,
        passed=2,
        failed=1,
        errors=1,
        skipped=1,
        duration_ms=2.1,
    )


@pytest.fixture
def empty_report() -> TestReport:
    """An empty report with no results."""
    return TestReport()


class TestFormatText:
    """Tests for text output formatting."""

    def test_contains_suite_name(self, sample_report: TestReport) -> None:
        output = format_text(sample_report)
        assert "greeting-tests" in output

    def test_contains_pass_indicator(self, sample_report: TestReport) -> None:
        output = format_text(sample_report)
        assert "PASS" in output

    def test_contains_fail_indicator(self, sample_report: TestReport) -> None:
        output = format_text(sample_report)
        assert "FAIL" in output

    def test_contains_error_indicator(self, sample_report: TestReport) -> None:
        output = format_text(sample_report)
        assert "ERR" in output

    def test_contains_skip_indicator(self, sample_report: TestReport) -> None:
        output = format_text(sample_report)
        assert "SKIP" in output

    def test_contains_summary(self, sample_report: TestReport) -> None:
        output = format_text(sample_report)
        assert "2 passed" in output
        assert "1 failed" in output
        assert "1 errors" in output
        assert "5 total" in output

    def test_contains_failure_message(self, sample_report: TestReport) -> None:
        output = format_text(sample_report)
        assert "exceeds limit" in output

    def test_empty_report(self, empty_report: TestReport) -> None:
        output = format_text(empty_report)
        assert "Results" in output


class TestFormatJson:
    """Tests for JSON output formatting."""

    def test_valid_json(self, sample_report: TestReport) -> None:
        output = format_json(sample_report)
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_json_fields(self, sample_report: TestReport) -> None:
        output = format_json(sample_report)
        data = json.loads(output)
        assert data["total"] == 5
        assert data["passed"] == 2
        assert data["failed"] == 1
        assert data["errors"] == 1
        assert data["skipped"] == 1
        assert data["duration_ms"] == 2.1

    def test_json_suites(self, sample_report: TestReport) -> None:
        output = format_json(sample_report)
        data = json.loads(output)
        assert len(data["suites"]) == 1
        assert data["suites"][0]["suite_name"] == "greeting-tests"
        assert len(data["suites"][0]["results"]) == 5

    def test_empty_json(self, empty_report: TestReport) -> None:
        output = format_json(empty_report)
        data = json.loads(output)
        assert data["total"] == 0


class TestFormatJunit:
    """Tests for JUnit XML output formatting."""

    def test_valid_xml(self, sample_report: TestReport) -> None:
        output = format_junit(sample_report)
        root = ET.fromstring(output)
        assert root.tag == "testsuites"

    def test_testsuites_attributes(self, sample_report: TestReport) -> None:
        output = format_junit(sample_report)
        root = ET.fromstring(output)
        assert root.get("tests") == "5"
        assert root.get("failures") == "1"
        assert root.get("errors") == "1"
        assert root.get("skipped") == "1"

    def test_testsuite_element(self, sample_report: TestReport) -> None:
        output = format_junit(sample_report)
        root = ET.fromstring(output)
        suites = root.findall("testsuite")
        assert len(suites) == 1
        assert suites[0].get("name") == "greeting-tests"

    def test_testcase_elements(self, sample_report: TestReport) -> None:
        output = format_junit(sample_report)
        root = ET.fromstring(output)
        testcases = root.findall(".//testcase")
        assert len(testcases) == 5

    def test_failure_element(self, sample_report: TestReport) -> None:
        output = format_junit(sample_report)
        root = ET.fromstring(output)
        failures = root.findall(".//failure")
        assert len(failures) == 1
        assert "exceeds limit" in failures[0].get("message", "")

    def test_error_element(self, sample_report: TestReport) -> None:
        output = format_junit(sample_report)
        root = ET.fromstring(output)
        errors = root.findall(".//error")
        assert len(errors) == 1

    def test_skipped_element(self, sample_report: TestReport) -> None:
        output = format_junit(sample_report)
        root = ET.fromstring(output)
        skipped = root.findall(".//skipped")
        assert len(skipped) == 1

    def test_xml_declaration(self, sample_report: TestReport) -> None:
        output = format_junit(sample_report)
        assert output.startswith('<?xml version="1.0"')

    def test_empty_junit(self, empty_report: TestReport) -> None:
        output = format_junit(empty_report)
        root = ET.fromstring(output)
        assert root.get("tests") == "0"
