"""Tests for security rules: PL060, PL061, PL062, PL063."""
from __future__ import annotations

from pathlib import Path

from promptlint.models import LintConfig, Message, PromptFile, PromptFormat
from promptlint.rules.security import (
    HardcodedAPIKeyRule,
    NoOutputConstraintsRule,
    PIIInPromptRule,
    UnboundedToolUseRule,
)


def _make_pf(content: str, total_tokens: int | None = None) -> PromptFile:
    pf = PromptFile(
        path=Path("test.txt"),
        format=PromptFormat.TEXT,
        raw_content=content,
        messages=[Message(role="user", content=content, line_start=1)],
    )
    pf.total_tokens = total_tokens
    return pf


class TestPL060PIIInPrompt:
    def test_fires_on_email(self) -> None:
        pf = _make_pf("Contact john@example.com for details.")
        violations = PIIInPromptRule().check(pf, LintConfig())
        assert any(v.rule_id == "PL060" and "email" in v.message for v in violations)

    def test_fires_on_phone(self) -> None:
        pf = _make_pf("Call 555-123-4567 for support.")
        violations = PIIInPromptRule().check(pf, LintConfig())
        assert any(v.rule_id == "PL060" and "phone" in v.message for v in violations)

    def test_fires_on_ssn(self) -> None:
        pf = _make_pf("SSN is 123-45-6789.")
        violations = PIIInPromptRule().check(pf, LintConfig())
        assert any(v.rule_id == "PL060" and "SSN" in v.message for v in violations)

    def test_clean(self) -> None:
        pf = _make_pf("Use {{email}} as the contact address.")
        violations = PIIInPromptRule().check(pf, LintConfig())
        assert all(v.rule_id != "PL060" for v in violations)


class TestPL061HardcodedAPIKey:
    def test_fires_on_openai_key(self) -> None:
        pf = _make_pf("Use key sk-abcdefghijklmnopqrstuvwx for the API.")
        violations = HardcodedAPIKeyRule().check(pf, LintConfig())
        assert any(v.rule_id == "PL061" for v in violations)

    def test_fires_on_bearer_token(self) -> None:
        pf = _make_pf("Auth: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test")
        violations = HardcodedAPIKeyRule().check(pf, LintConfig())
        assert any(v.rule_id == "PL061" for v in violations)

    def test_fires_on_generic_secret(self) -> None:
        pf = _make_pf("secret: abcdefghijklmnopqrstuvwxyz1234567890")
        violations = HardcodedAPIKeyRule().check(pf, LintConfig())
        assert any(v.rule_id == "PL061" for v in violations)

    def test_fires_on_anthropic_key(self) -> None:
        pf = _make_pf("Use this key: sk-ant-api03-xxxxxxxxxxxxxxxxxxxx to authenticate.")
        violations = HardcodedAPIKeyRule().check(pf, LintConfig())
        assert any(v.rule_id == "PL061" for v in violations)

    def test_fires_on_groq_key(self) -> None:
        pf = _make_pf("Set GROQ_API_KEY=gsk_abcdefghijklmnopqrstuvwx for inference.")
        violations = HardcodedAPIKeyRule().check(pf, LintConfig())
        assert any(v.rule_id == "PL061" for v in violations)

    def test_fires_on_gitlab_token(self) -> None:
        pf = _make_pf("Use token glpat-xxxxxxxxxxxxxxxxxxxx for GitLab API access.")
        violations = HardcodedAPIKeyRule().check(pf, LintConfig())
        assert any(v.rule_id == "PL061" for v in violations)

    def test_clean(self) -> None:
        pf = _make_pf("Use the {{api_key}} variable for authentication.")
        violations = HardcodedAPIKeyRule().check(pf, LintConfig())
        assert all(v.rule_id != "PL061" for v in violations)


class TestPL062NoOutputConstraints:
    def test_fires_no_constraints(self) -> None:
        pf = _make_pf(
            "Write a long essay about the history of computing. " * 10,
            total_tokens=500,
        )
        violations = NoOutputConstraintsRule().check(pf, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL062"

    def test_clean_has_constraints(self) -> None:
        pf = _make_pf(
            "Write an essay. Do not include personal opinions.",
            total_tokens=500,
        )
        violations = NoOutputConstraintsRule().check(pf, LintConfig())
        assert len(violations) == 0

    def test_clean_short_prompt(self) -> None:
        pf = _make_pf("Hello.", total_tokens=5)
        violations = NoOutputConstraintsRule().check(pf, LintConfig())
        assert len(violations) == 0


class TestPL063UnboundedToolUse:
    def test_fires_no_constraint(self) -> None:
        pf = _make_pf("You have access to the search tool. Use tools to find info.")
        violations = UnboundedToolUseRule().check(pf, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL063"

    def test_clean_has_constraint(self) -> None:
        pf = _make_pf("You have access to tools. Only when the user asks, use tools. Confirm before executing.")
        violations = UnboundedToolUseRule().check(pf, LintConfig())
        assert len(violations) == 0

    def test_clean_no_tool_access(self) -> None:
        pf = _make_pf("Summarize the text below.")
        violations = UnboundedToolUseRule().check(pf, LintConfig())
        assert len(violations) == 0
