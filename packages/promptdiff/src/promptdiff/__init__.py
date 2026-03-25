"""promptdiff: Semantic diff for LLM prompt changes.

Public API exports for convenience imports::

    from promptdiff import diff_files, PromptDiff, format_text
"""

from promptdiff.models import (
    BreakingChange,
    ChangeStatus,
    MessageDiff,
    MetadataDiff,
    PromptDiff,
    TokenDelta,
    VariableDiff,
)
from promptdiff.differ import (
    compute_token_delta,
    diff_files,
    diff_messages,
    diff_metadata,
    diff_variables,
)
from promptdiff.analyzer import analyze_breaking_changes
from promptdiff.reporter import format_json, format_markdown, format_text

__version__ = "1.0.0"

__all__ = [
    # Models
    "BreakingChange",
    "ChangeStatus",
    "MessageDiff",
    "MetadataDiff",
    "PromptDiff",
    "TokenDelta",
    "VariableDiff",
    # Differ
    "compute_token_delta",
    "diff_files",
    "diff_messages",
    "diff_metadata",
    "diff_variables",
    # Analyzer
    "analyze_breaking_changes",
    # Reporter
    "format_json",
    "format_markdown",
    "format_text",
    # Version
    "__version__",
]
