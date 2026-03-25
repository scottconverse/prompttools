"""Tests for prompttest data models."""

from __future__ import annotations

from pathlib import Path

import pytest

from prompttest.models import (
    AssertionResult,
    AssertionType,
    PromptTestCase,
    PromptTestReport,
    PromptTestStatus,
    PromptTestSuite,
)


class TestAssertionType:
    """Tests for the AssertionType enum."""

    def test_all_assertion_types_exist(self) -> None:
        expected = {
            "contains", "not_contains", "has_role", "has_variables",
            "max_tokens", "min_tokens", "max_messages", "min_messages",
            "max_cost", "valid_format", "matches_regex", "not_matches_regex",
            "token_ratio", "has_metadata", "content_hash",
        }
        actual = {t.value for t in AssertionType}
        assert actual == expected

    def test_enum_string_values(self) -> None:
        assert AssertionType.CONTAINS == "contains"
        assert AssertionType.MAX_COST == "max_cost"
        assert AssertionType.TOKEN_RATIO == "token_ratio"


class TestTestStatus:
    """Tests for the PromptTestStatus enum."""

    def test_all_statuses(self) -> None:
        assert set(PromptTestStatus) == {
            PromptTestStatus.PASSED,
            PromptTestStatus.FAILED,
            PromptTestStatus.ERROR,
            PromptTestStatus.SKIPPED,
        }


class TestTestCase:
    """Tests for the PromptTestCase model."""

    def test_create_from_alias(self) -> None:
        """The 'assert' alias should map to assert_type."""
        tc = PromptTestCase.model_validate({
            "name": "test-1",
            "assert": "contains",
            "text": "hello",
        })
        assert tc.name == "test-1"
        assert tc.assert_type == AssertionType.CONTAINS
        assert tc.text == "hello"

    def test_create_from_field_name(self) -> None:
        tc = PromptTestCase(name="test-2", assert_type=AssertionType.HAS_ROLE, role="system")
        assert tc.assert_type == AssertionType.HAS_ROLE
        assert tc.role == "system"

    def test_defaults(self) -> None:
        tc = PromptTestCase(name="test-3", assert_type=AssertionType.VALID_FORMAT)
        assert tc.text is None
        assert tc.role is None
        assert tc.variables is None
        assert tc.case_sensitive is False
        assert tc.skip is False
        assert tc.skip_reason is None

    def test_skip_fields(self) -> None:
        tc = PromptTestCase.model_validate({
            "name": "skipped-test",
            "assert": "contains",
            "text": "hello",
            "skip": True,
            "skip_reason": "Not ready yet",
        })
        assert tc.skip is True
        assert tc.skip_reason == "Not ready yet"

    def test_variables_list(self) -> None:
        tc = PromptTestCase.model_validate({
            "name": "var-test",
            "assert": "has_variables",
            "variables": ["user_name", "language"],
        })
        assert tc.variables == ["user_name", "language"]


class TestAssertionResult:
    """Tests for the AssertionResult model."""

    def test_passed_result(self) -> None:
        r = AssertionResult(
            test_name="test-1",
            status=PromptTestStatus.PASSED,
            assert_type=AssertionType.CONTAINS,
            message="Content contains 'hello'",
            expected="hello",
            duration_ms=1.5,
        )
        assert r.status == PromptTestStatus.PASSED
        assert r.duration_ms == 1.5

    def test_failed_result(self) -> None:
        r = AssertionResult(
            test_name="test-2",
            status=PromptTestStatus.FAILED,
            assert_type=AssertionType.MAX_TOKENS,
            message="Token count exceeds limit",
            expected=100,
            actual=200,
        )
        assert r.status == PromptTestStatus.FAILED
        assert r.expected == 100
        assert r.actual == 200

    def test_error_result(self) -> None:
        r = AssertionResult(
            test_name="test-3",
            status=PromptTestStatus.ERROR,
            assert_type=AssertionType.MAX_COST,
            message="Cost estimation failed",
        )
        assert r.status == PromptTestStatus.ERROR


class TestTestSuite:
    """Tests for the PromptTestSuite model."""

    def test_create_suite(self) -> None:
        suite = PromptTestSuite(
            name="my-suite",
            prompt_path=Path("prompts/test.yaml"),
            model="gpt-4o",
            tests=[
                PromptTestCase(name="t1", assert_type=AssertionType.VALID_FORMAT),
                PromptTestCase(name="t2", assert_type=AssertionType.CONTAINS, text="hello"),
            ],
        )
        assert suite.name == "my-suite"
        assert len(suite.tests) == 2
        assert suite.model == "gpt-4o"

    def test_suite_no_model(self) -> None:
        suite = PromptTestSuite(
            name="simple",
            prompt_path=Path("test.yaml"),
            tests=[],
        )
        assert suite.model is None


class TestTestReport:
    """Tests for the PromptTestReport model."""

    def test_empty_report(self) -> None:
        report = PromptTestReport()
        assert report.total == 0
        assert report.passed == 0
        assert report.failed == 0
        assert report.suites == []

    def test_report_with_data(self) -> None:
        report = PromptTestReport(
            suites=[{"suite_name": "s1", "prompt_path": "p.yaml", "results": []}],
            total=5,
            passed=3,
            failed=1,
            errors=1,
            duration_ms=100.0,
        )
        assert report.total == 5
        assert report.passed == 3
        assert report.failed == 1
        assert report.errors == 1
        assert report.duration_ms == 100.0
