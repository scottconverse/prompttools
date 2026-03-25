"""Tests for promptvault local registry."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from promptvault.models import PackageManifest, PromptEntry
from promptvault.registry import LocalRegistry


class TestLocalRegistryInit:
    """Tests for registry initialization."""

    def test_creates_directories(self, tmp_path: Path) -> None:
        reg_dir = tmp_path / "new-registry"
        reg = LocalRegistry(registry_dir=reg_dir)
        assert reg.registry_dir.exists()
        assert reg.packages_dir.exists()

    def test_default_paths(self, tmp_path: Path) -> None:
        reg = LocalRegistry(registry_dir=tmp_path / "reg")
        assert reg.index_path == reg.registry_dir / "index.json"


class TestPublish:
    """Tests for publishing packages."""

    def test_publish_creates_entry(
        self, registry: LocalRegistry, manifest_dir: Path
    ) -> None:
        entry = registry.publish(manifest_dir)
        assert entry.name == "@test/greeting-prompts"
        assert entry.latest_version == "1.0.0"
        assert entry.total_prompts == 2
        assert entry.integrity  # non-empty hash

    def test_publish_copies_files(
        self, registry: LocalRegistry, manifest_dir: Path
    ) -> None:
        registry.publish(manifest_dir)
        pkg_dir = registry.packages_dir / "@test/greeting-prompts" / "1.0.0"
        assert (pkg_dir / "promptvault.yaml").exists()
        assert (pkg_dir / "prompts" / "hello.yaml").exists()
        assert (pkg_dir / "prompts" / "farewell.yaml").exists()

    def test_publish_updates_index(
        self, registry: LocalRegistry, manifest_dir: Path
    ) -> None:
        registry.publish(manifest_dir)
        assert registry.index_path.exists()
        packages = registry.list_packages()
        assert len(packages) == 1
        assert packages[0].name == "@test/greeting-prompts"

    def test_publish_duplicate_version_raises(
        self, registry: LocalRegistry, manifest_dir: Path
    ) -> None:
        registry.publish(manifest_dir)
        with pytest.raises(ValueError, match="already exists"):
            registry.publish(manifest_dir)

    def test_publish_missing_manifest_raises(
        self, registry: LocalRegistry, tmp_path: Path
    ) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="No promptvault.yaml"):
            registry.publish(empty_dir)

    def test_publish_multiple_versions(
        self, registry: LocalRegistry, tmp_path: Path
    ) -> None:
        """Publish two versions of the same package."""
        for ver in ("1.0.0", "1.1.0"):
            pkg_dir = tmp_path / f"pkg-{ver}"
            pkg_dir.mkdir()
            manifest_data = {
                "name": "@test/multi",
                "version": ver,
                "description": f"Version {ver}",
                "author": "Tester",
                "prompts": [],
            }
            (pkg_dir / "promptvault.yaml").write_text(
                yaml.dump(manifest_data), encoding="utf-8"
            )
            registry.publish(pkg_dir)

        entry = registry.info("@test/multi")
        assert entry.latest_version == "1.1.0"
        assert set(entry.versions) == {"1.0.0", "1.1.0"}


class TestSearch:
    """Tests for searching the catalog."""

    def test_search_by_name(
        self, populated_registry: LocalRegistry
    ) -> None:
        results = populated_registry.search("greeting")
        assert len(results) == 1
        assert results[0].name == "@test/greeting-prompts"

    def test_search_by_description(
        self, populated_registry: LocalRegistry
    ) -> None:
        results = populated_registry.search("collection")
        assert len(results) == 1

    def test_search_case_insensitive(
        self, populated_registry: LocalRegistry
    ) -> None:
        results = populated_registry.search("GREETING")
        assert len(results) == 1

    def test_search_no_results(
        self, populated_registry: LocalRegistry
    ) -> None:
        results = populated_registry.search("nonexistent")
        assert results == []


class TestInfo:
    """Tests for package info lookup."""

    def test_info_returns_entry(
        self, populated_registry: LocalRegistry
    ) -> None:
        entry = populated_registry.info("@test/greeting-prompts")
        assert entry.name == "@test/greeting-prompts"
        assert entry.latest_version == "1.0.0"

    def test_info_missing_raises(
        self, populated_registry: LocalRegistry
    ) -> None:
        with pytest.raises(KeyError, match="not found"):
            populated_registry.info("@test/nonexistent")


class TestListPackages:
    """Tests for listing all packages."""

    def test_list_empty_registry(self, registry: LocalRegistry) -> None:
        packages = registry.list_packages()
        assert packages == []

    def test_list_populated(
        self, populated_registry: LocalRegistry
    ) -> None:
        packages = populated_registry.list_packages()
        assert len(packages) == 1


class TestGetVersions:
    """Tests for getting version lists."""

    def test_get_versions(
        self, populated_registry: LocalRegistry
    ) -> None:
        versions = populated_registry.get_versions("@test/greeting-prompts")
        assert "1.0.0" in versions

    def test_get_versions_missing_raises(
        self, populated_registry: LocalRegistry
    ) -> None:
        with pytest.raises(KeyError):
            populated_registry.get_versions("@test/nope")


class TestGetPackageDir:
    """Tests for package directory lookup."""

    def test_get_package_dir(
        self, populated_registry: LocalRegistry
    ) -> None:
        pkg_dir = populated_registry.get_package_dir(
            "@test/greeting-prompts", "1.0.0"
        )
        assert pkg_dir.exists()
        assert (pkg_dir / "promptvault.yaml").exists()

    def test_get_package_dir_missing_raises(
        self, populated_registry: LocalRegistry
    ) -> None:
        with pytest.raises(FileNotFoundError):
            populated_registry.get_package_dir("@test/greeting-prompts", "9.9.9")
