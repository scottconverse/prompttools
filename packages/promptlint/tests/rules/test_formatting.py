"""Tests for formatting rules: PL020, PL021, PL022, PL023, PL024."""
from __future__ import annotations

from pathlib import Path

from promptlint.models import LintConfig, Message, PromptFile, PromptFormat
from promptlint.rules.formatting import (
    ExcessiveRepetitionRule,
    InconsistentDelimitersRule,
    LineTooLongRule,
    MissingOutputFormatRule,
    TrailingWhitespaceRule,
)


def _make_pf(content: str, raw: str | None = None) -> PromptFile:
    return PromptFile(
        path=Path("test.txt"),
        format=PromptFormat.TEXT,
        raw_content=raw if raw is not None else content,
        messages=[Message(role="user", content=content, line_start=1)],
    )


class TestPL020TrailingWhitespace:
    def test_fires(self) -> None:
        pf = _make_pf("hello", raw="hello   \nworld")
        violations = TrailingWhitespaceRule().check(pf, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL020"
        assert violations[0].fixable is True

    def test_clean(self) -> None:
        pf = _make_pf("hello\nworld", raw="hello\nworld")
        violations = TrailingWhitespaceRule().check(pf, LintConfig())
        assert len(violations) == 0


class TestPL021InconsistentDelimiters:
    def test_fires_on_mixed(self) -> None:
        text = "# Header\n---\n===\n<tag>content</tag>"
        pf = _make_pf(text)
        violations = InconsistentDelimitersRule().check(pf, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL021"

    def test_clean_single_style(self) -> None:
        text = "# Header\n## Sub\n### Sub-sub"
        pf = _make_pf(text)
        violations = InconsistentDelimitersRule().check(pf, LintConfig())
        assert len(violations) == 0


class TestPL022MissingOutputFormat:
    def test_fires_no_format(self) -> None:
        pf = _make_pf("Tell me about dogs.")
        violations = MissingOutputFormatRule().check(pf, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL022"

    def test_clean_has_format(self) -> None:
        pf = _make_pf("Respond in JSON format with the answer.")
        violations = MissingOutputFormatRule().check(pf, LintConfig())
        assert len(violations) == 0

    def test_clean_mentions_list(self) -> None:
        pf = _make_pf("Return a list of items.")
        violations = MissingOutputFormatRule().check(pf, LintConfig())
        assert len(violations) == 0


class TestPL023ExcessiveRepetition:
    def test_fires_on_repeated_phrase(self) -> None:
        phrase = "always check your work carefully"
        text = f"{phrase}.\n{phrase}.\n{phrase}.\n"
        pf = _make_pf(text)
        config = LintConfig(repetition_threshold=3)
        violations = ExcessiveRepetitionRule().check(pf, config)
        assert len(violations) == 1
        assert violations[0].rule_id == "PL023"

    def test_clean_no_repetition(self) -> None:
        pf = _make_pf("First instruction.\nSecond instruction.\nThird instruction.")
        violations = ExcessiveRepetitionRule().check(pf, LintConfig())
        assert len(violations) == 0


class TestPL024LineTooLong:
    def test_fires_on_long_line(self) -> None:
        text = "x" * 600
        pf = _make_pf(text, raw=text)
        config = LintConfig(max_line_length=500)
        violations = LineTooLongRule().check(pf, config)
        assert len(violations) == 1
        assert violations[0].rule_id == "PL024"

    def test_clean_short_lines(self) -> None:
        pf = _make_pf("Short line.\nAnother short line.", raw="Short line.\nAnother short line.")
        violations = LineTooLongRule().check(pf, LintConfig())
        assert len(violations) == 0
