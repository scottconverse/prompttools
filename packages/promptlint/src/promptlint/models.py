"""Core data models for promptlint.

Shared models are imported from prompttools-core.
Lint-specific models (Severity, LintViolation, LintConfig) remain here.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

# Re-export shared models from prompttools-core so existing imports work
from prompttools_core.models import (  # noqa: F401
    Message,
    ModelProfile,
    PipelineStage,
    PromptFile,
    PromptFormat,
    PromptPipeline,
)


class Severity(str, Enum):
    """Severity levels for lint violations."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class LintViolation(BaseModel):
    """Represents a single rule violation produced by the engine."""

    model_config = {"frozen": False}

    rule_id: str = Field(..., description="Rule identifier, e.g. PL001")
    severity: Severity = Field(..., description="Violation severity level")
    message: str = Field(
        ..., description="Human-readable description of the violation"
    )
    suggestion: Optional[str] = Field(
        default=None, description="Optional actionable fix suggestion"
    )
    path: Path = Field(
        ..., description="Source file where the violation was found"
    )
    line: Optional[int] = Field(
        default=None, description="Line number of the violation, if applicable"
    )
    rule_name: str = Field(
        ...,
        description="Short slug name of the rule, e.g. token-budget-exceeded",
    )
    fixable: bool = Field(
        default=False,
        description="Whether this violation can be auto-fixed",
    )


class LintConfig(BaseModel):
    """Merged configuration from file + CLI flags + defaults."""

    model_config = {"frozen": False}

    model: Optional[str] = Field(
        default=None,
        description="Model profile name (auto-sets context window + tokenizer)",
    )
    tokenizer_encoding: str = Field(
        default="cl100k_base", description="tiktoken encoding name"
    )
    token_warn_threshold: int = Field(
        default=2048, description="PL001 warning threshold"
    )
    token_error_threshold: int = Field(
        default=4096, description="PL002 error threshold"
    )
    system_prompt_threshold: int = Field(
        default=1024, description="PL014 system prompt threshold"
    )
    stop_word_ratio: float = Field(
        default=0.60, description="PL003 stop-word ratio threshold"
    )
    max_line_length: int = Field(
        default=500, description="PL024 character limit"
    )
    repetition_threshold: int = Field(
        default=3, description="PL023 occurrence count"
    )
    rule_overrides: dict[str, str] = Field(
        default_factory=dict, description="Per-rule severity overrides"
    )
    ignored_rules: list[str] = Field(
        default_factory=list, description="Globally ignored rule IDs"
    )
    exclude_patterns: list[str] = Field(
        default_factory=list, description="Glob patterns for excluded files"
    )
    plugin_dirs: list[Path] = Field(
        default_factory=list,
        description="Directories containing custom rule plugins",
    )
    context_window: Optional[int] = Field(
        default=None,
        description="Model context window (auto-set by model profile, or manual)",
    )
