"""Tests for hallucination rules: PL050, PL051, PL052, PL053, PL054."""
from __future__ import annotations

from pathlib import Path

from promptlint.models import LintConfig, Message, PromptFile, PromptFormat
from promptlint.rules.hallucination import (
    AsksForCitationsRule,
    AsksForSpecificNumbersRule,
    AsksForURLsRule,
    FabricationProneTaskRule,
    NoUncertaintyInstructionRule,
)


def _make_pf(content: str) -> PromptFile:
    return PromptFile(
        path=Path("test.txt"),
        format=PromptFormat.TEXT,
        raw_content=content,
        messages=[Message(role="user", content=content, line_start=1)],
    )


class TestPL050AsksForNumbers:
    def test_fires_no_data_source(self) -> None:
        pf = _make_pf("How many users signed up last month?")
        violations = AsksForSpecificNumbersRule().check(pf, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL050"

    def test_clean_has_data_source(self) -> None:
        pf = _make_pf("How many users signed up? Use the database to get this info.")
        violations = AsksForSpecificNumbersRule().check(pf, LintConfig())
        assert len(violations) == 0

    def test_clean_no_number_request(self) -> None:
        pf = _make_pf("Tell me about dogs.")
        violations = AsksForSpecificNumbersRule().check(pf, LintConfig())
        assert len(violations) == 0


class TestPL051AsksForURLs:
    def test_fires_no_search_tool(self) -> None:
        pf = _make_pf("Provide a URL for the documentation.")
        violations = AsksForURLsRule().check(pf, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL051"

    def test_clean_has_web_search(self) -> None:
        pf = _make_pf("Provide a URL for the documentation. You have web search access.")
        violations = AsksForURLsRule().check(pf, LintConfig())
        assert len(violations) == 0

    def test_clean_no_url_request(self) -> None:
        pf = _make_pf("Describe the architecture.")
        violations = AsksForURLsRule().check(pf, LintConfig())
        assert len(violations) == 0


class TestPL052AsksForCitations:
    def test_fires(self) -> None:
        pf = _make_pf("Cite your sources for each claim.")
        violations = AsksForCitationsRule().check(pf, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL052"

    def test_clean(self) -> None:
        pf = _make_pf("Summarize the topic briefly.")
        violations = AsksForCitationsRule().check(pf, LintConfig())
        assert len(violations) == 0


class TestPL053NoUncertainty:
    def test_fires_factual_no_uncertainty(self) -> None:
        pf = _make_pf("Analyze the market trends for Q4.")
        violations = NoUncertaintyInstructionRule().check(pf, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL053"

    def test_clean_has_uncertainty(self) -> None:
        pf = _make_pf("Analyze the market trends for Q4. If unsure, say so.")
        violations = NoUncertaintyInstructionRule().check(pf, LintConfig())
        assert len(violations) == 0

    def test_clean_not_factual(self) -> None:
        pf = _make_pf("Write a poem about cats.")
        violations = NoUncertaintyInstructionRule().check(pf, LintConfig())
        assert len(violations) == 0


class TestPL054FabricationProne:
    def test_fires(self) -> None:
        pf = _make_pf("Provide the patent number for the first smartphone.")
        violations = FabricationProneTaskRule().check(pf, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL054"

    def test_clean(self) -> None:
        pf = _make_pf("Explain how patents work in general terms.")
        violations = FabricationProneTaskRule().check(pf, LintConfig())
        assert len(violations) == 0
