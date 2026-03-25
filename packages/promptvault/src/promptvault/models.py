"""Data models for promptvault.

All models use Pydantic v2 syntax. These represent prompt packages,
catalog entries, and lockfile structures for the local registry.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class PromptEntry(BaseModel):
    """A single prompt file within a package."""

    file: Path = Field(..., description="Relative path to the prompt file")
    name: str = Field(..., description="Human-readable name for the prompt")
    description: str = Field(default="", description="Optional description")
    variables: list[str] = Field(
        default_factory=list, description="Template variable names"
    )
    model: Optional[str] = Field(
        default=None, description="Recommended model for this prompt"
    )


class QualityConfig(BaseModel):
    """Quality gate configuration for a package."""

    lint: str = Field(default="optional", description="Lint gate: required, optional, skip")
    test: str = Field(default="optional", description="Test gate: required, optional, skip")
    format: str = Field(
        default="optional", description="Format gate: required, optional, skip"
    )


class PackageManifest(BaseModel):
    """The promptvault.yaml manifest for a prompt package."""

    name: str = Field(..., description="Package name in @scope/name format")
    version: str = Field(..., description="Semantic version string")
    description: str = Field(..., description="Package description")
    author: str = Field(..., description="Package author")
    license: Optional[str] = Field(default=None, description="SPDX license identifier")
    model: Optional[str] = Field(
        default=None, description="Default model for all prompts"
    )
    prompts: list[PromptEntry] = Field(
        default_factory=list, description="List of prompt entries"
    )
    dependencies: dict[str, str] = Field(
        default_factory=dict,
        description="Dependencies as name -> version range mapping",
    )
    quality: QualityConfig = Field(
        default_factory=QualityConfig, description="Quality gate configuration"
    )


class CatalogEntry(BaseModel):
    """An entry in the registry catalog (index.json)."""

    name: str = Field(..., description="Package name")
    latest_version: str = Field(..., description="Latest published version")
    versions: list[str] = Field(
        default_factory=list, description="All published versions"
    )
    description: str = Field(default="", description="Package description")
    model: Optional[str] = Field(
        default=None, description="Default model for the package"
    )
    total_prompts: int = Field(default=0, description="Number of prompts in the package")
    published_at: str = Field(..., description="ISO 8601 timestamp of last publish")
    integrity: str = Field(..., description="SHA-256 hash of the package contents")


class LockEntry(BaseModel):
    """A resolved dependency entry in the lockfile."""

    version: str = Field(..., description="Exact resolved version")
    integrity: str = Field(..., description="SHA-256 hash for verification")
    resolved: str = Field(
        ..., description="Path in the registry where the package is stored"
    )


class Lockfile(BaseModel):
    """The promptvault.lock lockfile for reproducible installs."""

    lockfile_version: int = Field(default=1, description="Lockfile format version")
    resolved: dict[str, LockEntry] = Field(
        default_factory=dict,
        description="Resolved dependencies as name -> LockEntry mapping",
    )
