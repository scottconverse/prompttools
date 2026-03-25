"""Security rules: PL060, PL061, PL062, PL063."""

from __future__ import annotations

import re

from promptlint.models import LintConfig, LintViolation, PromptFile, Severity
from promptlint.rules.base import BaseRule

# ---------------------------------------------------------------------------
# PL060 PII patterns
# ---------------------------------------------------------------------------
_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email address", re.compile(r"\b[\w.-]+@[\w.-]+\.\w+\b")),
    ("phone number", re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    (
        "credit card number",
        re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    ),
]

# ---------------------------------------------------------------------------
# PL061 API key patterns
# ---------------------------------------------------------------------------
_API_KEY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("OpenAI key", re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b")),
    ("GitHub token", re.compile(r"\bghp_[a-zA-Z0-9]{36}\b")),
    ("Bearer token", re.compile(r"\bBearer [a-zA-Z0-9._-]{20,}\b")),
    ("Generic key", re.compile(r"\bkey-[a-zA-Z0-9]{32,}\b")),
    ("AWS key", re.compile(r"\bAKIA[A-Z0-9]{16}\b")),
    (
        "Generic secret",
        re.compile(
            r"\b(?:key|token|secret|password)\s*[:=]\s*['\"]?[a-zA-Z0-9/+]{20,}['\"]?",
            re.IGNORECASE,
        ),
    ),
]

# ---------------------------------------------------------------------------
# PL062 negative constraint language
# ---------------------------------------------------------------------------
_NEGATIVE_CONSTRAINT_RE = re.compile(
    r"\b(do not|never|must not|avoid|refuse to|don't)\b", re.IGNORECASE
)

# ---------------------------------------------------------------------------
# PL063 tool access and constraint patterns
# ---------------------------------------------------------------------------
_TOOL_ACCESS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\buse tools?\b", re.IGNORECASE),
    re.compile(r"\byou have access to\b", re.IGNORECASE),
    re.compile(r"\bcall the\b", re.IGNORECASE),
    re.compile(r"\bexecute\b", re.IGNORECASE),
    re.compile(r"\brun the\b", re.IGNORECASE),
]

_TOOL_CONSTRAINT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bonly when\b", re.IGNORECASE),
    re.compile(r"\bconfirm before\b", re.IGNORECASE),
    re.compile(r"\bask permission\b", re.IGNORECASE),
    re.compile(r"\bdo not use.*without\b", re.IGNORECASE),
    re.compile(r"\blimit.*to\b", re.IGNORECASE),
]


# ===================================================================
# Rule classes
# ===================================================================


class PIIInPromptRule(BaseRule):
    """PL060: Prompt contains patterns matching PII."""

    rule_id = "PL060"
    name = "pii-in-prompt"
    default_severity = Severity.ERROR

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        violations: list[LintViolation] = []
        for msg in prompt_file.messages:
            for pii_type, pattern in _PII_PATTERNS:
                match = pattern.search(msg.content)
                if match:
                    # Mask the matched value for the message
                    matched_text = match.group(0)
                    masked = matched_text[:3] + "***"
                    violations.append(
                        LintViolation(
                            rule_id=self.rule_id,
                            severity=self.default_severity,
                            message=(
                                f"Possible {pii_type} detected: {masked}"
                            ),
                            suggestion=(
                                f"Remove the {pii_type} and use a template "
                                "variable instead (e.g., {{email}})."
                            ),
                            path=prompt_file.path,
                            line=msg.line_start,
                            rule_name=self.name,
                            fixable=False,
                        ),
                    )
        return violations


class HardcodedAPIKeyRule(BaseRule):
    """PL061: Prompt contains what appears to be an API key or secret."""

    rule_id = "PL061"
    name = "hardcoded-api-key"
    default_severity = Severity.ERROR

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        violations: list[LintViolation] = []
        for msg in prompt_file.messages:
            for key_type, pattern in _API_KEY_PATTERNS:
                match = pattern.search(msg.content)
                if match:
                    matched_text = match.group(0)
                    masked = matched_text[:6] + "***"
                    violations.append(
                        LintViolation(
                            rule_id=self.rule_id,
                            severity=self.default_severity,
                            message=(
                                f"Possible {key_type} detected: {masked}"
                            ),
                            suggestion=(
                                "Remove hardcoded secrets from prompts. Use "
                                "environment variables or a secrets manager."
                            ),
                            path=prompt_file.path,
                            line=msg.line_start,
                            rule_name=self.name,
                            fixable=False,
                        ),
                    )
        return violations


class NoOutputConstraintsRule(BaseRule):
    """PL062: Prompt has no constraints on what the model should NOT output."""

    rule_id = "PL062"
    name = "no-output-constraints"
    default_severity = Severity.WARNING

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        total = prompt_file.total_tokens
        if total is not None and total <= 200:
            return []

        all_text = " ".join(msg.content for msg in prompt_file.messages)
        if _NEGATIVE_CONSTRAINT_RE.search(all_text):
            return []

        return [
            LintViolation(
                rule_id=self.rule_id,
                severity=self.default_severity,
                message=(
                    "Prompt contains no negative constraint language "
                    "(do not, never, must not, avoid, refuse to, don't)."
                ),
                suggestion=(
                    "Add output constraints specifying what the model should "
                    "NOT do or produce (e.g., 'Do not include personal opinions')."
                ),
                path=prompt_file.path,
                line=None,
                rule_name=self.name,
                fixable=False,
            ),
        ]


class UnboundedToolUseRule(BaseRule):
    """PL063: Prompt grants tool access without specifying constraints."""

    rule_id = "PL063"
    name = "unbounded-tool-use"
    default_severity = Severity.WARNING

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        all_text = " ".join(msg.content for msg in prompt_file.messages)

        has_tool_access = any(p.search(all_text) for p in _TOOL_ACCESS_PATTERNS)
        if not has_tool_access:
            return []

        has_constraint = any(p.search(all_text) for p in _TOOL_CONSTRAINT_PATTERNS)
        if has_constraint:
            return []

        return [
            LintViolation(
                rule_id=self.rule_id,
                severity=self.default_severity,
                message=(
                    "Prompt grants tool access without specifying usage "
                    "constraints or confirmation requirements."
                ),
                suggestion=(
                    "Add constraints on tool usage (e.g., 'Only use the tool "
                    "when X' or 'Confirm before executing')."
                ),
                path=prompt_file.path,
                line=None,
                rule_name=self.name,
                fixable=False,
            ),
        ]
