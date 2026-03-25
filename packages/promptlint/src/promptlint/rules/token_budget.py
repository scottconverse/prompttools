"""Token budget rules: PL001, PL002, PL003."""

from __future__ import annotations

import re

from promptlint.models import LintConfig, LintViolation, PromptFile, Severity
from promptlint.rules.base import BaseRule

# Common English stop words used for PL003 density check.
STOP_WORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "if",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "as",
        "is",
        "was",
        "are",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "need",
        "must",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "i",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "he",
        "him",
        "his",
        "she",
        "her",
        "they",
        "them",
        "their",
        "what",
        "which",
        "who",
        "whom",
        "when",
        "where",
        "why",
        "how",
        "not",
        "no",
        "nor",
        "so",
        "up",
        "out",
        "about",
        "into",
        "over",
        "after",
        "before",
        "between",
        "under",
        "again",
        "then",
        "once",
        "here",
        "there",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "only",
        "own",
        "same",
        "than",
        "too",
        "very",
        "just",
        "because",
        "also",
        "any",
        "through",
        "during",
        "while",
        "get",
        "got",
        "make",
        "made",
    }
)

_WORD_RE = re.compile(r"[a-zA-Z]+")


class TokenBudgetWarnRule(BaseRule):
    """PL001: Total prompt token count exceeds the warning threshold."""

    rule_id = "PL001"
    name = "token-budget-warn"
    default_severity = Severity.WARNING

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        total = prompt_file.total_tokens
        if total is None:
            return []

        threshold = config.token_warn_threshold
        # Don't fire PL001 if PL002 would fire (avoid double-reporting).
        if total > threshold and total <= config.token_error_threshold:
            return [
                LintViolation(
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    message=(
                        f"Prompt uses {total} tokens, exceeding the warning "
                        f"threshold of {threshold}."
                    ),
                    suggestion=(
                        "Reduce prompt length by removing redundant instructions "
                        "or extracting reusable context into variables."
                    ),
                    path=prompt_file.path,
                    line=None,
                    rule_name=self.name,
                    fixable=False,
                ),
            ]
        return []


class TokenBudgetErrorRule(BaseRule):
    """PL002: Total prompt token count exceeds the error threshold."""

    rule_id = "PL002"
    name = "token-budget-error"
    default_severity = Severity.ERROR

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        total = prompt_file.total_tokens
        if total is None:
            return []

        threshold = config.token_error_threshold
        if total > threshold:
            return [
                LintViolation(
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    message=(
                        f"Prompt uses {total} tokens, exceeding the error "
                        f"threshold of {threshold}."
                    ),
                    suggestion=(
                        "Significantly reduce prompt length. Consider splitting "
                        "into a multi-stage pipeline or removing low-value content."
                    ),
                    path=prompt_file.path,
                    line=None,
                    rule_name=self.name,
                    fixable=False,
                ),
            ]
        return []


class TokenDensityLowRule(BaseRule):
    """PL003: Token-to-information ratio is low (high filler / stop-word content)."""

    rule_id = "PL003"
    name = "token-density-low"
    default_severity = Severity.INFO

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        all_text = " ".join(msg.content for msg in prompt_file.messages)
        words = _WORD_RE.findall(all_text)
        if not words:
            return []

        stop_count = sum(1 for w in words if w.lower() in STOP_WORDS)
        ratio = stop_count / len(words)

        if ratio >= config.stop_word_ratio:
            return [
                LintViolation(
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    message=(
                        f"Stop-word ratio is {ratio:.0%} (threshold: "
                        f"{config.stop_word_ratio:.0%}). Prompt may contain "
                        "excessive filler language."
                    ),
                    suggestion=(
                        "Tighten language by removing unnecessary filler words "
                        "and rephrasing for conciseness."
                    ),
                    path=prompt_file.path,
                    line=None,
                    rule_name=self.name,
                    fixable=False,
                ),
            ]
        return []
