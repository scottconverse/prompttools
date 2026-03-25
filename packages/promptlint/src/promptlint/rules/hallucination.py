"""Hallucination risk rules: PL050, PL051, PL052, PL053, PL054."""

from __future__ import annotations

import re

from promptlint.models import LintConfig, LintViolation, PromptFile, Severity
from promptlint.rules.base import BaseRule

# ---------------------------------------------------------------------------
# PL050 patterns: requests for specific numbers without data source
# ---------------------------------------------------------------------------
_NUMBER_REQUEST_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bhow many\b", re.IGNORECASE),
    re.compile(
        r"\bwhat is the (volume|count|number|rate|percentage)\b", re.IGNORECASE
    ),
    re.compile(
        r"\bgive me the (exact|specific) (number|figure|statistic)\b",
        re.IGNORECASE,
    ),
]

_DATA_SOURCE_INDICATORS: list[re.Pattern[str]] = [
    re.compile(r"\b(from the provided|from the given|based on the data)\b", re.IGNORECASE),
    re.compile(r"\{\{data\}\}", re.IGNORECASE),
    re.compile(r"\b(tool|api|database|search)\b", re.IGNORECASE),
    re.compile(r"\b(use the|access the|query the)\b", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# PL051 patterns: requests for URLs
# ---------------------------------------------------------------------------
_URL_REQUEST_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bprovide (a |the )?(url|link|website)\b", re.IGNORECASE),
    re.compile(r"\binclude (a |the )?(link|url)\b", re.IGNORECASE),
    re.compile(r"\bpoint me to\b", re.IGNORECASE),
    re.compile(r"\bwhere can I find\b", re.IGNORECASE),
]

_WEB_SEARCH_INDICATOR = re.compile(
    r"\b(web search|search tool|browse|internet access)\b", re.IGNORECASE
)

# ---------------------------------------------------------------------------
# PL052 patterns: requests for citations
# ---------------------------------------------------------------------------
_CITATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bcite (your )?sources\b", re.IGNORECASE),
    re.compile(r"\bprovide references\b", re.IGNORECASE),
    re.compile(r"\binclude citations\b", re.IGNORECASE),
    re.compile(r"\blink to (studies|papers|research)\b", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# PL053 patterns: factual task without uncertainty instruction
# ---------------------------------------------------------------------------
_FACTUAL_TASK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(analyze|report on)\b", re.IGNORECASE),
    re.compile(r"\bwhat is\b", re.IGNORECASE),
    re.compile(r"\b(explain|describe the state of)\b", re.IGNORECASE),
]

_UNCERTAINTY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bif unsure\b", re.IGNORECASE),
    re.compile(r"\bflag uncertain\b", re.IGNORECASE),
    re.compile(r"\bdistinguish fact from\b", re.IGNORECASE),
    re.compile(r"\bexpress confidence\b", re.IGNORECASE),
    re.compile(r"""say ["']I don'?t know["']""", re.IGNORECASE),
    re.compile(r"\bI don'?t know\b", re.IGNORECASE),
    re.compile(r"\b(uncertain|unsure|not sure|confidence level)\b", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# PL054 patterns: fabrication-prone verifiable entity requests
# ---------------------------------------------------------------------------
_FABRICATION_PRONE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"\bprovide the (patent|case|ISBN|DOI) number\b", re.IGNORECASE
    ),
    re.compile(
        r"\bname the (author|researcher|company)\b", re.IGNORECASE
    ),
    re.compile(r"\bwhat year did\b", re.IGNORECASE),
    re.compile(r"\bwho (invented|discovered|founded)\b", re.IGNORECASE),
]


# ===================================================================
# Rule classes
# ===================================================================


class AsksForSpecificNumbersRule(BaseRule):
    """PL050: Prompt asks for numerical data without a data source."""

    rule_id = "PL050"
    name = "asks-for-specific-numbers"
    default_severity = Severity.WARNING

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        all_text = " ".join(msg.content for msg in prompt_file.messages)

        asks_numbers = any(p.search(all_text) for p in _NUMBER_REQUEST_PATTERNS)
        if not asks_numbers:
            return []

        has_source = any(p.search(all_text) for p in _DATA_SOURCE_INDICATORS)
        if has_source:
            return []

        return [
            LintViolation(
                rule_id=self.rule_id,
                severity=self.default_severity,
                message=(
                    "Prompt asks for specific numerical data without providing "
                    "a data source or tool access."
                ),
                suggestion=(
                    "Provide a data source, reference a data variable "
                    "(e.g., {{data}}), or grant tool access for data retrieval."
                ),
                path=prompt_file.path,
                line=None,
                rule_name=self.name,
                fixable=False,
            ),
        ]


