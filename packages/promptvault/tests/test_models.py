"""Tests for promptvault data models."""

from __future__ import annotations

from pathlib import Path

import pytest

from promptvault.models import (
    CatalogEntry,
    LockEntry,
    Lockfile,
    PackageManifest,
    PromptEntry,
    QualityConfig,
)


class TestPromptEntry:
    """Tests for the PromptEntry model."""

    def test_minimal(self) -> None:
        entry = PromptEntry(file=Path("hello.yaml"), name="hello")
        assert entry.file == Path("hello.yaml")
        assert entry.name == "hello"
        assert entry.description == ""
        assert entry.variables == []
        assert entry.model is None

    def test_full(self) -> None:
        entry = PromptEntry(
            file=Path("prompts/greet.yaml"),
            name="greet",
            description="Greet the user",
            variables=["name", "lang"],
            model="gpt-4o",
        )
        assert entry.variables == ["name", "lang"]
        assert entry.model == "gpt-4o"

    def test_serialization_roundtrip(self) -> None:
        entry = PromptEntry(
            file=Path("test.yaml"), name="test", variables=["x"]
        )
        data = entry.model_dump(mode="json")
        restored = PromptEntry(**data)
        assert restored.name == entry.name
        assert restored.variables == entry.variables


class TestQualityConfig:
    """Tests for the QualityConfig model."""

    def test_defaults(self) -> None:
        config = QualityConfig()
        assert config.lint == "optional"
        assert config.test == "optional"
        assert config.format == "optional"

    def test_custom(self) -> None:
        config = QualityConfig(lint="required", test="skip", format="required")
        assert config.lint == "required"
        assert config.test == "skip"


class TestPackageManifest:
    """Tests for the PackageManifest model."""

    def test_minimal(self) -> None:
        manifest = PackageManifest(
            name="@org/pkg",
            version="1.0.0",
            description="A package",
            author="Author",
        )
        assert manifest.name == "@org/pkg"
        assert manifest.prompts == []
        assert manifest.dependencies == {}
        assert manifest.quality.lint == "optional"

    def test_with_prompts_and_deps(self) -> None:
        manifest = PackageManifest(
            name="@org/pkg",
            version="2.1.0",
            description="Full package",
            author="Author",
            prompts=[
                PromptEntry(file=Path("a.yaml"), name="a"),
            ],
            dependencies={"@org/base": "^1.0.0"},
        )
        assert len(manifest.prompts) == 1
        assert "@org/base" in manifest.dependencies

    def test_roundtrip(self) -> None:
        manifest = PackageManifest(
            name="@scope/test",
            version="0.1.0",
            description="test",
            author="me",
            license="MIT",
            model="gpt-4o",
            prompts=[PromptEntry(file=Path("x.yaml"), name="x")],
            dependencies={"@scope/dep": ">=1.0"},
            quality=QualityConfig(lint="required"),
        )
        data = manifest.model_dump(mode="json")
        restored = PackageManifest(**data)
        assert restored.name == manifest.name
        assert restored.dependencies == manifest.dependencies
        assert restored.quality.lint == "required"


class TestCatalogEntry:
    """Tests for the CatalogEntry model."""

    def test_creation(self) -> None:
        entry = CatalogEntry(
            name="@org/pkg",
            latest_version="1.0.0",
            versions=["0.1.0", "1.0.0"],
            description="Test",
            total_prompts=3,
            published_at="2025-01-01T00:00:00+00:00",
            integrity="abc123",
        )
        assert entry.latest_version == "1.0.0"
        assert len(entry.versions) == 2
        assert entry.model is None


class TestLockEntry:
    """Tests for the LockEntry model."""

    def test_creation(self) -> None:
        entry = LockEntry(
            version="1.0.0",
            integrity="sha256hash",
            resolved="/home/user/.promptvault/registry/packages/@org/pkg/1.0.0",
        )
        assert entry.version == "1.0.0"


class TestLockfile:
    """Tests for the Lockfile model."""

    def test_empty(self) -> None:
        lockfile = Lockfile()
        assert lockfile.lockfile_version == 1
        assert lockfile.resolved == {}

    def test_with_entries(self) -> None:
        lockfile = Lockfile(
            resolved={
                "@org/pkg": LockEntry(
                    version="1.0.0",
                    integrity="hash",
                    resolved="/path/to/pkg",
                )
            }
        )
        assert "@org/pkg" in lockfile.resolved
        assert lockfile.resolved["@org/pkg"].version == "1.0.0"


class TestValidationRejection:
    """Tests that models reject missing required fields."""

    def test_prompt_entry_missing_file(self) -> None:
        with pytest.raises(Exception):
            PromptEntry(name="hello")  # type: ignore[call-arg]

    def test_prompt_entry_missing_name(self) -> None:
        with pytest.raises(Exception):
            PromptEntry(file=Path("hello.yaml"))  # type: ignore[call-arg]

    def test_package_manifest_missing_name(self) -> None:
        with pytest.raises(Exception):
            PackageManifest(  # type: ignore[call-arg]
                version="1.0.0", description="d", author="a"
            )

    def test_package_manifest_missing_version(self) -> None:
        with pytest.raises(Exception):
            PackageManifest(  # type: ignore[call-arg]
                name="@org/pkg", description="d", author="a"
            )

    def test_package_manifest_missing_description(self) -> None:
        with pytest.raises(Exception):
            PackageManifest(  # type: ignore[call-arg]
                name="@org/pkg", version="1.0.0", author="a"
            )

    def test_package_manifest_missing_author(self) -> None:
        with pytest.raises(Exception):
            PackageManifest(  # type: ignore[call-arg]
                name="@org/pkg", version="1.0.0", description="d"
            )

    def test_catalog_entry_missing_required(self) -> None:
        with pytest.raises(Exception):
            CatalogEntry(  # type: ignore[call-arg]
                name="@org/pkg",
                # missing latest_version, published_at, integrity
            )

    def test_catalog_entry_model_defaults_none(self) -> None:
        entry = CatalogEntry(
            name="@org/pkg",
            latest_version="1.0.0",
            published_at="2025-01-01T00:00:00+00:00",
            integrity="abc123",
        )
        assert entry.model is None
        assert entry.total_prompts == 0
