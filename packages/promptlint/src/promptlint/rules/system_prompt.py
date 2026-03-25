"""System prompt rules: PL010, PL011, PL012, PL013, PL014."""

from __future__ import annotations

import re
from collections import Counter

from promptlint.models import LintConfig, LintViolation, PromptFile, Severity
from promptlint.rules.base import BaseRule

# ---------------------------------------------------------------------------
# PL012 injection detection patterns
# ---------------------------------------------------------------------------
INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"ignore (all |previous |above )*(instructions|prompts|rules|constraints)",
        re.IGNORECASE,
    ),
    re.compile(
        r"disregard (your|all) (previous |prior )?(instructions|context)",
        re.IGNORECASE,
    ),
    re.compile(r"you are now (a |an )?(?!helpful)", re.IGNORECASE),
    re.compile(
        r"forget (everything|all)( you (know|were told))?", re.IGNORECASE
    ),
    re.compile(r"act as (a |an )?(?!(helpful|professional|expert))", re.IGNORECASE),
    re.compile(r"new (persona|personality|role|identity):", re.IGNORECASE),
    re.compile(r"\[SYSTEM\]", re.IGNORECASE),
    re.compile(r"<\|system\|>", re.IGNORECASE),
    re.compile(r"###\s*(SYSTEM|INSTRUCTION)", re.IGNORECASE),
    re.compile(r"enter (developer|debug|admin|god) mode", re.IGNORECASE),
    re.compile(r"system override", re.IGNORECASE),
    re.compile(r"admin mode", re.IGNORECASE),
    re.compile(r"maintenance mode", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# PL013 conflicting instruction helpers
# ---------------------------------------------------------------------------
_MODAL_RE = re.compile(
    r"\b(must|should|always|never|do not|don't|shall|cannot|can't)\b",
    re.IGNORECASE,
)
_IMPERATIVE_START = re.compile(
    r"^(be |do |use |include |provide |ensure |make |keep |set |add |write |avoid |respond |return |output |format |generate |create |list |give )",
    re.IGNORECASE,
)

_CONTRADICTION_PAIRS: list[tuple[re.Pattern[str], re.Pattern[str]]] = [
    (
        re.compile(r"\b(be concise|be brief)\b", re.IGNORECASE),
        re.compile(
            r"\b(be thorough|be detailed|be comprehensive)\b", re.IGNORECASE
        ),
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


def _extract_imperative_sentences(text: str) -> list[str]:
    """Extract sentences that look like instructions."""
    sentences: list[str] = []
    for raw in re.split(r"[.!?\n]", text):
        s = raw.strip()
        if not s:
            continue
        if _MODAL_RE.search(s) or _IMPERATIVE_START.match(s):
            sentences.append(s)
    return sentences


def _significant_words(sentence: str) -> set[str]:
    """Return lowered non-trivial words from a sentence."""
    trivial = {"a", "an", "the", "to", "in", "of", "and", "or", "is", "be", "it", "for", "with", "not", "do", "don't"}
    return {
        w.lower()
        for w in re.findall(r"[a-zA-Z]{3,}", sentence)
        if w.lower() not in trivial
    }


def _is_negative(sentence: str) -> bool:
    return bool(re.search(r"\b(never|do not|don't|must not|cannot|can't|avoid)\b", sentence, re.IGNORECASE))


def _detect_conflicts(sentences: list[str]) -> list[tuple[str, str]]:
    """Return pairs of contradictory sentences."""
    conflicts: list[tuple[str, str]] = []
    # Check hardcoded contradiction pairs first
    full_text = " ".join(sentences)
    for pat_a, pat_b in _CONTRADICTION_PAIRS:
        if pat_a.search(full_text) and pat_b.search(full_text):
            ma = pat_a.search(full_text)
            mb = pat_b.search(full_text)
            if ma and mb:
                conflicts.append((ma.group(0), mb.group(0)))

    # Check always/never and must/do-not pairs with keyword overlap
    for i, s1 in enumerate(sentences):
        for s2 in sentences[i + 1 :]:
            neg1 = _is_negative(s1)
            neg2 = _is_negative(s2)
            if neg1 == neg2:
                continue
            w1 = _significant_words(s1)
            w2 = _significant_words(s2)
            overlap = w1 & w2
            if len(overlap) >= 2:
                conflicts.append((s1, s2))
    return conflicts


# ===================================================================
# Rule classes
# ===================================================================


class SystemPromptMissingRule(BaseRule):
    """PL010: No system role message found in a multi-message prompt."""

    rule_id = "PL010"
    name = "system-prompt-missing"
    default_severity = Severity.WARNING

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        if len(prompt_file.messages) <= 1:
            return []
        has_system = any(m.role == "system" for m in prompt_file.messages)
        if not has_system:
            return [
                LintViolation(
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    message="No system role message found in a multi-message prompt.",
                    suggestion="Add a system message to define assistant behavior and constraints.",
                    path=prompt_file.path,
                    line=1,
                    rule_name=self.name,
                    fixable=False,
                ),
            ]
        return []


class SystemPromptNotFirstRule(BaseRule):
    """PL011: A system message exists but is not the first message."""

    rule_id = "PL011"
    name = "system-prompt-not-first"
    default_severity = Severity.ERROR
    fixable = True

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        if not prompt_file.messages:
            return []
        system_indices = [
            i for i, m in enumerate(prompt_file.messages) if m.role == "system"
        ]
        if not system_indices:
            return []
        if system_indices[0] != 0:
            msg = prompt_file.messages[system_indices[0]]
            return [
                LintViolation(
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    message=(
                        f"System message found at position {system_indices[0] + 1} "
                        "instead of position 1."
                    ),
                    suggestion="Move the system message to the first position in the message list.",
                    path=prompt_file.path,
                    line=msg.line_start,
                    rule_name=self.name,
                    fixable=True,
                ),
            ]
        return []

    def fix(self, prompt_file: PromptFile, violation: LintViolation) -> str | None:
        """Move system message to first position.

        Only reliable for YAML/JSON formats.  Returns None for text/markdown.
        """
        from promptlint.models import PromptFormat

        if prompt_file.format not in (PromptFormat.YAML, PromptFormat.JSON):
            return None

        # Reorder messages: all system first, rest in original order
        system_msgs = [m for m in prompt_file.messages if m.role == "system"]
        other_msgs = [m for m in prompt_file.messages if m.role != "system"]
        reordered = system_msgs + other_msgs

        if prompt_file.format == PromptFormat.YAML:
            import yaml

            data = yaml.safe_load(prompt_file.raw_content) or {}
            data["messages"] = [
                {"role": m.role, "content": m.content} for m in reordered
            ]
            return yaml.dump(data, default_flow_style=False, allow_unicode=True)

        if prompt_file.format == PromptFormat.JSON:
            import json

            data = json.loads(prompt_file.raw_content)
            data["messages"] = [
                {"role": m.role, "content": m.content} for m in reordered
            ]
            return json.dumps(data, indent=2, ensure_ascii=False)

        return None


class InjectionVectorDetectedRule(BaseRule):
    """PL012: Content contains patterns indicative of prompt injection."""

    rule_id = "PL012"
    name = "injection-vector-detected"
    default_severity = Severity.ERROR

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        violations: list[LintViolation] = []
        for msg in prompt_file.messages:
            # Only check non-system messages for injection patterns
            if msg.role == "system":
                continue
            for pattern in INJECTION_PATTERNS:
                match = pattern.search(msg.content)
                if match:
                    violations.append(
                        LintViolation(
                            rule_id=self.rule_id,
                            severity=self.default_severity,
                            message=(
                                f'Content matches injection pattern: "{match.group(0)}"'
                            ),
                            suggestion=(
                                "Remove or sanitize instruction-override language "
                                "from user-facing content."
                            ),
                            path=prompt_file.path,
                            line=msg.line_start,
                            rule_name=self.name,
                            fixable=False,
                        ),
                    )
                    break  # one violation per message
        return violations


class ConflictingInstructionsRule(BaseRule):
    """PL013: System prompt contains self-contradictory instruction patterns."""

    rule_id = "PL013"
    name = "conflicting-instructions"
    default_severity = Severity.WARNING

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        system_msgs = [m for m in prompt_file.messages if m.role == "system"]
        if not system_msgs:
            return []

        violations: list[LintViolation] = []
        for msg in system_msgs:
            sentences = _extract_imperative_sentences(msg.content)
            conflicts = _detect_conflicts(sentences)
            for s1, s2 in conflicts:
                violations.append(
                    LintViolation(
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        message=(
                            f'Conflicting instructions detected: "{s1[:60]}" '
                            f'vs "{s2[:60]}".'
                        ),
                        suggestion=(
                            "Remove one of the conflicting instructions or add "
                            "explicit priority to resolve the ambiguity."
                        ),
                        path=prompt_file.path,
                        line=msg.line_start,
                        rule_name=self.name,
                        fixable=False,
                    ),
                )
        return violations


class SystemPromptTooLongRule(BaseRule):
    """PL014: System message alone exceeds the system prompt token threshold."""

    rule_id = "PL014"
    name = "system-prompt-too-long"
    default_severity = Severity.WARNING

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        violations: list[LintViolation] = []
        for msg in prompt_file.messages:
            if msg.role != "system":
                continue
            if msg.token_count is not None and msg.token_count > config.system_prompt_threshold:
                violations.append(
                    LintViolation(
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        message=(
                            f"System message uses {msg.token_count} tokens, "
                            f"exceeding the threshold of {config.system_prompt_threshold}."
                        ),
                        suggestion=(
                            "Shorten the system prompt by extracting detailed "
                            "instructions into user messages or separate context."
                        ),
                        path=prompt_file.path,
                        line=msg.line_start,
                        rule_name=self.name,
                        fixable=False,
                    ),
                )
        return violations