class AsksForURLsRule(BaseRule):
    """PL051: Prompt asks model to provide URLs or links."""

    rule_id = "PL051"
    name = "asks-for-urls"
    default_severity = Severity.WARNING

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        all_text = " ".join(msg.content for msg in prompt_file.messages)

        asks_urls = any(p.search(all_text) for p in _URL_REQUEST_PATTERNS)
        if not asks_urls:
            return []

        if _WEB_SEARCH_INDICATOR.search(all_text):
            return []

        return [
            LintViolation(
                rule_id=self.rule_id,
                severity=self.default_severity,
                message=(
                    "Prompt asks the model to provide URLs, which have a high "
                    "risk of being fabricated."
                ),
                suggestion=(
                    "Grant web search tool access, or remove the request for "
                    "URLs. Consider asking the model to describe where to find "
                    "information instead."
                ),
                path=prompt_file.path,
                line=None,
                rule_name=self.name,
                fixable=False,
            ),
        ]


class AsksForCitationsRule(BaseRule):
    """PL052: Prompt asks for citations without a verification method."""

    rule_id = "PL052"
    name = "asks-for-citations"
    default_severity = Severity.INFO

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        all_text = " ".join(msg.content for msg in prompt_file.messages)

        asks_citations = any(p.search(all_text) for p in _CITATION_PATTERNS)
        if not asks_citations:
            return []

        return [
            LintViolation(
                rule_id=self.rule_id,
                severity=self.default_severity,
                message=(
                    "Prompt asks for citations or references without specifying "
                    "a verification method."
                ),
                suggestion=(
                    "Add a verification instruction (e.g., 'Only cite sources "
                    "you can verify' or provide a reference database)."
                ),
                path=prompt_file.path,
                line=None,
                rule_name=self.name,
                fixable=False,
            ),
        ]


class NoUncertaintyInstructionRule(BaseRule):
    """PL053: Factual prompt with no instruction to express uncertainty."""

    rule_id = "PL053"
    name = "no-uncertainty-instruction"
    default_severity = Severity.WARNING

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        all_text = " ".join(msg.content for msg in prompt_file.messages)

        is_factual = any(p.search(all_text) for p in _FACTUAL_TASK_PATTERNS)
        if not is_factual:
            return []

        has_uncertainty = any(p.search(all_text) for p in _UNCERTAINTY_PATTERNS)
        if has_uncertainty:
            return []

        return [
            LintViolation(
                rule_id=self.rule_id,
                severity=self.default_severity,
                message=(
                    "Prompt asks for factual claims but contains no instruction "
                    "to express uncertainty or flag unverified information."
                ),
                suggestion=(
                    'Add an uncertainty instruction such as "If unsure, say so" '
                    'or "Distinguish verified facts from inferences."'
                ),
                path=prompt_file.path,
                line=None,
                rule_name=self.name,
                fixable=False,
            ),
        ]


class FabricationProneTaskRule(BaseRule):
    """PL054: Prompt asks for specific verifiable entities commonly fabricated."""

    rule_id = "PL054"
    name = "fabrication-prone-task"
    default_severity = Severity.INFO

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        all_text = " ".join(msg.content for msg in prompt_file.messages)

        violations: list[LintViolation] = []
        for pattern in _FABRICATION_PRONE_PATTERNS:
            match = pattern.search(all_text)
            if match:
                violations.append(
                    LintViolation(
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        message=(
                            f"Prompt requests verifiable entities "
                            f'("{match.group(0)}") that are commonly fabricated '
                            "by language models."
                        ),
                        suggestion=(
                            "Provide reference data or grant tool access for "
                            "verification. Add instructions to flag unverifiable "
                            "claims."
                        ),
                        path=prompt_file.path,
                        line=None,
                        rule_name=self.name,
                        fixable=False,
                    ),
                )
                break  # one violation per file
        return violations
