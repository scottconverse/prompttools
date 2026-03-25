"""Data models for promptdiff.

All models use Pydantic v2 syntax. These define the structured representation
of prompt diffs, including message-level changes, variable changes, token
deltas, and breaking change classification.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, computed_field


class ChangeStatus(str, Enum):
    """Status of a change between two versions."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class MessageDiff(BaseModel):
    """Diff of a single message between old and new prompt versions."""

    status: ChangeStatus = Field(..., description="Change status for this message")
    role: str = Field(..., description="Message role (system, user, assistant, tool)")
    old_content: Optional[str] = Field(
        default=None, description="Content in the old version"
    )
    new_content: Optional[str] = Field(
        default=None, description="Content in the new version"
    )
    content_diff: Optional[str] = Field(
        default=None, description="Unified diff of the content"
    )
    token_delta: int = Field(
        default=0, description="Change in token count for this message"
    )
    changes: list[str] = Field(
        default_factory=list,
        description="Human-readable descriptions of changes",
    )


class VariableDiff(BaseModel):
    """Diff of a template variable between old and new prompt versions."""

    name: str = Field(..., description="Variable name")
    status: ChangeStatus = Field(..., description="Change status for this variable")
    old_default: Optional[str] = Field(
        default=None, description="Default value in the old version"
    )
    new_default: Optional[str] = Field(
        default=None, description="Default value in the new version"
    )
    is_breaking: bool = Field(
        default=False,
        description="True if this is a breaking change",
    )


class MetadataDiff(BaseModel):
    """Diff of a metadata key between old and new prompt versions."""

    key: str = Field(..., description="Metadata key")
    status: ChangeStatus = Field(..., description="Change status for this key")
    old_value: Optional[Any] = Field(
        default=None, description="Value in the old version"
    )
    new_value: Optional[Any] = Field(
        default=None, description="Value in the new version"
    )


class TokenDelta(BaseModel):
    """Token count comparison between old and new prompt versions."""

    old_total: int = Field(..., description="Total tokens in old version")
    new_total: int = Field(..., description="Total tokens in new version")
    delta: int = Field(..., description="Change in token count (new - old)")
    percent_change: float = Field(
        ..., description="Percentage change in token count"
    )


class BreakingChange(BaseModel):
    """A detected breaking change between prompt versions."""

    category: str = Field(
        ...,
        description="Category: variable, message, model, role",
    )
    description: str = Field(
        ..., description="Human-readable description of the breaking change"
    )
    severity: str = Field(
        ..., description="Severity: high, medium, low"
    )


class PromptDiff(BaseModel):
    """Complete structured diff between two prompt file versions."""

    file_path: Path = Field(..., description="Path to the diffed file")
    old_hash: str = Field(..., description="SHA256 hash of the old content")
    new_hash: str = Field(..., description="SHA256 hash of the new content")
    message_diffs: list[MessageDiff] = Field(
        default_factory=list,
        description="Per-message diffs",
    )
    variable_diffs: list[VariableDiff] = Field(
        default_factory=list,
        description="Per-variable diffs",
    )
    metadata_diffs: list[MetadataDiff] = Field(
        default_factory=list,
        description="Per-metadata-key diffs",
    )
    token_delta: TokenDelta = Field(
        ..., description="Token count comparison"
    )
    breaking_changes: list[BreakingChange] = Field(
        default_factory=list,
        description="Detected breaking changes",
    )

    @computed_field  # type: ignore[misc]
    @property
    def is_breaking(self) -> bool:
        """True if any breaking changes were detected."""
        return len(self.breaking_changes) > 0
