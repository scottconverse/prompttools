"""Core data models for the prompttools suite.

All models use Pydantic v2 syntax. These are the canonical representations
that every tool in the suite operates on.
"""

from __future__ import annotations

import hashlib
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, computed_field


class PromptFormat(str, Enum):
    """Supported prompt file formats."""

    TEXT = "text"
    MARKDOWN = "md"
    YAML = "yaml"
    JSON = "json"


class Message(BaseModel):
    """Represents a single turn within a prompt conversation."""

    model_config = {"frozen": False}

    role: Literal["system", "user", "assistant", "tool"] = Field(
        ..., description="Message role"
    )
    content: str = Field(..., description="The text content of the message")
    line_start: Optional[int] = Field(
        default=None,
        description="Line number where this message begins in the source file",
    )
    line_end: Optional[int] = Field(
        default=None,
        description="Line number where this message ends in the source file",
    )
    token_count: Optional[int] = Field(
        default=None,
        description="Token count, populated by the tokenizer",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata attached to this message",
    )


class PromptFile(BaseModel):
    """Represents a single parsed prompt file."""

    model_config = {"frozen": False}

    path: Path = Field(..., description="Path to the source file")
    format: PromptFormat = Field(..., description="Detected format")
    raw_content: str = Field(..., description="Original unmodified file content")
    messages: list[Message] = Field(
        default_factory=list, description="Parsed list of messages"
    )
    variables: dict[str, str] = Field(
        default_factory=dict,
        description="Extracted template variables mapped to syntax style",
    )
    variable_defaults: dict[str, str] = Field(
        default_factory=dict,
        description="Default values for variables extracted from metadata",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Front-matter or top-level YAML/JSON metadata",
    )
    total_tokens: Optional[int] = Field(
        default=None,
        description="Total token count across all messages",
    )
    content_hash: str = Field(
        default="",
        description="SHA256 hash of raw_content for caching",
    )

    def model_post_init(self, __context: Any) -> None:
        """Compute content_hash if not already set."""
        if not self.content_hash and self.raw_content:
            self.content_hash = hashlib.sha256(
                self.raw_content.encode("utf-8")
            ).hexdigest()

    def system_message(self) -> Optional[Message]:
        """Return the first system message, or None."""
        for msg in self.messages:
            if msg.role == "system":
                return msg
        return None

    def user_messages(self) -> list[Message]:
        """Return all user messages."""
        return [msg for msg in self.messages if msg.role == "user"]

    def has_role(self, role: str) -> bool:
        """Return True if any message has the given role."""
        return any(msg.role == role for msg in self.messages)


class PipelineStage(BaseModel):
    """Represents one stage in a prompt pipeline."""

    model_config = {"frozen": False}

    name: str = Field(..., description="Stage name")
    file: Optional[Path] = Field(
        default=None, description="Path to the prompt file for this stage"
    )
    persona: Optional[str] = Field(
        default=None, description="Declared persona/role for this stage"
    )
    expected_output_tokens: int = Field(
        default=0, description="Estimated output token count"
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="Names of stages whose output this stage consumes",
    )
    prompt_file: Optional[PromptFile] = Field(
        default=None, description="Resolved prompt file (populated during loading)"
    )


class PromptPipeline(BaseModel):
    """Represents an ordered set of prompt files forming a multi-stage pipeline."""

    model_config = {"frozen": False}

    name: str = Field(..., description="Pipeline name")
    model: Optional[str] = Field(
        default=None, description="Default model for pipeline stages"
    )
    manifest_path: Path = Field(
        ..., description="Path to the pipeline manifest"
    )
    stages: list[PipelineStage] = Field(
        default_factory=list, description="Ordered list of stages"
    )

    total_tokens: Optional[int] = Field(
        default=None, description="Sum of all stage token counts"
    )
    cumulative_tokens: Optional[list[int]] = Field(
        default=None,
        description="Running total of tokens at each stage",
    )


class ModelProfile(BaseModel):
    """Configuration for a specific LLM model."""

    model_config = {"frozen": True}

    name: str = Field(..., description="Model identifier")
    context_window: int = Field(
        ..., description="Maximum context window in tokens"
    )
    encoding: str = Field(
        ..., description="tiktoken encoding name"
    )
    provider: str = Field(
        default="unknown", description="Provider: openai, anthropic, google, custom"
    )
    input_price_per_mtok: Optional[float] = Field(
        default=None, description="Cost per million input tokens in USD"
    )
    output_price_per_mtok: Optional[float] = Field(
        default=None, description="Cost per million output tokens in USD"
    )
    max_output_tokens: Optional[int] = Field(
        default=None, description="Maximum output tokens"
    )
    supports_system_message: bool = Field(
        default=True, description="Whether the model supports system messages"
    )
    supports_tools: bool = Field(
        default=False, description="Whether the model supports tool use"
    )
    approximate_tokenizer: bool = Field(
        default=False,
        description="True if the tokenizer is an approximation",
    )

    @property
    def tokenizer_encoding(self) -> str:
        """Backward-compatible alias for encoding."""
        return self.encoding


class ToolConfig(BaseModel):
    """Base configuration shared by all tools in the suite."""

    model_config = {"frozen": False}

    model: Optional[str] = Field(
        default=None, description="Model profile name"
    )
    tokenizer_encoding: Optional[str] = Field(
        default=None, description="Override tiktoken encoding"
    )
    exclude: list[str] = Field(
        default_factory=list, description="Glob patterns for excluded files"
    )
    plugins: list[str] = Field(
        default_factory=list, description="Plugin directory paths"
    )
    cache_enabled: bool = Field(
        default=False, description="Enable content caching"
    )
    cache_dir: Path = Field(
        default=Path(".prompttools-cache"), description="Cache directory"
    )
    extra: dict[str, Any] = Field(
        default_factory=dict, description="Tool-specific configuration"
    )
