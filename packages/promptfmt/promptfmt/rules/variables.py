"""Variable syntax normalization rules for promptfmt."""

from __future__ import annotations

import re

# Variable patterns
_JINJA_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")
_FSTRING_RE = re.compile(r"(?<!\{)\{(\w+)\}(?!\})")
_XML_RE = re.compile(r"<(\w+)>(?!</)")

# Code block/inline code detection
_CODE_BLOCK_RE = re.compile(r"^```")
_INLINE_CODE_RE = re.compile(r"`[^`]+`")

# Tags to exclude from variable detection
_EXCLUDED_TAGS = frozenset({
    "br", "hr", "p", "div", "span", "a", "b", "i", "u", "em", "strong",
    "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "table", "tr",
    "td", "th", "thead", "tbody", "img", "code", "pre", "blockquote",
    "html", "head", "body", "meta", "link", "script", "style", "section",
    "article", "nav", "footer", "header", "main", "aside", "form", "input",
    "button", "label", "select", "option", "textarea",
})

_STYLES = {
    "double_brace": ("{{", "}}"),
    "single_brace": ("{", "}"),
    "angle_bracket": ("<", ">"),
}


def _replace_in_text(text: str, target_style: str) -> str:
    """Replace all variable syntaxes in text (not code) to target style."""
    if target_style not in _STYLES:
        return text

    open_d, close_d = _STYLES[target_style]

    # Protect inline code spans by replacing them temporarily
    code_spans: list[str] = []
    def _save_code(m: re.Match) -> str:
        code_spans.append(m.group(0))
        return f"\x00CODE{len(code_spans) - 1}\x00"

    text = _INLINE_CODE_RE.sub(_save_code, text)

    # Replace jinja: {{var}} -> target
    def _replace_jinja(m: re.Match) -> str:
        name = m.group(1)
        return f"{open_d}{name}{close_d}"

    # Replace fstring: {var} -> target (only if target isn't single_brace)
    def _replace_fstring(m: re.Match) -> str:
        name = m.group(1)
        return f"{open_d}{name}{close_d}"

    # Replace xml: <var> -> target (only for non-HTML tags)
    def _replace_xml(m: re.Match) -> str:
        name = m.group(1)
        if name.lower() in _EXCLUDED_TAGS:
            return m.group(0)
        return f"{open_d}{name}{close_d}"

    text = _JINJA_RE.sub(_replace_jinja, text)
    if target_style != "single_brace":
        text = _FSTRING_RE.sub(_replace_fstring, text)
    if target_style != "angle_bracket":
        text = _XML_RE.sub(_replace_xml, text)

    # Restore code spans
    for i, span in enumerate(code_spans):
        text = text.replace(f"\x00CODE{i}\x00", span)

    return text


def apply(content: str, style: str = "double_brace") -> str:
    """Normalize all variable references to a single syntax style.

    Parameters
    ----------
    content:
        The file content.
    style:
        Target style: ``"double_brace"``, ``"single_brace"``, ``"angle_bracket"``.
    """
    lines = content.split("\n")
    result: list[str] = []
    in_code_block = False

    for line in lines:
        if _CODE_BLOCK_RE.match(line):
            in_code_block = not in_code_block
            result.append(line)
            continue

        if in_code_block:
            result.append(line)
            continue

        result.append(_replace_in_text(line, style))

    return "\n".join(result)
