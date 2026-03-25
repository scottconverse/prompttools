"""Tokenizer warning rules: PL090."""

from __future__ import annotations

from promptlint.models import LintConfig, LintViolation, PromptFile, Severity
from promptlint.profiles.models import get_profile
from promptlint.rules.base import BaseRule


class ApproximateTokenizerWarning(BaseRule):
    """PL090: Warn when the configured model uses an approximate tokenizer.

    Claude and Gemini models do not publish their native tokenizers.
    promptlint approximates token counts using cl100k_base, which may
    differ from actual token counts by 10-20%. This rule surfaces that
    uncertainty so users know their token budgets are estimates.
    """

    rule_id = "PL090"
    name = "approximate-tokenizer"
    default_severity = Severity.INFO
    fixable = False

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        if not config.model:
            return []

        profile = get_profile(config.model)
        if profile is None or not profile.approximate_tokenizer:
            return []

        return [
            LintViolation(
                rule_id=self.rule_id,
                severity=self._effective_severity(config),
                message=(
                    f"Model '{config.model}' uses an approximate tokenizer "
                    f"({profile.tokenizer_encoding}). Actual token counts may differ "
                    f"by 10-20%. Token budget thresholds are estimates, not exact limits."
                ),
                suggestion=(
                    "Token counts for this model are directional. Do not treat "
                    "threshold violations as precise — leave a margin of 15-20% "
                    "below the model's context window for safety."
                ),
                path=prompt_file.path,
                line=None,
                rule_name=self.name,
                fixable=False,
            )
        ]

    def _effective_severity(self, config: LintConfig) -> Severity:
        override = config.rule_overrides.get(self.rule_id) or config.rule_overrides.get(self.name)
        if override:
            return Severity(override)
        return self.default_severity
