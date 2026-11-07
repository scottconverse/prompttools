"""Variable rules: PL030, PL031, PL032, PL033."""

from __future__ import annotations

import re

from promptlint.models import LintConfig, LintViolation, PromptFile, Severity
from promptlint.rules.base import BaseRule

# Variable syntaxes: Jinja2 {{var}}, Python {var}, XML <var>
_JINJA_VAR_RE = re.compile(r"\{\{(\w+)\}\}")
_PYTHON_VAR_RE = re.compile(r"(?<!\{)\{(\w+)\}(?!\})")
_XML_VAR_RE = re.compile(r"<(\w+)>(?!.*</\1>)", re.DOTALL)

# More restrictive XML pattern: only match single-word tags that look like
# template variables (lowercase, underscores) and not common XML/HTML tags.
_HTML_TAGS = frozenset({
    "p", "br", "hr", "div", "span", "a", "b", "i", "u", "em", "strong",
    "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "table", "tr",
    "td", "th", "thead", "tbody", "img", "code", "pre", "blockquote",
    "section", "article", "header", "footer", "nav", "main", "aside",
    "details", "summary", "figure", "figcaption", "mark", "small", "sub",
    "sup", "del", "ins", "s",
})

_XML_TEMPLATE_VAR_RE = re.compile(r"<([a-z][a-z0-9_]*)>")


def _find_all_content_vars(messages_text: str) -> dict[str, list[str]]:
    """Find all template variables in message content, grouped by syntax style.

    Returns a dict mapping style name to list of variable names found.
    """
    result: dict[str, list[str]] = {
        "jinja2": [],
        "python": [],
        "xml": [],
    }

    for match in _JINJA_VAR_RE.finditer(messages_text):
        result["jinja2"].append(match.group(1))

    for match in _PYTHON_VAR_RE.finditer(messages_text):
        result["python"].append(match.group(1))

    for match in _XML_TEMPLATE_VAR_RE.finditer(messages_text):
        name = match.group(1)
        if name.lower() not in _HTML_TAGS:
            result["xml"].append(name)

    return result


def _all_var_names(var_map: dict[str, list[str]]) -> set[str]:
    """Collect all variable names across styles."""
    names: set[str] = set()
    for names_list in var_map.values():
        names.update(names_list)
    return names


class UndefinedVariableRule(BaseRule):
    """PL030: A variable placeholder is referenced but not declared."""

    rule_id = "PL030"
    name = "undefined-variable"
    default_severity = Severity.ERROR

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        all_text = " ".join(msg.content for msg in prompt_file.messages)
        content_vars = _find_all_content_vars(all_text)
        referenced = _all_var_names(content_vars)
        declared = set(prompt_file.variables.keys())

        violations: list[LintViolation] = []
        for var_name in sorted(referenced - declared):
            violations.append(
                LintViolation(
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    message=f"Variable '{var_name}' is referenced but not declared.",
                    suggestion=(
                        f"Add '{var_name}' to the variables block with a description "
                        "and optional default value."
                    ),
                    path=prompt_file.path,
                    line=None,
                    rule_name=self.name,
                    fixable=False,
                ),
            )
        return violations


class UnusedVariableRule(BaseRule):
    """PL031: A variable is declared but never referenced in any message."""

    rule_id = "PL031"
    name = "unused-variable"
    default_severity = Severity.WARNING

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        if not prompt_file.variables:
            return []

        all_text = " ".join(msg.content for msg in prompt_file.messages)
        content_vars = _find_all_content_vars(all_text)
        referenced = _all_var_names(content_vars)
        declared = set(prompt_file.variables.keys())

        violations: list[LintViolation] = []
        for var_name in sorted(declared - referenced):
            violations.append(
                LintViolation(
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    message=f"Variable '{var_name}' is declared but never used.",
                    suggestion=(
                        f"Remove '{var_name}' from the variables block or "
                        "reference it in a message."
                    ),
                    path=prompt_file.path,
                    line=None,
                    rule_name=self.name,
                    fixable=False,
                ),
            )
        return violations


class VariableNoDefaultRule(BaseRule):
    """PL032: A variable is declared but has no default value specified."""

    rule_id = "PL032"
    name = "variable-no-default"
    default_severity = Severity.INFO

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        violations: list[LintViolation] = []
        for var_name, var_value in sorted(prompt_file.variables.items()):
            if not var_value or var_value.strip() == "":
                violations.append(
                    LintViolation(
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        message=f"Variable '{var_name}' has no default value.",
                        suggestion=(
                            f"Provide a sensible default for '{var_name}' to make "
                            "the prompt testable without external inputs."
                        ),
                        path=prompt_file.path,
                        line=None,
                        rule_name=self.name,
                        fixable=False,
                    ),
                )
        return violations


class VariableFormatInconsistentRule(BaseRule):
    """PL033: Variable placeholder style is mixed across the file."""

    rule_id = "PL033"
    name = "variable-format-inconsistent"
    default_severity = Severity.WARNING
    fixable = True

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        all_text = " ".join(msg.content for msg in prompt_file.messages)
        content_vars = _find_all_content_vars(all_text)

        styles_with_vars = [
            style for style, names in content_vars.items() if names
        ]
        if len(styles_with_vars) <= 1:
            return []

        return [
            LintViolation(
                rule_id=self.rule_id,
                severity=self.default_severity,
                message=(
                    f"Mixed variable styles detected: "
                    f"{', '.join(styles_with_vars)}."
                ),
                suggestion=(
                    "Normalize all variables to {{variable_name}} (Jinja2) style "
                    "for consistency."
                ),
                path=prompt_file.path,
                line=None,
                rule_name=self.name,
                fixable=True,
            ),
        ]

    def fix(self, prompt_file: PromptFile, violation: LintViolation) -> str | None:
        """Normalize all variable references to {{variable_name}} style."""
        content = prompt_file.raw_content

        # Replace Python-style {var} with {{var}} (avoid already-doubled)
        def _replace_python(m: re.Match[str]) -> str:
            return "{{" + m.group(1) + "}}"

        content = _PYTHON_VAR_RE.sub(_replace_python, content)

        # Replace XML-style <var> with {{var}} (only template vars)
        def _replace_xml(m: re.Match[str]) -> str:
            name = m.group(1)
            if name.lower() in _HTML_TAGS:
                return m.group(0)
            return "{{" + name + "}}"

        content = _XML_TEMPLATE_VAR_RE.sub(_replace_xml, content)

        return content
