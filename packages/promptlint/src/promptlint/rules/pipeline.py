"""Pipeline rules: PL040, PL041, PL042, PL043."""

from __future__ import annotations

import re

from promptlint.models import (
    LintConfig,
    LintViolation,
    PromptPipeline,
    Severity,
)
from promptlint.rules.base import BasePipelineRule

# Handoff reference patterns for PL040
_HANDOFF_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"from stage\b", re.IGNORECASE),
    re.compile(r"previous (output|result|analysis|response|stage)", re.IGNORECASE),
    re.compile(r"above (analysis|output|result|response)", re.IGNORECASE),
    re.compile(r"prior (stage|step|output|analysis)", re.IGNORECASE),
    re.compile(r"based on (the )?(previous|prior|earlier|above)", re.IGNORECASE),
    re.compile(r"output (from|of) (the )?(previous|prior|first|second|third)", re.IGNORECASE),
]

# Transition language for PL043
_TRANSITION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"you are now\b", re.IGNORECASE),
    re.compile(r"in this stage,?\s*(your )?role is", re.IGNORECASE),
    re.compile(r"switch(ing)? (to|your) role", re.IGNORECASE),
    re.compile(r"acting as\b", re.IGNORECASE),
    re.compile(r"take on the role of\b", re.IGNORECASE),
]


class PipelineNoHandoffRule(BasePipelineRule):
    """PL040: Multi-file prompt set has no handoff mechanism between stages."""

    rule_id = "PL040"
    name = "pipeline-no-handoff"
    default_severity = Severity.WARNING

    def check_pipeline(
        self, pipeline: PromptPipeline, config: LintConfig
    ) -> list[LintViolation]:
        violations: list[LintViolation] = []

        for i, stage in enumerate(pipeline.stages):
            if i == 0:
                continue  # first stage doesn't need handoff
            if not stage.depends_on:
                continue  # no declared dependency = no handoff expected

            all_text = " ".join(
                msg.content for msg in stage.prompt_file.messages
            )

            # Check for handoff patterns
            has_handoff = False
            for pattern in _HANDOFF_PATTERNS:
                if pattern.search(all_text):
                    has_handoff = True
                    break

            # Check for references to dependency stage names
            if not has_handoff:
                for dep_name in stage.depends_on:
                    if dep_name.lower() in all_text.lower():
                        has_handoff = True
                        break

            if not has_handoff:
                violations.append(
                    LintViolation(
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        message=(
                            f"Stage '{stage.name}' depends on "
                            f"{stage.depends_on} but contains no reference to "
                            "prior stage output."
                        ),
                        suggestion=(
                            "Add explicit handoff language referencing the output "
                            "from dependent stages (e.g., 'Using the output from "
                            "the previous stage...')."
                        ),
                        path=stage.prompt_file.path,
                        line=None,
                        rule_name=self.name,
                        fixable=False,
                    ),
                )
        return violations


class PipelineContextGrowthRule(BasePipelineRule):
    """PL041: Cumulative token count exceeds model context window."""

    rule_id = "PL041"
    name = "pipeline-context-growth"
    default_severity = Severity.WARNING

    def check_pipeline(
        self, pipeline: PromptPipeline, config: LintConfig
    ) -> list[LintViolation]:
        context_window = config.context_window
        if context_window is None:
            return []

        violations: list[LintViolation] = []
        # Build a map of stage name -> stage for dependency lookup
        stage_map = {s.name: s for s in pipeline.stages}

        for stage in pipeline.stages:
            # Compute input tokens for this stage:
            # prompt_tokens + sum of expected_output_tokens from all depends_on
            prompt_tokens = stage.prompt_file.total_tokens or 0
            dep_output_tokens = 0
            for dep_name in stage.depends_on:
                dep_stage = stage_map.get(dep_name)
                if dep_stage and dep_stage.expected_output_tokens:
                    dep_output_tokens += dep_stage.expected_output_tokens

            total_input = prompt_tokens + dep_output_tokens
            if total_input > context_window:
                violations.append(
                    LintViolation(
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        message=(
                            f"Stage '{stage.name}' requires ~{total_input} tokens "
                            f"(prompt: {prompt_tokens} + dependency outputs: "
                            f"{dep_output_tokens}), exceeding context window of "
                            f"{context_window}."
                        ),
                        suggestion=(
                            "Reduce prompt length or dependency output sizes. "
                            "Consider summarizing intermediate outputs before "
                            "passing to downstream stages."
                        ),
                        path=stage.prompt_file.path,
                        line=None,
                        rule_name=self.name,
                        fixable=False,
                    ),
                )
        return violations


class PipelineOrphanReferenceRule(BasePipelineRule):
    """PL042: A prompt references a stage name that doesn't exist."""

    rule_id = "PL042"
    name = "pipeline-orphan-reference"
    default_severity = Severity.ERROR

    def check_pipeline(
        self, pipeline: PromptPipeline, config: LintConfig
    ) -> list[LintViolation]:
        stage_names = {s.name for s in pipeline.stages}
        violations: list[LintViolation] = []

        for stage in pipeline.stages:
            for dep_name in stage.depends_on:
                if dep_name not in stage_names:
                    violations.append(
                        LintViolation(
                            rule_id=self.rule_id,
                            severity=self.default_severity,
                            message=(
                                f"Stage '{stage.name}' references non-existent "
                                f"stage '{dep_name}' in depends_on."
                            ),
                            suggestion=(
                                f"Check the pipeline manifest. Either add a stage "
                                f"named '{dep_name}' or fix the depends_on reference."
                            ),
                            path=pipeline.manifest_path,
                            line=None,
                            rule_name=self.name,
                            fixable=False,
                        ),
                    )
        return violations


class PipelineInconsistentPersonaRule(BasePipelineRule):
    """PL043: Different prompts define conflicting personas without transition."""

    rule_id = "PL043"
    name = "pipeline-inconsistent-persona"
    default_severity = Severity.WARNING

    def check_pipeline(
        self, pipeline: PromptPipeline, config: LintConfig
    ) -> list[LintViolation]:
        violations: list[LintViolation] = []

        for i in range(1, len(pipeline.stages)):
            prev_stage = pipeline.stages[i - 1]
            curr_stage = pipeline.stages[i]

            if not prev_stage.persona or not curr_stage.persona:
                continue
            if prev_stage.persona.lower() == curr_stage.persona.lower():
                continue

            # Persona changed -- check for transition language
            all_text = " ".join(
                msg.content for msg in curr_stage.prompt_file.messages
            )
            has_transition = any(
                p.search(all_text) for p in _TRANSITION_PATTERNS
            )

            if not has_transition:
                violations.append(
                    LintViolation(
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        message=(
                            f"Persona changes from '{prev_stage.persona}' "
                            f"(stage '{prev_stage.name}') to "
                            f"'{curr_stage.persona}' (stage '{curr_stage.name}') "
                            "without explicit transition language."
                        ),
                        suggestion=(
                            "Add explicit role transition language (e.g., "
                            "'You are now a ...') when changing personas between "
                            "pipeline stages."
                        ),
                        path=curr_stage.prompt_file.path,
                        line=None,
                        rule_name=self.name,
                        fixable=False,
                    ),
                )
        return violations
