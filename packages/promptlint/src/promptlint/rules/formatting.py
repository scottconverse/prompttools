"""Formatting rules: PL020, PL021, PL022, PL023, PL024."""

from __future__ import annotations

import re
from collections import Counter

from promptlint.models import LintConfig, LintViolation, PromptFile, Severity
from promptlint.rules.base import BaseRule

# Output format indicators for PL022
_OUTPUT_FORMAT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(json|xml|yaml|csv|markdown|table|html|list|bullet|numbered)\b", re.IGNORECASE),
    re.compile(r"\bformat\s*(as|in|your|the)\b", re.IGNORECASE),
    re.compile(r"\brespond (in|as|with)\b", re.IGNORECASE),
    re.compile(r"\boutput (as|in|format)\b", re.IGNORECASE),
    re.compile(r"\breturn (a |the )?(list|dict|object|array|table)\b", re.IGNORECASE),
]

# Delimiter styles for PL021
_DELIMITER_PATTERNS: dict[str, re.Pattern[str]] = {
    "markdown_header": re.compile(r"^#{1,6}\s", re.MULTILINE),
    "triple_dash": re.compile(r"^---+\s*$", re.MULTILINE),
    "triple_equals": re.compile(r"^===+\s*$", re.MULTILINE),
    "triple_hash": re.compile(r"^####+\s*$", re.MULTILINE),
    "xml_tag": re.compile(r"</?[a-zA-Z][\w-]*>"),
}


class TrailingWhitespaceRule(BaseRule):
    """PL020: Lines contain trailing whitespace."""

    rule_id = "PL020"
    name = "trailing-whitespace"
    default_severity = Severity.INFO
    fixable = True

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        violations: list[LintViolation] = []
        for i, line in enumerate(prompt_file.raw_content.splitlines(), start=1):
            if line != line.rstrip():
                violations.append(
                    LintViolation(
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        message=f"Line {i} has trailing whitespace.",
                        suggestion="Remove trailing whitespace from this line.",
                        path=prompt_file.path,
                        line=i,
                        rule_name=self.name,
                        fixable=True,
                    ),
                )
        return violations

    def fix(self, prompt_file: PromptFile, violation: LintViolation) -> str | None:
        """Strip trailing whitespace from all lines."""
        lines = prompt_file.raw_content.splitlines(keepends=True)
        fixed = []
        for line in lines:
            eol = ""
            if line.endswith("\r\n"):
                eol = "\r\n"
            elif line.endswith("\n"):
                eol = "\n"
            elif line.endswith("\r"):
                eol = "\r"
            fixed.append(line.rstrip() + eol)
        return "".join(fixed)


class InconsistentDelimitersRule(BaseRule):
    """PL021: Prompt mixes delimiter styles without consistent pattern."""

    rule_id = "PL021"
    name = "inconsistent-delimiters"
    default_severity = Severity.WARNING

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        all_text = " ".join(msg.content for msg in prompt_file.messages)
        found_styles: list[str] = []
        for style_name, pattern in _DELIMITER_PATTERNS.items():
            if pattern.search(all_text):
                found_styles.append(style_name)

        if len(found_styles) >= 3:
            return [
                LintViolation(
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    message=(
                        f"Prompt mixes {len(found_styles)} delimiter styles: "
                        f"{', '.join(found_styles)}."
                    ),
                    suggestion=(
                        "Choose one consistent delimiter style throughout the prompt "
                        "(e.g., markdown headers or XML tags, not both)."
                    ),
                    path=prompt_file.path,
                    line=None,
                    rule_name=self.name,
                    fixable=False,
                ),
            ]
        return []


class MissingOutputFormatRule(BaseRule):
    """PL022: No output format instruction detected in the prompt."""

    rule_id = "PL022"
    name = "missing-output-format"
    default_severity = Severity.WARNING

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        all_text = " ".join(msg.content for msg in prompt_file.messages)
        for pattern in _OUTPUT_FORMAT_PATTERNS:
            if pattern.search(all_text):
                return []
        return [
            LintViolation(
                rule_id=self.rule_id,
                severity=self.default_severity,
                message="No output format instruction detected in the prompt.",
                suggestion=(
                    "Specify the desired output format (e.g., JSON, markdown, "
                    "bullet list) to get more predictable responses."
                ),
                path=prompt_file.path,
                line=None,
                rule_name=self.name,
                fixable=False,
            ),
        ]


class ExcessiveRepetitionRule(BaseRule):
    """PL023: The same instruction or phrase appears 3+ times across messages."""

    rule_id = "PL023"
    name = "excessive-repetition"
    default_severity = Severity.WARNING

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        # Extract meaningful phrases (sentences / instruction fragments)
        all_sentences: list[str] = []
        for msg in prompt_file.messages:
            for raw in re.split(r"[.!?\n]", msg.content):
                s = raw.strip().lower()
                if len(s) >= 10:  # skip very short fragments
                    all_sentences.append(s)

        counts = Counter(all_sentences)
        violations: list[LintViolation] = []
        for phrase, count in counts.items():
            if count >= config.repetition_threshold:
                violations.append(
                    LintViolation(
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        message=(
                            f'Phrase "{phrase[:60]}..." repeated {count} times '
                            f"(threshold: {config.repetition_threshold})."
                        ),
                        suggestion=(
                            "Remove duplicate instructions. State each instruction "
                            "once clearly rather than repeating it."
                        ),
                        path=prompt_file.path,
                        line=None,
                        rule_name=self.name,
                        fixable=False,
                    ),
                )
        return violations


class LineTooLongRule(BaseRule):
    """PL024: A single line exceeds the configured character limit."""

    rule_id = "PL024"
    name = "line-too-long"
    default_severity = Severity.INFO

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        violations: list[LintViolation] = []
        for i, line in enumerate(prompt_file.raw_content.splitlines(), start=1):
            if len(line) > config.max_line_length:
                violations.append(
                    LintViolation(
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        message=(
                            f"Line {i} is {len(line)} characters long "
                            f"(max: {config.max_line_length})."
                        ),
                        suggestion="Break this line into shorter segments for readability.",
                        path=prompt_file.path,
                        line=i,
                        rule_name=self.name,
                        fixable=False,
                    ),
                )
        return violations
