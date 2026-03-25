"""Gate/constraint rules: PL080, PL081, PL082, PL083."""

from __future__ import annotations

import re

from promptlint.models import LintConfig, LintViolation, PromptFile, Severity
from promptlint.rules.base import BaseRule

# ---------------------------------------------------------------------------
# PL080: Conditional patterns and enforcement language
# ---------------------------------------------------------------------------
_CONDITIONAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bif .*(missing|absent|not provided|unavailable|unclear)\b", re.IGNORECASE),
    re.compile(r"\bwhen .*(no|without|lacking)\b", re.IGNORECASE),
]

_ENFORCEMENT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bdo not (proceed|continue|generate)\b", re.IGNORECASE),
    re.compile(r"\b(stop|block|refuse|halt|wait)\b", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# PL081: Capability declarations and fallback language
# ---------------------------------------------------------------------------
_CAPABILITY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\brequires? (web search|tool|API|database|internet)\b", re.IGNORECASE),
    re.compile(r"\byou have access to\b", re.IGNORECASE),
    re.compile(r"\busing (the )?\w+ (tool|API|function)\b", re.IGNORECASE),
]

_FALLBACK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bif .*(unavailable|not available|cannot access)\b", re.IGNORECASE),
    re.compile(r"\b(fallback|alternative|otherwise)\b", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# PL082: Format specification and schema presence
# ---------------------------------------------------------------------------
_FORMAT_SPEC_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\brespond in (JSON|XML|YAML|CSV|markdown|table)\b", re.IGNORECASE),
    re.compile(r"\buse (this|the following) format\b", re.IGNORECASE),
    re.compile(r"\boutput (as|in) \b", re.IGNORECASE),
]

_SCHEMA_INDICATORS: list[re.Pattern[str]] = [
    re.compile(r"```"),                                   # code blocks
    re.compile(r'[{]\s*"', re.MULTILINE),                 # JSON-like structure
    re.compile(r"\b(field|key|property|column)\s*:", re.IGNORECASE),
    re.compile(r"\bexample\s*(output|response)\b", re.IGNORECASE),
    re.compile(r"^\s*[-*]\s+\w+:", re.MULTILINE),         # key-value bullets
]

# ---------------------------------------------------------------------------
# PL083: Claim-generating instructions and evidence language
# ---------------------------------------------------------------------------
_CLAIM_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(analyze|recommend|assess|evaluate)\b", re.IGNORECASE),
    re.compile(r"\bdetermine whether\b", re.IGNORECASE),
    re.compile(r"\b(rate|score|rank)\b", re.IGNORECASE),
]

_EVIDENCE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bbased on\b", re.IGNORECASE),
    re.compile(r"\bcite\b", re.IGNORECASE),
    re.compile(r"\bsource\b", re.IGNORECASE),
    re.compile(r"\bevidence\b", re.IGNORECASE),
    re.compile(r"\bconfidence\b", re.IGNORECASE),
    re.compile(r"\bverified\b", re.IGNORECASE),
    re.compile(r"\bif unsure\b", re.IGNORECASE),
]


# ===================================================================
# Rule classes
# ===================================================================


class GateNoEnforcementRule(BaseRule):
    """PL080: Conditional logic exists but has no hard stop instruction."""

    rule_id = "PL080"
    name = "gate-no-enforcement"
    default_severity = Severity.WARNING

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        all_text = " ".join(msg.content for msg in prompt_file.messages)
        violations: list[LintViolation] = []

        # Split into sentences for proximity check
        sentences = re.split(r"[.!?\n]", all_text)

        for i, sentence in enumerate(sentences):
            has_conditional = any(p.search(sentence) for p in _CONDITIONAL_PATTERNS)
            if not has_conditional:
                continue

            # Check within 3 sentences for enforcement language
            nearby = sentences[max(0, i - 1) : i + 4]
            nearby_text = " ".join(nearby)
            has_enforcement = any(p.search(nearby_text) for p in _ENFORCEMENT_PATTERNS)

            if not has_enforcement:
                violations.append(
                    LintViolation(
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        message=(
                            f'Conditional gate "{sentence.strip()[:60]}..." '
                            "has no enforcement instruction nearby."
                        ),
                        suggestion=(
                            "Add a hard stop instruction after the condition "
                            '(e.g., "do not proceed", "stop", "refuse").'
                        ),
                        path=prompt_file.path,
                        line=None,
                        rule_name=self.name,
                        fixable=False,
                    ),
                )
        return violations


class GateNoFallbackRule(BaseRule):
    """PL081: Capability declared without fallback if unavailable."""

    rule_id = "PL081"
    name = "gate-no-fallback"
    default_severity = Severity.INFO

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        all_text = " ".join(msg.content for msg in prompt_file.messages)

        has_capability = any(p.search(all_text) for p in _CAPABILITY_PATTERNS)
        if not has_capability:
            return []

        has_fallback = any(p.search(all_text) for p in _FALLBACK_PATTERNS)
        if has_fallback:
            return []

        return [
            LintViolation(
                rule_id=self.rule_id,
                severity=self.default_severity,
                message=(
                    "Prompt declares a required tool or capability but has "
                    "no fallback instruction if unavailable."
                ),
                suggestion=(
                    "Add a fallback instruction for when the capability is "
                    'unavailable (e.g., "If the API is not available, ...'
                    'explain that you cannot complete the request").'
                ),
                path=prompt_file.path,
                line=None,
                rule_name=self.name,
                fixable=False,
            ),
        ]


class OutputSchemaMissingRule(BaseRule):
    """PL082: Structured output specified but no schema or example provided."""

    rule_id = "PL082"
    name = "output-schema-missing"
    default_severity = Severity.WARNING

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        all_text = " ".join(msg.content for msg in prompt_file.messages)

        has_format_spec = any(p.search(all_text) for p in _FORMAT_SPEC_PATTERNS)
        if not has_format_spec:
            return []

        has_schema = any(p.search(all_text) for p in _SCHEMA_INDICATORS)
        if has_schema:
            return []

        return [
            LintViolation(
                rule_id=self.rule_id,
                severity=self.default_severity,
                message=(
                    "Prompt specifies a structured output format but provides "
                    "no schema, template, or example of the expected structure."
                ),
                suggestion=(
                    "Add a schema definition, example output, or field list "
                    "to clarify the expected output structure."
                ),
                path=prompt_file.path,
                line=None,
                rule_name=self.name,
                fixable=False,
            ),
        ]


class ClaimNoEvidenceGateRule(BaseRule):
    """PL083: Prompt asks for claims/recommendations with no evidence instruction."""

    rule_id = "PL083"
    name = "claim-no-evidence-gate"
    default_severity = Severity.INFO

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        all_text = " ".join(msg.content for msg in prompt_file.messages)

        has_claims = any(p.search(all_text) for p in _CLAIM_PATTERNS)
        if not has_claims:
            return []

        has_evidence = any(p.search(all_text) for p in _EVIDENCE_PATTERNS)
        if has_evidence:
            return []

        return [
            LintViolation(
                rule_id=self.rule_id,
                severity=self.default_severity,
                message=(
                    "Prompt asks the model to make claims or recommendations "
                    "but has no instruction to substantiate or express confidence."
                ),
                suggestion=(
                    "Add an evidence instruction (e.g., 'Support each "
                    "recommendation with reasoning' or 'Express confidence "
                    "levels for each claim')."
                ),
                path=prompt_file.path,
                line=None,
                rule_name=self.name,
                fixable=False,
            ),
        ]
