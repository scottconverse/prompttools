"""Shared variable extraction logic used by all format parsers."""

from __future__ import annotations

import re

# Patterns for template variables
JINJA_VAR_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")       # {{var}}
FSTRING_VAR_RE = re.compile(r"(?<!\{)\{(\w+)\}(?!\})")   # {var} (not {{var}})
XML_VAR_RE = re.compile(r"<(\w+)>(?!</)")                 # <var> (not closing tags)

# Combined pattern for detecting any variable style
ALL_VAR_RE = re.compile(
    r"\{\{\s*(\w+)\s*\}\}"       # {{var}}
    r"|(?<!\{)\{(\w+)\}(?!\})"   # {var}
    r"|<(\w+)>"                   # <var>
)

# Common XML/HTML tags to exclude from variable detection
EXCLUDED_XML_TAGS = frozenset({
    "br", "hr", "p", "div", "span", "a", "b", "i", "u", "em", "strong",
    "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "table", "tr",
    "td", "th", "thead", "tbody", "img", "code", "pre", "blockquote",
    "html", "head", "body", "meta", "link", "script", "style", "section",
    "article", "nav", "footer", "header", "main", "aside", "form", "input",
    "button", "label", "select", "option", "textarea",
})


def extract_variables(text: str) -> dict[str, str]:
    """Detect ``{{var}}``, ``{var}``, and ``<var>`` patterns in *text*.

    Returns a dict mapping variable name to the syntax style used
    (``jinja``, ``fstring``, or ``xml``).
    """
    variables: dict[str, str] = {}

    for match in JINJA_VAR_RE.finditer(text):
        variables[match.group(1)] = "jinja"

    for match in FSTRING_VAR_RE.finditer(text):
        name = match.group(1)
        if name not in variables:
            variables[name] = "fstring"

    for match in XML_VAR_RE.finditer(text):
        name = match.group(1)
        if name.lower() not in EXCLUDED_XML_TAGS and name not in variables:
            variables[name] = "xml"

    return variables
