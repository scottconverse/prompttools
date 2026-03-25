"""Prompt smell rules: PL070, PL071, PL072, PL073, PL074."""

from __future__ import annotations

import re

from promptlint.models import LintConfig, LintViolation, PromptFile, Severity
from promptlint.rules.base import BaseRule

# ---------------------------------------------------------------------------
# PL070: Ambiguous quantifier patterns (only in instruction context)
# ---------------------------------------------------------------------------
_AMBIGUOUS_QUANTIFIER_RE = re.compile(
    r"\b(include|provide|give|add|list)\s+(some|a few|several|many|various|multiple)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# PL071: Critical keywords
# ---------------------------------------------------------------------------
_CRITICAL_KEYWORDS_RE = re.compile(
    r"\b(MUST|NEVER|ALWAYS|IMPORTANT|CRITICAL|MANDATORY|REQUIRED)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# PL073: Example indicators
# ---------------------------------------------------------------------------
_EXAMPLE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bfor example\b", re.IGNORECASE),
    re.compile(r"\be\.g\.\b", re.IGNORECASE),
    re.compile(r"\bsuch as\b", re.IGNORECASE),
    re.compile(r"\bhere is an example\b", re.IGNORECASE),
    re.compile(r"\bsample (input|output)\b", re.IGNORECASE),
    re.compile(r"```"),  # code blocks
    re.compile(r"Input:.*Output:", re.IGNORECASE | re.DOTALL),
]

# ---------------------------------------------------------------------------
# PL074: Structural markers
# ---------------------------------------------------------------------------
_STRUCTURE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^#{1,6}\s", re.MULTILINE),          # markdown headers
    re.compile(r"^[\s]*[-*\u2022]\s", re.MULTILINE),  # bullet points
    re.compile(r"^[\s]*\d+[.)]\s", re.MULTILINE),     # numbered lists
    re.compile(r"^[\s]*[a-z][.)]\s", re.MULTILINE),   # lettered lists
    re.compile(r"^---+\s*$", re.MULTILINE),            # horizontal rules
    re.compile(r"^===+\s*$", re.MULTILINE),            # separator
    re.compile(r"^####+\s*$", re.MULTILINE),           # hash separator
    re.compile(r"</?[a-zA-Z][\w-]*>"),                 # XML/HTML tags
]

# ---------------------------------------------------------------------------
# PL072: Competing instructions (reuses conflict detection from system_prompt)
# ---------------------------------------------------------------------------
_COMPETING_CONTRADICTION_PAIRS: list[tuple[re.Pattern[str], re.Pattern[str]]] = [
    (
        re.compile(r"\b(be concise|be brief)\b", re.IGNORECASE),
        re.compile(r"\b(be thorough|be detailed|be comprehensive)\b", re.IGNORECASE),
    ),
    (
        re.compile(r"\bdo not make assumptions\b", re.IGNORECASE),
        re.compile(r"\b(fill in any gaps|infer what'?s needed)\b", re.IGNORECASE),
    ),
    (
        re.compile(r"\brespond only in (\w+)\b", re.IGNORECASE),
        re.compile(r"\balso include\b", re.IGNORECASE),
    ),
]

_MODAL_RE = re.compile(
    r"\b(must|should|always|never|do not|don't|shall|cannot|can't)\b",
    re.IGNORECASE,
)
_IMPERATIVE_START = re.compile(
    r"^(be |do |use |include |provide |ensure |make |keep |set |add |write |avoid |respond |return |output |format |generate |create |list |give )",
    re.IGNORECASE,
)


def _extract_instructions(text: str) -> list[str]:
    sentences: list[str] = []
    for raw in re.split(r"[.!?\n]", text):
        s = raw.strip()
        if not s:
            continue
        if _MODAL_RE.search(s) or _IMPERATIVE_START.match(s):
            sentences.append(s)
    return sentences


def _significant_words(sentence: str) -> set[str]:
    trivial = {"a", "an", "the", "to", "in", "of", "and", "or", "is", "be", "it", "for", "with", "not", "do", "don't"}
    return {
        w.lower()
        for w in re.findall(r"[a-zA-Z]{3,}", sentence)
        if w.lower() not in trivial
    }


def _is_negative(sentence: str) -> bool:
    return bool(re.search(r"\b(never|do not|don't|must not|cannot|can't|avoid)\b", sentence, re.IGNORECASE))


# ===================================================================
# Rule classes
# ===================================================================


class AmbiguousQuantifierRule(BaseRule):
    """PL070: Prompt uses vague quantifiers where specificity would help."""

    rule_id = "PL070"
    name = "ambiguous-quantifier"
    default_severity = Severity.INFO

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        violations: list[LintViolation] = []
        for msg in prompt_file.messages:
            for match in _AMBIGUOUS_QUANTIFIER_RE.finditer(msg.content):
                violations.append(
                    LintViolation(
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        message=(
                            f'Vague quantifier in instruction context: '
                            f'"{match.group(0)}".'
                        ),
                        suggestion=(
                            "Replace vague quantifiers with specific numbers "
                            '(e.g., "provide 3 examples" instead of "provide some '
                            'examples").'
                        ),
                        path=prompt_file.path,
                        line=msg.line_start,
                        rule_name=self.name,
                        fixable=False,
                    ),
                )
        return violations


