"""File parser for promptlint.

Delegates to prompttools-core for parsing, re-exporting the public API
so existing imports continue to work.
"""

from __future__ import annotations

from pathlib import Path

from prompttools_core.parser import (  # noqa: F401
    parse_file,
    parse_stdin,
)
from prompttools_core.parser import parse_pipeline as _parse_pipeline
from prompttools_core.formats._variables import extract_variables as _extract_variables  # noqa: F401

# Re-export for backward compat with the old function name
from prompttools_core.models import (  # noqa: F401
    Message,
    PipelineStage,
    PromptFile,
    PromptFormat,
    PromptPipeline,
)


def parse_pipeline_manifest(path: Path) -> PromptPipeline:
    """Parse a pipeline manifest. Delegates to prompttools-core.

    This wrapper preserves the old function name for backward compatibility.
    """
    return _parse_pipeline(path)
