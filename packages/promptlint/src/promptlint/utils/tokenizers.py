"""tiktoken wrapper for token counting.

Delegates to prompttools-core for all tokenization functionality.
"""

from __future__ import annotations

# Re-export everything from prompttools-core
from prompttools_core.tokenizer import (  # noqa: F401
    count_tokens,
    get_encoding,
)