class InstructionBuriedRule(BaseRule):
    """PL071: Critical instruction appears past 75% of the prompt."""

    rule_id = "PL071"
    name = "instruction-buried"
    default_severity = Severity.WARNING

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        # Build a flat text with token-position mapping
        all_text = "\n".join(msg.content for msg in prompt_file.messages)
        total_tokens = prompt_file.total_tokens
        if not total_tokens or total_tokens == 0:
            return []

        # Approximate position by character ratio (good enough without tiktoken)
        total_chars = len(all_text)
        if total_chars == 0:
            return []

        violations: list[LintViolation] = []
        for match in _CRITICAL_KEYWORDS_RE.finditer(all_text):
            char_pos = match.start()
            position_pct = char_pos / total_chars
            if position_pct > 0.75:
                # Find approximate line number
                line_num = all_text[:char_pos].count("\n") + 1
                violations.append(
                    LintViolation(
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        message=(
                            f'Critical keyword "{match.group(0)}" appears at '
                            f"~{position_pct:.0%} of the prompt (past 75% threshold)."
                        ),
                        suggestion=(
                            "Move critical instructions to the beginning of the "
                            "prompt where they are more likely to be followed."
                        ),
                        path=prompt_file.path,
                        line=line_num,
                        rule_name=self.name,
                        fixable=False,
                    ),
                )
        return violations


class CompetingInstructionsRule(BaseRule):
    """PL072: Prompt contains contradictory statements across all messages."""

    rule_id = "PL072"
    name = "competing-instructions"
    default_severity = Severity.WARNING

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        all_text = " ".join(msg.content for msg in prompt_file.messages)

        violations: list[LintViolation] = []

        # Check hardcoded contradiction pairs
        for pat_a, pat_b in _COMPETING_CONTRADICTION_PAIRS:
            if pat_a.search(all_text) and pat_b.search(all_text):
                ma = pat_a.search(all_text)
                mb = pat_b.search(all_text)
                if ma and mb:
                    violations.append(
                        LintViolation(
                            rule_id=self.rule_id,
                            severity=self.default_severity,
                            message=(
                                f'Competing instructions: "{ma.group(0)}" vs '
                                f'"{mb.group(0)}".'
                            ),
                            suggestion=(
                                "Remove one competing instruction or add explicit "
                                "priority to clarify which takes precedence."
                            ),
                            path=prompt_file.path,
                            line=None,
                            rule_name=self.name,
                            fixable=False,
                        ),
                    )

        # Check instruction pairs with contradictory polarity
        sentences = _extract_instructions(all_text)
        for i, s1 in enumerate(sentences):
            for s2 in sentences[i + 1 :]:
                neg1 = _is_negative(s1)
                neg2 = _is_negative(s2)
                if neg1 == neg2:
                    continue
                w1 = _significant_words(s1)
                w2 = _significant_words(s2)
                # Lower threshold than PL013 (1 word overlap is enough)
                if len(w1 & w2) >= 2:
                    violations.append(
                        LintViolation(
                            rule_id=self.rule_id,
                            severity=self.default_severity,
                            message=(
                                f'Competing instructions: "{s1[:50]}..." vs '
                                f'"{s2[:50]}...".'
                            ),
                            suggestion=(
                                "Resolve the contradiction by removing one "
                                "instruction or adding explicit priority."
                            ),
                            path=prompt_file.path,
                            line=None,
                            rule_name=self.name,
                            fixable=False,
                        ),
                    )
        return violations


class NoExamplesRule(BaseRule):
    """PL073: Prompt over 500 tokens with no examples or demonstrations."""

    rule_id = "PL073"
    name = "no-examples"
    default_severity = Severity.INFO

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        total = prompt_file.total_tokens
        if total is None or total <= 500:
            return []

        all_text = " ".join(msg.content for msg in prompt_file.messages)
        for pattern in _EXAMPLE_PATTERNS:
            if pattern.search(all_text):
                return []

        return [
            LintViolation(
                rule_id=self.rule_id,
                severity=self.default_severity,
                message=(
                    f"Prompt has {total} tokens but contains no examples or "
                    "demonstrations."
                ),
                suggestion=(
                    "Add one or more examples (few-shot patterns) to improve "
                    "output quality and consistency."
                ),
                path=prompt_file.path,
                line=None,
                rule_name=self.name,
                fixable=False,
            ),
        ]


class WallOfTextRule(BaseRule):
    """PL074: Prompt exceeds 200 tokens with no structural markers."""

    rule_id = "PL074"
    name = "wall-of-text"
    default_severity = Severity.WARNING

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        total = prompt_file.total_tokens
        if total is None or total <= 200:
            return []

        all_text = " ".join(msg.content for msg in prompt_file.messages)
        for pattern in _STRUCTURE_PATTERNS:
            if pattern.search(all_text):
                return []

        return [
            LintViolation(
                rule_id=self.rule_id,
                severity=self.default_severity,
                message=(
                    f"Prompt has {total} tokens with no structural markers "
                    "(headers, bullets, numbered lists, delimiters)."
                ),
                suggestion=(
                    "Add structure using markdown headers, bullet points, "
                    "numbered lists, or section delimiters to improve readability."
                ),
                path=prompt_file.path,
                line=None,
                rule_name=self.name,
                fixable=False,
            ),
        ]
