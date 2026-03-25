"""Tests for PL090 approximate tokenizer warning."""

from __future__ import annotations

from pathlib import Path

from promptlint.models import LintConfig, Message, PromptFile, PromptFormat
from promptlint.rules.tokenizer_warnings import ApproximateTokenizerWarning


def _make_prompt(content: str = "Hello world") -> PromptFile:
    return PromptFile(
        path=Path("test.yaml"),
        format=PromptFormat.YAML,
        raw_content=content,
        messages=[Message(role="user", content=content, line_start=1)],
    )


class TestPL090ApproximateTokenizer:
    def test_fires_on_claude_model(self):
        rule = ApproximateTokenizerWarning()
        config = LintConfig(model="claude-3-sonnet")
        violations = rule.check(_make_prompt(), config)
        assert len(violations) == 1
        assert violations[0].rule_id == "PL090"
        assert "approximate" in violations[0].message.lower()
        assert "claude-3-sonnet" in violations[0].message

    def test_fires_on_gemini_model(self):
        rule = ApproximateTokenizerWarning()
        config = LintConfig(model="gemini-1.5-pro")
        violations = rule.check(_make_prompt(), config)
        assert len(violations) == 1
        assert "gemini-1.5-pro" in violations[0].message

    def test_clean_on_gpt4_model(self):
        rule = ApproximateTokenizerWarning()
        config = LintConfig(model="gpt-4")
        violations = rule.check(_make_prompt(), config)
        assert len(violations) == 0

    def test_clean_no_model(self):
        rule = ApproximateTokenizerWarning()
        config = LintConfig()
        violations = rule.check(_make_prompt(), config)
        assert len(violations) == 0

    def test_clean_unknown_model(self):
        rule = ApproximateTokenizerWarning()
        config = LintConfig(model="unknown-model-xyz")
        violations = rule.check(_make_prompt(), config)
        assert len(violations) == 0
