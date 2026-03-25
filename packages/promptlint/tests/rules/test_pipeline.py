"""Tests for pipeline rules: PL040, PL041, PL042, PL043."""
from __future__ import annotations

from pathlib import Path

from promptlint.models import (
    LintConfig,
    Message,
    PipelineStage,
    PromptFile,
    PromptFormat,
    PromptPipeline,
)
from promptlint.rules.pipeline import (
    PipelineContextGrowthRule,
    PipelineInconsistentPersonaRule,
    PipelineNoHandoffRule,
    PipelineOrphanReferenceRule,
)


def _make_pf(content: str, path: str = "stage.txt", total_tokens: int | None = None) -> PromptFile:
    pf = PromptFile(
        path=Path(path),
        format=PromptFormat.TEXT,
        raw_content=content,
        messages=[Message(role="user", content=content, line_start=1)],
    )
    pf.total_tokens = total_tokens
    return pf


def _make_pipeline(
    stages: list[PipelineStage],
    manifest: str = "manifest.yaml",
) -> PromptPipeline:
    return PromptPipeline(
        name="test",
        stages=stages,
        manifest_path=Path(manifest),
    )


class TestPL040NoHandoff:
    def test_fires_no_handoff_reference(self) -> None:
        s1 = PipelineStage(name="s1", prompt_file=_make_pf("Do step one."))
        s2 = PipelineStage(
            name="s2",
            prompt_file=_make_pf("Do step two independently."),
            depends_on=["s1"],
        )
        pipeline = _make_pipeline([s1, s2])
        violations = PipelineNoHandoffRule().check_pipeline(pipeline, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL040"

    def test_clean_has_handoff(self) -> None:
        s1 = PipelineStage(name="s1", prompt_file=_make_pf("Do step one."))
        s2 = PipelineStage(
            name="s2",
            prompt_file=_make_pf("Based on the previous output, summarize."),
            depends_on=["s1"],
        )
        pipeline = _make_pipeline([s1, s2])
        violations = PipelineNoHandoffRule().check_pipeline(pipeline, LintConfig())
        assert len(violations) == 0

    def test_clean_references_stage_name(self) -> None:
        s1 = PipelineStage(name="research", prompt_file=_make_pf("Do research."))
        s2 = PipelineStage(
            name="report",
            prompt_file=_make_pf("Using the research results, write a report."),
            depends_on=["research"],
        )
        pipeline = _make_pipeline([s1, s2])
        violations = PipelineNoHandoffRule().check_pipeline(pipeline, LintConfig())
        assert len(violations) == 0


class TestPL041ContextGrowth:
    def test_fires_exceeds_context_window(self) -> None:
        s1 = PipelineStage(
            name="s1",
            prompt_file=_make_pf("Big prompt.", total_tokens=5000),
            expected_output_tokens=10000,
        )
        s2 = PipelineStage(
            name="s2",
            prompt_file=_make_pf("Another prompt.", total_tokens=5000),
            depends_on=["s1"],
        )
        pipeline = _make_pipeline([s1, s2])
        config = LintConfig(context_window=8000)
        violations = PipelineContextGrowthRule().check_pipeline(pipeline, config)
        assert len(violations) == 1
        assert violations[0].rule_id == "PL041"

    def test_clean_within_window(self) -> None:
        s1 = PipelineStage(
            name="s1",
            prompt_file=_make_pf("Small.", total_tokens=100),
            expected_output_tokens=200,
        )
        s2 = PipelineStage(
            name="s2",
            prompt_file=_make_pf("Also small.", total_tokens=100),
            depends_on=["s1"],
        )
        pipeline = _make_pipeline([s1, s2])
        config = LintConfig(context_window=8000)
        violations = PipelineContextGrowthRule().check_pipeline(pipeline, config)
        assert len(violations) == 0

    def test_no_context_window_skips(self) -> None:
        s1 = PipelineStage(name="s1", prompt_file=_make_pf("x", total_tokens=99999))
        pipeline = _make_pipeline([s1])
        violations = PipelineContextGrowthRule().check_pipeline(pipeline, LintConfig())
        assert len(violations) == 0


class TestPL042OrphanReference:
    def test_fires_on_nonexistent_dep(self) -> None:
        s1 = PipelineStage(name="s1", prompt_file=_make_pf("Step 1."))
        s2 = PipelineStage(
            name="s2",
            prompt_file=_make_pf("Step 2."),
            depends_on=["nonexistent"],
        )
        pipeline = _make_pipeline([s1, s2])
        violations = PipelineOrphanReferenceRule().check_pipeline(pipeline, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL042"

    def test_clean_valid_deps(self) -> None:
        s1 = PipelineStage(name="s1", prompt_file=_make_pf("Step 1."))
        s2 = PipelineStage(
            name="s2",
            prompt_file=_make_pf("Step 2."),
            depends_on=["s1"],
        )
        pipeline = _make_pipeline([s1, s2])
        violations = PipelineOrphanReferenceRule().check_pipeline(pipeline, LintConfig())
        assert len(violations) == 0


class TestPL043InconsistentPersona:
    def test_fires_persona_change_no_transition(self) -> None:
        s1 = PipelineStage(
            name="s1",
            prompt_file=_make_pf("Do research."),
            persona="researcher",
        )
        s2 = PipelineStage(
            name="s2",
            prompt_file=_make_pf("Write a report."),
            persona="writer",
        )
        pipeline = _make_pipeline([s1, s2])
        violations = PipelineInconsistentPersonaRule().check_pipeline(pipeline, LintConfig())
        assert len(violations) == 1
        assert violations[0].rule_id == "PL043"

    def test_clean_same_persona(self) -> None:
        s1 = PipelineStage(name="s1", prompt_file=_make_pf("A."), persona="analyst")
        s2 = PipelineStage(name="s2", prompt_file=_make_pf("B."), persona="analyst")
        pipeline = _make_pipeline([s1, s2])
        violations = PipelineInconsistentPersonaRule().check_pipeline(pipeline, LintConfig())
        assert len(violations) == 0

    def test_clean_has_transition_language(self) -> None:
        s1 = PipelineStage(name="s1", prompt_file=_make_pf("Research."), persona="researcher")
        s2 = PipelineStage(
            name="s2",
            prompt_file=_make_pf("You are now a writer. Write the report."),
            persona="writer",
        )
        pipeline = _make_pipeline([s1, s2])
        violations = PipelineInconsistentPersonaRule().check_pipeline(pipeline, LintConfig())
        assert len(violations) == 0
