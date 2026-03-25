"""Tests for variable rules: PL030, PL031, PL032, PL033."""
from __future__ import annotations

from pathlib import Path

from promptlint.models import LintConfig, Message, PromptFile, PromptFormat
from promptlint.rules.variables import (
    UndefinedVariableRule,
    UnusedVariableRule,
    VariableFormatInconsistentRule,
    VariableNoDefaultRule,
)


def _make_pf(
    content: str,
    variables: dict[str, str] | None = None,
) -> PromptFile:
    return PromptFile(
        path=Path("test.txt"),
        format=PromptFormat.TEXT,
        raw_content=content,
        messages=[Message(role="user", content=content, line_start=1)],
        variables=variables or {},
    )


class TestPL030UndefinedVariable:
    def test_fires_on_undefined(self) -> None:
        # {{name}} is in content but not in variables
        pf = _make_pf("Hello {{name}}", variables={})
        violations = UndefinedVariableRule().check(pf, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL030"
        assert "name" in violations[0].message

    def test_clean_all_defined(self) -> None:
        pf = _make_pf("Hello {{name}}", variables={"name": "jinja"})
        violations = UndefinedVariableRule().check(pf, LintConfig())
        assert len(violations) == 0


class TestPL031UnusedVariable:
    def test_fires_on_unused(self) -> None:
        pf = _make_pf("Hello world", variables={"name": "jinja"})
        violations = UnusedVariableRule().check(pf, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL031"

    def test_clean_all_used(self) -> None:
        pf = _make_pf("Hello {{name}}", variables={"name": "jinja"})
        violations = UnusedVariableRule().check(pf, LintConfig())
        assert len(violations) == 0


class TestPL032VariableNoDefault:
    def test_fires_on_empty_value(self) -> None:
        pf = _make_pf("Hello {{name}}", variables={"name": ""})
        violations = VariableNoDefaultRule().check(pf, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL032"

    def test_clean_has_value(self) -> None:
        pf = _make_pf("Hello {{name}}", variables={"name": "jinja"})
        violations = VariableNoDefaultRule().check(pf, LintConfig())
        assert len(violations) == 0


class TestPL033VariableFormatInconsistent:
    def test_fires_on_mixed_formats(self) -> None:
        content = "Hello {{name}} and {age}"
        pf = _make_pf(content, variables={"name": "jinja", "age": "fstring"})
        violations = VariableFormatInconsistentRule().check(pf, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL033"
        assert violations[0].fixable is True

    def test_clean_single_format(self) -> None:
        pf = _make_pf("Hello {{name}} and {{age}}", variables={"name": "jinja", "age": "jinja"})
        violations = VariableFormatInconsistentRule().check(pf, LintConfig())
        assert len(violations) == 0

    def test_fix_normalizes(self) -> None:
        content = "Hello {name} and {{age}}"
        pf = _make_pf(content, variables={"name": "fstring", "age": "jinja"})
        rule = VariableFormatInconsistentRule()
        violations = rule.check(pf, LintConfig())
        assert len(violations) == 1
        fixed = rule.fix(pf, violations[0])
        assert fixed is not None
        assert "{{name}}" in fixed
        assert "{{age}}" in fixed
