"""Abstract base classes for all lint rules."""

from __future__ import annotations

from abc import ABC, abstractmethod

from promptlint.models import (
    LintConfig,
    LintViolation,
    PromptFile,
    PromptPipeline,
    Severity,
)


class BaseRule(ABC):
    """Abstract base class for single-file lint rules."""

    rule_id: str
    name: str
    default_severity: Severity
    fixable: bool = False

    @abstractmethod
    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        """Run this rule against a parsed prompt file."""
        ...

    def fix(self, prompt_file: PromptFile, violation: LintViolation) -> str | None:
        """Return fixed content, or None if not fixable. Only called if fixable=True."""
        return None


class BasePipelineRule(ABC):
    """Abstract base class for pipeline-level lint rules."""

    rule_id: str
    name: str
    default_severity: Severity

    @abstractmethod
    def check_pipeline(
        self, pipeline: PromptPipeline, config: LintConfig
    ) -> list[LintViolation]:
        """Run this rule against a prompt pipeline."""
        ...
