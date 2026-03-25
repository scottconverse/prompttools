"""Tests for promptlint.core.engine."""
from __future__ import annotations

from pathlib import Path

from promptlint.core.engine import (
    _filter_violations,
    get_all_pipeline_rules,
    get_all_rules,
    lint_file,
    lint_pipeline,
)
from promptlint.models import (
    LintConfig,
    LintViolation,
    Message,
    PipelineStage,
    PromptFile,
    PromptFormat,
    PromptPipeline,
    Severity,
)


def _make_pf(content: str, role: str = "user", path: str = "test.yaml") -> PromptFile:
    return PromptFile(
        path=Path(path),
        format=PromptFormat.YAML,
        raw_content=content,
        messages=[Message(role=role, content=content, line_start=1)],
    )


# ---------------------------------------------------------------------------
# Rule discovery
# ---------------------------------------------------------------------------


class TestRuleDiscovery:
    def test_get_all_rules_returns_nonempty(self) -> None:
        rules = get_all_rules()
        assert len(rules) > 0

    def test_all_rules_have_rule_id(self) -> None:
        for rule in get_all_rules():
            assert hasattr(rule, "rule_id")
            assert rule.rule_id.startswith("PL")

    def test_get_all_pipeline_rules(self) -> None:
        rules = get_all_pipeline_rules()
        assert len(rules) > 0
        for rule in rules:
            assert rule.rule_id.startswith("PL04")


# ---------------------------------------------------------------------------
# Token counting via lint_file
# ---------------------------------------------------------------------------


class TestTokenCounting:
    def test_lint_file_populates_tokens(self) -> None:
        pf = _make_pf("Hello world this is a test.")
        config = LintConfig()
        lint_file(pf, config)
        assert pf.total_tokens is not None
        assert pf.total_tokens > 0
        assert pf.messages[0].token_count is not None


# ---------------------------------------------------------------------------
# lint_file
# ---------------------------------------------------------------------------


class TestLintFile:
    def test_lint_file_returns_violations(self) -> None:
        # A prompt with trailing whitespace should trigger PL020
        pf = PromptFile(
            path=Path("test.txt"),
            format=PromptFormat.TEXT,
            raw_content="hello   \nworld",
            messages=[Message(role="user", content="hello   \nworld", line_start=1)],
        )
        config = LintConfig()
        violations = lint_file(pf, config)
        rule_ids = [v.rule_id for v in violations]
        assert "PL020" in rule_ids

    def test_lint_file_severity_filtering(self) -> None:
        pf = _make_pf("hello   \nworld")
        pf.raw_content = "hello   \nworld"
        config = LintConfig()
        # PL020 is INFO, filter to WARNING+
        violations = lint_file(pf, config, min_severity="warning")
        pl020 = [v for v in violations if v.rule_id == "PL020"]
        assert len(pl020) == 0

    def test_lint_file_ignores_rule(self) -> None:
        pf = PromptFile(
            path=Path("test.txt"),
            format=PromptFormat.TEXT,
            raw_content="hello   \n",
            messages=[Message(role="user", content="hello   \n", line_start=1)],
        )
        config = LintConfig(ignored_rules=["PL020"])
        violations = lint_file(pf, config)
        assert all(v.rule_id != "PL020" for v in violations)


# ---------------------------------------------------------------------------
# lint_pipeline
# ---------------------------------------------------------------------------


class TestLintPipeline:
    def test_lint_pipeline_runs_file_and_pipeline_rules(self, tmp_path: Path) -> None:
        pf1 = PromptFile(
            path=tmp_path / "s1.txt",
            format=PromptFormat.TEXT,
            raw_content="Stage 1 content. Do not output personal info.",
            messages=[
                Message(role="user", content="Stage 1 content. Do not output personal info.", line_start=1)
            ],
        )
        pf2 = PromptFile(
            path=tmp_path / "s2.txt",
            format=PromptFormat.TEXT,
            raw_content="Stage 2 content. Do not hallucinate.",
            messages=[
                Message(role="user", content="Stage 2 content. Do not hallucinate.", line_start=1)
            ],
        )
        pipeline = PromptPipeline(
            name="test",
            stages=[
                PipelineStage(name="s1", prompt_file=pf1),
                PipelineStage(name="s2", prompt_file=pf2, depends_on=["s1"]),
            ],
            manifest_path=tmp_path / "manifest.yaml",
        )
        config = LintConfig()
        violations = lint_pipeline(pipeline, config)
        # Should produce some violations (pipeline + file-level)
        assert isinstance(violations, list)


# ---------------------------------------------------------------------------
# _filter_violations
# ---------------------------------------------------------------------------


class TestFilterViolations:
    def _make_violation(self, severity: Severity) -> LintViolation:
        return LintViolation(
            rule_id="PL999",
            severity=severity,
            message="test",
            path=Path("test.txt"),
            rule_name="test-rule",
        )

    def test_filter_info_passes_all(self) -> None:
        vs = [
            self._make_violation(Severity.INFO),
            self._make_violation(Severity.WARNING),
            self._make_violation(Severity.ERROR),
        ]
        result = _filter_violations(vs, LintConfig(), "info")
        assert len(result) == 3

    def test_filter_warning_excludes_info(self) -> None:
        vs = [
            self._make_violation(Severity.INFO),
            self._make_violation(Severity.WARNING),
        ]
        result = _filter_violations(vs, LintConfig(), "warning")
        assert len(result) == 1
        assert result[0].severity == Severity.WARNING

    def test_filter_error_only(self) -> None:
        vs = [
            self._make_violation(Severity.WARNING),
            self._make_violation(Severity.ERROR),
        ]
        result = _filter_violations(vs, LintConfig(), "error")
        assert len(result) == 1
        assert result[0].severity == Severity.ERROR
