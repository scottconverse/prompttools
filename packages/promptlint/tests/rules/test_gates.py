"""Tests for gate/constraint rules: PL080, PL081, PL082, PL083."""
from __future__ import annotations

from pathlib import Path

from promptlint.models import LintConfig, Message, PromptFile, PromptFormat
from promptlint.rules.gates import (
    ClaimNoEvidenceGateRule,
    GateNoEnforcementRule,
    GateNoFallbackRule,
    OutputSchemaMissingRule,
)


def _make_pf(content: str) -> PromptFile:
    return PromptFile(
        path=Path("test.txt"),
        format=PromptFormat.TEXT,
        raw_content=content,
        messages=[Message(role="user", content=content, line_start=1)],
    )


class TestPL080GateNoEnforcement:
    def test_fires_conditional_no_enforcement(self) -> None:
        pf = _make_pf("If the input is missing, just guess the answer.")
        violations = GateNoEnforcementRule().check(pf, LintConfig())
        assert len(violations) >= 1
        assert violations[0].rule_id == "PL080"

    def test_clean_has_enforcement(self) -> None:
        pf = _make_pf("If the input is missing, do not proceed. Stop and ask the user.")
        violations = GateNoEnforcementRule().check(pf, LintConfig())
        assert len(violations) == 0

    def test_clean_no_conditional(self) -> None:
        pf = _make_pf("Summarize the following text.")
        violations = GateNoEnforcementRule().check(pf, LintConfig())
        assert len(violations) == 0


class TestPL081GateNoFallback:
    def test_fires_no_fallback(self) -> None:
        pf = _make_pf("You have access to the search API. Use it to find answers.")
        violations = GateNoFallbackRule().check(pf, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL081"

    def test_clean_has_fallback(self) -> None:
        pf = _make_pf(
            "You have access to the search API. "
            "If not available, explain that you cannot complete the request."
        )
        violations = GateNoFallbackRule().check(pf, LintConfig())
        assert len(violations) == 0

    def test_clean_no_capability(self) -> None:
        pf = _make_pf("Summarize the text below.")
        violations = GateNoFallbackRule().check(pf, LintConfig())
        assert len(violations) == 0


class TestPL082OutputSchemaMissing:
    def test_fires_format_no_schema(self) -> None:
        pf = _make_pf("Respond in JSON with the results.")
        violations = OutputSchemaMissingRule().check(pf, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL082"

    def test_clean_has_schema(self) -> None:
        pf = _make_pf(
            'Respond in JSON. Example output:\n```\n{"name": "test", "value": 42}\n```'
        )
        violations = OutputSchemaMissingRule().check(pf, LintConfig())
        assert len(violations) == 0

    def test_clean_no_format_spec(self) -> None:
        pf = _make_pf("Tell me about the topic.")
        violations = OutputSchemaMissingRule().check(pf, LintConfig())
        assert len(violations) == 0


class TestPL083ClaimNoEvidence:
    def test_fires_no_evidence(self) -> None:
        pf = _make_pf("Analyze the company's performance and recommend next steps.")
        violations = ClaimNoEvidenceGateRule().check(pf, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL083"

    def test_clean_has_evidence(self) -> None:
        pf = _make_pf(
            "Analyze the company's performance. "
            "Express confidence levels for each recommendation. "
            "Cite your source for each claim."
        )
        violations = ClaimNoEvidenceGateRule().check(pf, LintConfig())
        assert len(violations) == 0

    def test_clean_no_claims(self) -> None:
        pf = _make_pf("List the colors of the rainbow.")
        violations = ClaimNoEvidenceGateRule().check(pf, LintConfig())
        assert len(violations) == 0
