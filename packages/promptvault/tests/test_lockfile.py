"""Tests for promptvault lockfile management."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from promptvault.lockfile import (
    generate_lockfile,
    read_lockfile,
    verify_lockfile,
    write_lockfile,
)
from promptvault.models import LockEntry, Lockfile, PackageManifest
from promptvault.registry import LocalRegistry


def _publish_package(
    registry: LocalRegistry,
    tmp_path: Path,
    name: str,
    version: str,
) -> None:
    """Publish a minimal package to the registry."""
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


class TestGenerateLockfile:
    """Tests for lockfile generation."""

    def test_generate_empty(self, tmp_path: Path) -> None:
        reg = LocalRegistry(registry_dir=tmp_path / "reg")
        manifest = PackageManifest(
            name="@test/app",
            version="1.0.0",
            description="App",
            author="Test",
        )
        lockfile = generate_lockfile(manifest, {}, reg)
        assert lockfile.lockfile_version == 1
        assert lockfile.resolved == {}

    def test_generate_with_deps(self, tmp_path: Path) -> None:
        reg = LocalRegistry(registry_dir=tmp_path / "reg")
        _publish_package(reg, tmp_path, "@test/base", "1.0.0")

        manifest = PackageManifest(
            name="@test/app",
            version="1.0.0",
            description="App",
            author="Test",
        )
        resolved = {"@test/base": "1.0.0"}
        lockfile = generate_lockfile(manifest, resolved, reg)

        assert "@test/base" in lockfile.resolved
        entry = lockfile.resolved["@test/base"]
        assert entry.version == "1.0.0"
        assert entry.integrity  # non-empty
        assert entry.resolved  # non-empty path


class TestWriteAndReadLockfile:
    """Tests for lockfile I/O."""

    def test_write_read_roundtrip(self, tmp_path: Path) -> None:
        lockfile = Lockfile(
            lockfile_version=1,
            resolved={
                "@test/pkg": LockEntry(
                    version="1.0.0",
                    integrity="abc123",
                    resolved="/path/to/pkg",
                )
            },
        )
        lockfile_path = tmp_path / "promptvault.lock"
        write_lockfile(lockfile, lockfile_path)

        restored = read_lockfile(lockfile_path)
        assert restored.lockfile_version == 1
        assert "@test/pkg" in restored.resolved
        assert restored.resolved["@test/pkg"].version == "1.0.0"
        assert restored.resolved["@test/pkg"].integrity == "abc123"

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        lockfile = Lockfile()
        lockfile_path = tmp_path / "nested" / "dir" / "promptvault.lock"
        write_lockfile(lockfile, lockfile_path)
        assert lockfile_path.exists()

    def test_read_missing_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Lockfile not found"):
            read_lockfile(tmp_path / "nonexistent.lock")

    def test_write_empty_lockfile(self, tmp_path: Path) -> None:
        lockfile = Lockfile()
        lockfile_path = tmp_path / "promptvault.lock"
        write_lockfile(lockfile, lockfile_path)
        restored = read_lockfile(lockfile_path)
        assert restored.resolved == {}


class TestVerifyLockfile:
    """Tests for lockfile verification."""

    def test_verify_valid(self, tmp_path: Path) -> None:
        reg = LocalRegistry(registry_dir=tmp_path / "reg")
        _publish_package(reg, tmp_path, "@test/lib", "1.0.0")

        manifest = PackageManifest(
            name="@test/app",
            version="1.0.0",
            description="App",
            author="Test",
        )
        resolved = {"@test/lib": "1.0.0"}
        lockfile = generate_lockfile(manifest, resolved, reg)

        assert verify_lockfile(lockfile, reg) is True

    def test_verify_missing_package(self, tmp_path: Path) -> None:
        reg = LocalRegistry(registry_dir=tmp_path / "reg")
        lockfile = Lockfile(
            resolved={
                "@test/gone": LockEntry(
                    version="1.0.0",
                    integrity="hash",
                    resolved="/nonexistent",
                )
            }
        )
        assert verify_lockfile(lockfile, reg) is False

    def test_verify_tampered_integrity(self, tmp_path: Path) -> None:
        reg = LocalRegistry(registry_dir=tmp_path / "reg")
        _publish_package(reg, tmp_path, "@test/lib", "1.0.0")

        manifest = PackageManifest(
            name="@test/app",
            version="1.0.0",
            description="App",
            author="Test",
        )
        resolved = {"@test/lib": "1.0.0"}
        lockfile = generate_lockfile(manifest, resolved, reg)

        # Tamper with the integrity
        lockfile.resolved["@test/lib"].integrity = "tampered_hash"
        assert verify_lockfile(lockfile, reg) is False

    def test_verify_empty_lockfile(self, tmp_path: Path) -> None:
        reg = LocalRegistry(registry_dir=tmp_path / "reg")
        lockfile = Lockfile()
        assert verify_lockfile(lockfile, reg) is True
