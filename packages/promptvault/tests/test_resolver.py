"""Tests for promptvault dependency resolver."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from promptvault.models import PackageManifest, PromptEntry
from promptvault.registry import LocalRegistry
from promptvault.resolver import (
    DependencyConflictError,
    _find_best_match,
    _parse_version_range,
    resolve_dependencies,
)


class TestParseVersionRange:
    """Tests for version range parsing."""

    def test_exact_version(self) -> None:
        spec = _parse_version_range("1.2.3")
        assert "1.2.3" in spec
        assert "1.2.4" not in spec

    def test_caret_major(self) -> None:
        spec = _parse_version_range("^1.2.3")
        assert "1.2.3" in spec
        assert "1.9.0" in spec
        assert "2.0.0" not in spec

    def test_caret_minor(self) -> None:
        spec = _parse_version_range("^0.2.3")
        assert "0.2.3" in spec
        assert "0.2.9" in spec
        assert "0.3.0" not in spec

    def test_caret_patch(self) -> None:
        spec = _parse_version_range("^0.0.3")
        assert "0.0.3" in spec
        assert "0.0.4" not in spec

    def test_tilde(self) -> None:
        spec = _parse_version_range("~1.2.3")
        assert "1.2.3" in spec
        assert "1.2.9" in spec
        assert "1.3.0" not in spec

    def test_pep440_range(self) -> None:
        spec = _parse_version_range(">=1.0,<2.0")
        assert "1.0.0" in spec
        assert "1.5.0" in spec
        assert "2.0.0" not in spec

    def test_gte(self) -> None:
        spec = _parse_version_range(">=1.0.0")
        assert "1.0.0" in spec
        assert "2.0.0" in spec
        assert "0.9.0" not in spec


class TestFindBestMatch:
    """Tests for finding the best matching version."""

    def test_finds_highest(self) -> None:
        spec = _parse_version_range("^1.0.0")
        versions = ["1.0.0", "1.1.0", "1.2.0", "2.0.0"]
        best = _find_best_match(versions, spec)
        assert best == "1.2.0"

    def test_no_match(self) -> None:
        spec = _parse_version_range("^3.0.0")
        versions = ["1.0.0", "2.0.0"]
        best = _find_best_match(versions, spec)
        assert best is None

    def test_exact_match(self) -> None:
        spec = _parse_version_range("1.0.0")
        versions = ["0.9.0", "1.0.0", "1.1.0"]
        best = _find_best_match(versions, spec)
        assert best == "1.0.0"

    def test_single_version(self) -> None:
        spec = _parse_version_range(">=1.0.0")
        versions = ["1.5.0"]
        best = _find_best_match(versions, spec)
        assert best == "1.5.0"


class TestResolveDependencies:
    """Tests for full dependency resolution."""

    def _publish_package(
        self,
        registry: LocalRegistry,
        tmp_path: Path,
        name: str,
        version: str,
    ) -> None:
        """Helper to publish a minimal package."""
        pkg_dir = tmp_path / f"{name.replace('/', '_')}-{version}"
        pkg_dir.mkdir(parents=True)
        manifest_data = {
            "name": name,
            "version": version,
            "description": f"{name} {version}",
            "author": "Test",
            "prompts": [],
        }
        (pkg_dir / "promptvault.yaml").write_text(
            yaml.dump(manifest_data), encoding="utf-8"
        )
        registry.publish(pkg_dir)

    def test_resolve_single_dep(self, tmp_path: Path) -> None:
        reg = LocalRegistry(registry_dir=tmp_path / "reg")
        self._publish_package(reg, tmp_path, "@test/base", "1.0.0")
        self._publish_package(reg, tmp_path, "@test/base", "1.1.0")

        manifest = PackageManifest(
            name="@test/app",
            version="1.0.0",
            description="App",
            author="Test",
            dependencies={"@test/base": "^1.0.0"},
        )

        resolved = resolve_dependencies(manifest, reg)
        assert resolved["@test/base"] == "1.1.0"

    def test_resolve_multiple_deps(self, tmp_path: Path) -> None:
        reg = LocalRegistry(registry_dir=tmp_path / "reg")
        self._publish_package(reg, tmp_path, "@test/base", "1.0.0")
        self._publish_package(reg, tmp_path, "@test/utils", "0.2.0")
        self._publish_package(reg, tmp_path, "@test/utils", "0.2.5")
        self._publish_package(reg, tmp_path, "@test/utils", "0.3.0")

        manifest = PackageManifest(
            name="@test/app",
            version="1.0.0",
            description="App",
            author="Test",
            dependencies={
                "@test/base": "^1.0.0",
                "@test/utils": "~0.2.0",
            },
        )

        resolved = resolve_dependencies(manifest, reg)
        assert resolved["@test/base"] == "1.0.0"
        assert resolved["@test/utils"] == "0.2.5"  # ~0.2.0 excludes 0.3.0

    def test_resolve_no_deps(self, tmp_path: Path) -> None:
        reg = LocalRegistry(registry_dir=tmp_path / "reg")
        manifest = PackageManifest(
            name="@test/app",
            version="1.0.0",
            description="App",
            author="Test",
            dependencies={},
        )
        resolved = resolve_dependencies(manifest, reg)
        assert resolved == {}

    def test_resolve_missing_dep_raises(self, tmp_path: Path) -> None:
        reg = LocalRegistry(registry_dir=tmp_path / "reg")
        manifest = PackageManifest(
            name="@test/app",
            version="1.0.0",
            description="App",
            author="Test",
            dependencies={"@test/missing": "^1.0.0"},
        )
        with pytest.raises(DependencyConflictError, match="not found"):
            resolve_dependencies(manifest, reg)

    def test_resolve_unsatisfiable_raises(self, tmp_path: Path) -> None:
        reg = LocalRegistry(registry_dir=tmp_path / "reg")
        self._publish_package(reg, tmp_path, "@test/old", "0.1.0")

        manifest = PackageManifest(
            name="@test/app",
            version="1.0.0",
            description="App",
            author="Test",
            dependencies={"@test/old": "^2.0.0"},
        )
        with pytest.raises(DependencyConflictError, match="No version"):
            resolve_dependencies(manifest, reg)
