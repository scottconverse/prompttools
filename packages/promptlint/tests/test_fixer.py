"""Tests for promptlint.core.fixer."""
from __future__ import annotations

from pathlib import Path

from promptlint.core.engine import get_all_rules, lint_file
from promptlint.core.fixer import apply_fixes
from promptlint.models import LintConfig, Message, PromptFile, PromptFormat


def _make_file(tmp_path: Path, name: str, content: str) -> Path:
    f = tmp_path / name
    f.write_text(content, encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# PL020 trailing whitespace fix
# ---------------------------------------------------------------------------


class TestFixTrailingWhitespace:
    def test_fix_writes_stripped_content(self, tmp_path: Path) -> None:
        content = "hello   \nworld  \n"
        fp = _make_file(tmp_path, "prompt.txt", content)
        pf = PromptFile(
            path=fp,
            format=PromptFormat.TEXT,
            raw_content=content,
            messages=[Message(role="user", content=content, line_start=1)],
        )
        config = LintConfig()
        violations = lint_file(pf, config)
        fixable = [v for v in violations if v.rule_id == "PL020"]
        assert len(fixable) > 0

        rules = get_all_rules(config)
        summary = apply_fixes(violations, rules, dry_run=False)
        fixed = fp.read_text(encoding="utf-8")
        assert "hello   \n" not in fixed
        assert "hello\n" in fixed
        assert any("fixed" in s for s in summary)

    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        content = "hello   \n"
        fp = _make_file(tmp_path, "prompt.txt", content)
        pf = PromptFile(
            path=fp,
            format=PromptFormat.TEXT,
            raw_content=content,
            messages=[Message(role="user", content=content, line_start=1)],
        )
        config = LintConfig()
        violations = lint_file(pf, config)
        rules = get_all_rules(config)
        summary = apply_fixes(violations, rules, dry_run=True)
        # File should still have trailing whitespace
        assert fp.read_text(encoding="utf-8") == content
        assert any("dry-run" in s for s in summary)


# ---------------------------------------------------------------------------
# PL033 variable normalization fix
# ---------------------------------------------------------------------------


class TestFixVariableNormalization:
    def test_fix_normalizes_to_jinja(self, tmp_path: Path) -> None:
        content = "Hello {name}, your id is {{order_id}}."
        fp = _make_file(tmp_path, "prompt.txt", content)
        pf = PromptFile(
            path=fp,
            format=PromptFormat.TEXT,
            raw_content=content,
            messages=[Message(role="user", content=content, line_start=1)],
            variables={"name": "fstring", "order_id": "jinja"},
        )
        config = LintConfig()
        violations = lint_file(pf, config)
        pl033 = [v for v in violations if v.rule_id == "PL033"]
        assert len(pl033) > 0

        rules = get_all_rules(config)
        summary = apply_fixes(violations, rules, dry_run=False)
        fixed = fp.read_text(encoding="utf-8")
        assert "{{name}}" in fixed
        assert "{{order_id}}" in fixed


# ---------------------------------------------------------------------------
# No fixable violations
# ---------------------------------------------------------------------------


class TestNoFixable:
    def test_no_fixable_returns_message(self) -> None:
        from promptlint.models import LintViolation, Severity

        violation = LintViolation(
            rule_id="PL001",
            severity=Severity.WARNING,
            message="test",
            path=Path("test.txt"),
            rule_name="test-rule",
            fixable=False,
        )
        rules = get_all_rules()
        summary = apply_fixes([violation], rules)
        assert any("No fixable" in s for s in summary)
