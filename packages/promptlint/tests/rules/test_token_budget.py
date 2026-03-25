"""Tests for token budget rules: PL001, PL002, PL003."""
from __future__ import annotations

from pathlib import Path

from promptlint.models import LintConfig, Message, PromptFile, PromptFormat, Severity
from promptlint.rules.token_budget import (
    TokenBudgetErrorRule,
    TokenBudgetWarnRule,
    TokenDensityLowRule,
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


class TestPL001TokenBudgetWarn:
    def test_fires_above_warn_below_error(self) -> None:
        config = LintConfig(token_warn_threshold=100, token_error_threshold=500)
        pf = _make_pf("x", total_tokens=250)
        violations = TokenBudgetWarnRule().check(pf, config)
        assert len(violations) == 1
        assert violations[0].rule_id == "PL001"
        assert violations[0].severity == Severity.WARNING

    def test_clean_below_threshold(self) -> None:
        config = LintConfig(token_warn_threshold=100, token_error_threshold=500)
        pf = _make_pf("x", total_tokens=50)
        violations = TokenBudgetWarnRule().check(pf, config)
        assert len(violations) == 0

    def test_does_not_fire_when_error_would(self) -> None:
        config = LintConfig(token_warn_threshold=100, token_error_threshold=500)
        pf = _make_pf("x", total_tokens=600)
        violations = TokenBudgetWarnRule().check(pf, config)
        assert len(violations) == 0


class TestPL002TokenBudgetError:
    def test_fires_above_error_threshold(self) -> None:
        config = LintConfig(token_error_threshold=500)
        pf = _make_pf("x", total_tokens=600)
        violations = TokenBudgetErrorRule().check(pf, config)
        assert len(violations) == 1
        assert violations[0].rule_id == "PL002"
        assert violations[0].severity == Severity.ERROR

    def test_clean_below_threshold(self) -> None:
        config = LintConfig(token_error_threshold=500)
        pf = _make_pf("x", total_tokens=400)
        violations = TokenBudgetErrorRule().check(pf, config)
        assert len(violations) == 0


class TestPL003TokenDensityLow:
    def test_fires_on_high_stop_words(self) -> None:
        # All stop words
        text = "the a an is was are were be been being have has had do does did"
        config = LintConfig(stop_word_ratio=0.60)
        pf = _make_pf(text)
        violations = TokenDensityLowRule().check(pf, config)
        assert len(violations) == 1
        assert violations[0].rule_id == "PL003"

    def test_clean_low_stop_words(self) -> None:
        text = "Analyze patent claims regarding semiconductor fabrication lithography processes"
        config = LintConfig(stop_word_ratio=0.60)
        pf = _make_pf(text)
        violations = TokenDensityLowRule().check(pf, config)
        assert len(violations) == 0
