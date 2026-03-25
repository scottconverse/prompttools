"""Tests for prompt smell rules: PL070, PL071, PL072, PL073, PL074."""
from __future__ import annotations

from pathlib import Path

from promptlint.models import LintConfig, Message, PromptFile, PromptFormat
from promptlint.rules.smells import (
    AmbiguousQuantifierRule,
    CompetingInstructionsRule,
    InstructionBuriedRule,
    NoExamplesRule,
    WallOfTextRule,
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


class TestPL070AmbiguousQuantifier:
    def test_fires(self) -> None:
        pf = _make_pf("Please provide some examples of best practices.")
        violations = AmbiguousQuantifierRule().check(pf, LintConfig())
        assert len(violations) >= 1
        assert violations[0].rule_id == "PL070"

    def test_clean(self) -> None:
        pf = _make_pf("Provide 3 examples of best practices.")
        violations = AmbiguousQuantifierRule().check(pf, LintConfig())
        assert len(violations) == 0


class TestPL071InstructionBuried:
    def test_fires_critical_past_75pct(self) -> None:
        filler = "This is some filler text. " * 50
        text = filler + "IMPORTANT: always verify the output."
        pf = _make_pf(text, total_tokens=300)
        violations = InstructionBuriedRule().check(pf, LintConfig())
        assert len(violations) >= 1
        assert violations[0].rule_id == "PL071"

    def test_clean_critical_early(self) -> None:
        text = "IMPORTANT: verify output first.\n" + "Some other instructions. " * 20
        pf = _make_pf(text, total_tokens=300)
        violations = InstructionBuriedRule().check(pf, LintConfig())
        assert len(violations) == 0


class TestPL072CompetingInstructions:
    def test_fires_on_contradiction(self) -> None:
        pf = _make_pf("Be concise. Also be thorough and detailed in your response.")
        violations = CompetingInstructionsRule().check(pf, LintConfig())
        assert len(violations) >= 1
        assert violations[0].rule_id == "PL072"

    def test_clean(self) -> None:
        pf = _make_pf("Be helpful. Be polite.")
        violations = CompetingInstructionsRule().check(pf, LintConfig())
        assert len(violations) == 0


class TestPL073NoExamples:
    def test_fires_long_no_examples(self) -> None:
        text = "Describe the process step by step. " * 30
        pf = _make_pf(text, total_tokens=600)
        violations = NoExamplesRule().check(pf, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL073"

    def test_clean_has_example(self) -> None:
        text = "Process the data. For example, if X then Y. " * 20
        pf = _make_pf(text, total_tokens=600)
        violations = NoExamplesRule().check(pf, LintConfig())
        assert len(violations) == 0

    def test_clean_short_prompt(self) -> None:
        pf = _make_pf("Hello.", total_tokens=5)
        violations = NoExamplesRule().check(pf, LintConfig())
        assert len(violations) == 0


class TestPL074WallOfText:
    def test_fires_no_structure(self) -> None:
        text = "Write a comprehensive analysis of the semiconductor industry including all major players and their market positions and future outlook and technological developments. " * 10
        pf = _make_pf(text, total_tokens=300)
        violations = WallOfTextRule().check(pf, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL074"

    def test_clean_has_structure(self) -> None:
        text = "# Analysis\n- Point one\n- Point two\n" + "Details here. " * 50
        pf = _make_pf(text, total_tokens=300)
        violations = WallOfTextRule().check(pf, LintConfig())
        assert len(violations) == 0

    def test_clean_short(self) -> None:
        pf = _make_pf("Short prompt.", total_tokens=5)
        violations = WallOfTextRule().check(pf, LintConfig())
        assert len(violations) == 0
