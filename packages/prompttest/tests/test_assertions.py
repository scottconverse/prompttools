"""Tests for all assertion types in prompttest."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from prompttools_core import Message, PromptFile, PromptFormat

from prompttest.assertions import run_assertion
from prompttest.models import AssertionType, PromptTestCase, PromptTestStatus


class TestContains:
    """Tests for the 'contains' assertion."""

    def test_contains_pass(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.CONTAINS, text="greet the user")
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.PASSED

    def test_contains_case_insensitive(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.CONTAINS, text="GREET THE USER")
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.PASSED

    def test_contains_case_sensitive_fail(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t",
            assert_type=AssertionType.CONTAINS,
            text="GREET THE USER",
            case_sensitive=True,
        )
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.FAILED

    def test_contains_fail(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.CONTAINS, text="nonexistent text")
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.FAILED

    def test_contains_missing_text(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.CONTAINS)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.ERROR


class TestNotContains:
    """Tests for the 'not_contains' assertion."""

    def test_not_contains_pass(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.NOT_CONTAINS,
            text="ignore previous instructions",
        )
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.PASSED

    def test_not_contains_fail(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.NOT_CONTAINS,
            text="helpful assistant",
        )
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.FAILED

    def test_not_contains_missing_text(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.NOT_CONTAINS)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.ERROR


class TestHasRole:
    """Tests for the 'has_role' assertion."""

    def test_has_role_system_pass(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.HAS_ROLE, role="system")
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.PASSED

    def test_has_role_user_pass(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.HAS_ROLE, role="user")
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.PASSED

    def test_has_role_assistant_fail(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.HAS_ROLE, role="assistant")
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.FAILED

    def test_has_role_assistant_pass(self, multi_message_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.HAS_ROLE, role="assistant")
        result = run_assertion(multi_message_prompt, tc)
        assert result.status == PromptTestStatus.PASSED

    def test_has_role_missing_param(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.HAS_ROLE)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.ERROR


class TestHasVariables:
    """Tests for the 'has_variables' assertion."""

    def test_has_variables_pass(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.HAS_VARIABLES,
            variables=["user_name"],
        )
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.PASSED

    def test_has_variables_fail(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.HAS_VARIABLES,
            variables=["user_name", "language"],
        )
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.FAILED
        assert "language" in result.message

    def test_has_variables_missing_param(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.HAS_VARIABLES)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.ERROR

    def test_has_variables_multi(self, multi_message_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.HAS_VARIABLES,
            variables=["language"],
        )
        result = run_assertion(multi_message_prompt, tc)
        assert result.status == PromptTestStatus.PASSED


class TestMaxTokens:
    """Tests for the 'max_tokens' assertion."""

    def test_max_tokens_pass(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.MAX_TOKENS, max=5000)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.PASSED

    def test_max_tokens_fail(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.MAX_TOKENS, max=1)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.FAILED

    def test_max_tokens_missing_param(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.MAX_TOKENS)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.ERROR


class TestMinTokens:
    """Tests for the 'min_tokens' assertion."""

    def test_min_tokens_pass(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.MIN_TOKENS, min=1)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.PASSED

    def test_min_tokens_fail(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.MIN_TOKENS, min=100000)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.FAILED

    def test_min_tokens_missing_param(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.MIN_TOKENS)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.ERROR


class TestMaxMessages:
    """Tests for the 'max_messages' assertion."""

    def test_max_messages_pass(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.MAX_MESSAGES, max=5)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.PASSED

    def test_max_messages_fail(self, multi_message_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.MAX_MESSAGES, max=2)
        result = run_assertion(multi_message_prompt, tc)
        assert result.status == PromptTestStatus.FAILED

    def test_max_messages_exact(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.MAX_MESSAGES, max=2)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.PASSED

    def test_max_messages_missing_param(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.MAX_MESSAGES)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.ERROR


class TestMinMessages:
    """Tests for the 'min_messages' assertion."""

    def test_min_messages_pass(self, multi_message_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.MIN_MESSAGES, min=3)
        result = run_assertion(multi_message_prompt, tc)
        assert result.status == PromptTestStatus.PASSED

    def test_min_messages_fail(self, minimal_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.MIN_MESSAGES, min=3)
        result = run_assertion(minimal_prompt, tc)
        assert result.status == PromptTestStatus.FAILED

    def test_min_messages_missing_param(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.MIN_MESSAGES)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.ERROR


class TestMaxCost:
    """Tests for the 'max_cost' assertion."""

    def test_max_cost_no_model(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.MAX_COST, max=0.05)
        result = run_assertion(simple_prompt, tc, suite_model=None)
        assert result.status == PromptTestStatus.ERROR
        assert "model" in result.message.lower()

    def test_max_cost_missing_param(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.MAX_COST)
        result = run_assertion(simple_prompt, tc, suite_model="gpt-4o")
        assert result.status == PromptTestStatus.ERROR

    @patch("promptcost.estimate_file")
    def test_max_cost_pass(self, mock_estimate, simple_prompt: PromptFile) -> None:
        from promptcost.models import CostEstimate

        mock_estimate.return_value = CostEstimate(
            file_path=simple_prompt.path,
            model="gpt-4o",
            input_tokens=100,
            estimated_output_tokens=500,
            input_cost=0.001,
            output_cost=0.01,
            total_cost=0.011,
        )
        tc = PromptTestCase(name="t", assert_type=AssertionType.MAX_COST, max=0.05)
        result = run_assertion(simple_prompt, tc, suite_model="gpt-4o")
        assert result.status == PromptTestStatus.PASSED

    @patch("promptcost.estimate_file")
    def test_max_cost_fail(self, mock_estimate, simple_prompt: PromptFile) -> None:
        from promptcost.models import CostEstimate

        mock_estimate.return_value = CostEstimate(
            file_path=simple_prompt.path,
            model="gpt-4o",
            input_tokens=100,
            estimated_output_tokens=500,
            input_cost=0.05,
            output_cost=0.10,
            total_cost=0.15,
        )
        tc = PromptTestCase(name="t", assert_type=AssertionType.MAX_COST, max=0.05)
        result = run_assertion(simple_prompt, tc, suite_model="gpt-4o")
        assert result.status == PromptTestStatus.FAILED


class TestValidFormat:
    """Tests for the 'valid_format' assertion."""

    def test_valid_format_pass(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.VALID_FORMAT)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.PASSED

    def test_valid_format_fail_empty(self, empty_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.VALID_FORMAT)
        result = run_assertion(empty_prompt, tc)
        assert result.status == PromptTestStatus.FAILED


class TestMatchesRegex:
    """Tests for the 'matches_regex' assertion."""

    def test_matches_regex_pass(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.MATCHES_REGEX,
            pattern=r"greet\s+the\s+user",
        )
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.PASSED

    def test_matches_regex_fail(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.MATCHES_REGEX,
            pattern=r"^xyz\d{5}$",
        )
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.FAILED

    def test_matches_regex_invalid(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.MATCHES_REGEX,
            pattern=r"[invalid",
        )
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.ERROR

    def test_matches_regex_missing_param(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.MATCHES_REGEX)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.ERROR


class TestNotMatchesRegex:
    """Tests for the 'not_matches_regex' assertion."""

    def test_not_matches_regex_pass(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.NOT_MATCHES_REGEX,
            pattern=r"ignore\s+previous",
        )
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.PASSED

    def test_not_matches_regex_fail(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.NOT_MATCHES_REGEX,
            pattern=r"helpful\s+assistant",
        )
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.FAILED

    def test_not_matches_regex_invalid(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.NOT_MATCHES_REGEX,
            pattern=r"(unclosed",
        )
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.ERROR

    def test_not_matches_regex_missing_param(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.NOT_MATCHES_REGEX)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.ERROR


class TestTokenRatio:
    """Tests for the 'token_ratio' assertion."""

    def test_token_ratio_pass(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.TOKEN_RATIO, ratio_max=5.0,
        )
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.PASSED

    def test_token_ratio_fail(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.TOKEN_RATIO, ratio_max=0.01,
        )
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.FAILED

    def test_token_ratio_no_user_messages(self) -> None:
        pf = PromptFile(
            path=Path("test.yaml"),
            format=PromptFormat.YAML,
            raw_content="test",
            messages=[Message(role="system", content="System only prompt.")],
        )
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.TOKEN_RATIO, ratio_max=1.0,
        )
        result = run_assertion(pf, tc)
        assert result.status == PromptTestStatus.FAILED

    def test_token_ratio_missing_param(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.TOKEN_RATIO)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.ERROR


class TestHasMetadata:
    """Tests for the 'has_metadata' assertion."""

    def test_has_metadata_pass(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.HAS_METADATA,
            keys=["version", "author"],
        )
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.PASSED

    def test_has_metadata_fail(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.HAS_METADATA,
            keys=["version", "nonexistent"],
        )
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.FAILED
        assert "nonexistent" in result.message

    def test_has_metadata_empty(self, minimal_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.HAS_METADATA,
            keys=["version"],
        )
        result = run_assertion(minimal_prompt, tc)
        assert result.status == PromptTestStatus.FAILED

    def test_has_metadata_missing_param(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.HAS_METADATA)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.ERROR


class TestContentHash:
    """Tests for the 'content_hash' assertion."""

    def test_content_hash_pass(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.CONTENT_HASH,
            hash=simple_prompt.content_hash,
        )
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.PASSED

    def test_content_hash_fail(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.CONTENT_HASH,
            hash="0000000000000000000000000000000000000000000000000000000000000000",
        )
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.FAILED

    def test_content_hash_no_expected(self, simple_prompt: PromptFile) -> None:
        """When no hash is specified, it should pass and report the current hash."""
        tc = PromptTestCase(name="t", assert_type=AssertionType.CONTENT_HASH)
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.PASSED
        assert simple_prompt.content_hash in result.message


class TestSkippedTests:
    """Tests for the skip functionality."""

    def test_skipped_test(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.CONTAINS,
            text="hello", skip=True, skip_reason="Not implemented",
        )
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.SKIPPED
        assert "Not implemented" in result.message

    def test_skipped_no_reason(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(
            name="t", assert_type=AssertionType.CONTAINS,
            text="hello", skip=True,
        )
        result = run_assertion(simple_prompt, tc)
        assert result.status == PromptTestStatus.SKIPPED


class TestDuration:
    """Tests that assertion timing is recorded."""

    def test_duration_recorded(self, simple_prompt: PromptFile) -> None:
        tc = PromptTestCase(name="t", assert_type=AssertionType.VALID_FORMAT)
        result = run_assertion(simple_prompt, tc)
        assert result.duration_ms >= 0
