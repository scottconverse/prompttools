"""Shared fixtures for promptvault tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from promptvault.models import PackageManifest, PromptEntry
from promptvault.registry import LocalRegistry


@pytest.fixture
def sample_manifest() -> PackageManifest:
    """A sample package manifest for testing."""
    return PackageManifest(
        name="@test/greeting-prompts",
        version="1.0.0",
        description="A collection of greeting prompts",
        author="Test Author",
        license="MIT",
        model="claude-4-sonnet",
        prompts=[
            PromptEntry(
                file=Path("prompts/hello.yaml"),
                name="hello",
                description="A hello world prompt",
                variables=["user_name"],
            ),
            PromptEntry(
                file=Path("prompts/farewell.yaml"),
                name="farewell",
                description="A farewell prompt",
                variables=["user_name", "reason"],
            ),
        ],
        dependencies={},
    )


@pytest.fixture
def sample_manifest_with_deps() -> PackageManifest:
    """A manifest with dependencies declared."""
    return PackageManifest(
        name="@test/advanced-prompts",
        version="2.0.0",
        description="Advanced prompts with dependencies",
        author="Test Author",
        prompts=[
            PromptEntry(
                file=Path("prompts/chain.yaml"),
                name="chain",
                description="A chain prompt",
            ),
        ],
        dependencies={
            "@test/greeting-prompts": "^1.0.0",
            "@test/utils": "~0.2.0",
        },
    )


@pytest.fixture
def manifest_dir(tmp_path: Path, sample_manifest: PackageManifest) -> Path:
    """Create a manifest directory on disk with promptvault.yaml and prompt files."""
    pkg_dir = tmp_path / "my-package"
    pkg_dir.mkdir()

    # Write manifest
    manifest_data = sample_manifest.model_dump(mode="json")
    # Convert Path objects to strings for YAML serialization
    for p in manifest_data.get("prompts", []):
        p["file"] = str(p["file"])
    (pkg_dir / "promptvault.yaml").write_text(
        yaml.dump(manifest_data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )

    # Create prompt files
    prompts_dir = pkg_dir / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "hello.yaml").write_text(
        "messages:\n  - role: user\n    content: Hello {{user_name}}\n",
        encoding="utf-8",
    )
    (prompts_dir / "farewell.yaml").write_text(
        "messages:\n  - role: user\n    content: Goodbye {{user_name}}, {{reason}}\n",
        encoding="utf-8",
    )

    return pkg_dir


@pytest.fixture
def registry(tmp_path: Path) -> LocalRegistry:
    """Create a temporary local registry."""
    registry_dir = tmp_path / "registry"
    return LocalRegistry(registry_dir=registry_dir)


@pytest.fixture
def populated_registry(
    registry: LocalRegistry, manifest_dir: Path
) -> LocalRegistry:
    """A registry with a sample package already published."""
    registry.publish(manifest_dir)
    return registry
