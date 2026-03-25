"""promptfmt: Auto-formatter for LLM prompt files."""

from promptfmt.formatter import FmtConfig, FormattedResult, format_content, format_file
from promptfmt.equivalence import is_equivalent

__version__ = "1.0.0"

__all__ = [
    "FmtConfig",
    "FormattedResult",
    "format_content",
    "format_file",
    "is_equivalent",
]
