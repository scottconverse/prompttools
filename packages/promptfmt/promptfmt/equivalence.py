"""Semantic equivalence checking for promptfmt.

Verifies that formatting did not alter the semantic content of a prompt.
"""

from __future__ import annotations

from prompttools_core.models import PromptFile


def _normalize_whitespace(text: str) -> str:
    """Normalize whitespace for comparison (collapse runs, strip)."""
    return " ".join(text.split())


def is_equivalent(original: PromptFile, formatted: PromptFile) -> bool:
    """Check whether two PromptFiles are semantically equivalent.

    Two prompts are equivalent if:
    - Same number of messages
    - Each message has the same role
    - Each message content is identical after whitespace normalization
    - Same variable names (syntax may differ)
    - Same metadata keys and values
    """
    # Message count
    if len(original.messages) != len(formatted.messages):
        return False

    # Message content and roles
    for orig_msg, fmt_msg in zip(original.messages, formatted.messages):
        if orig_msg.role != fmt_msg.role:
            return False
        if _normalize_whitespace(orig_msg.content) != _normalize_whitespace(fmt_msg.content):
            return False

    # Variable names (not syntax style)
    if set(original.variables.keys()) != set(formatted.variables.keys()):
        return False

    # Metadata
    if original.metadata != formatted.metadata:
        return False

    return True
