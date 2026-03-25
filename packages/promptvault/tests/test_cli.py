"""Tests for promptvault CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from promptvault.cli import app
from promptvault.registry import LocalRegistry

runner = CliRunner()


def _create_manifest_dir(
    tmp_path: Path,
    name: str = "@test/cli-pkg",
    version: str = "1.0.0",
) -> Path:
    """Create a package directory with a manifest and prompt files."""
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir(exist_ok=True)
    prompts_dir = pkg_dir / "prompts"
    prompts_dir.mkdir(exist_ok=True)

    manifest_data = {
        "name": name,
        "version": version,
        "description": "CLI test package",
        "author": "Tester",
        "prompts": [
            {"file": "prompts/hello.yaml", "name": "hello", "description": "Say hello"},
        ],
        "dependencies": {},
    }
    (pkg_dir / "promptvault.yaml").write_text(
        yaml.dump(manifest_data, default_flow_style=False), encoding="utf-8"
    )
    (prompts_dir / "hello.yaml").write_text(
        "messages:\n  - role: user\n    content: Hello\n", encoding="utf-8"
    )
    return pkg_dir


class TestInit:
    """Tests for the init command."""

    def test_init_creates_manifest(self, tmp_path: Path) -> None:
        target = tmp_path / "new-project"
        target.mkdir()
        result = runner.invoke(
            app,
            ["init", str(target), "--name", "@my/prompts", "--author", "Me"],
        )
        assert result.exit_code == 0
        assert (target / "promptvault.yaml").exists()

    def test_init_existing_manifest_fails(self, tmp_path: Path) -> None:
        (tmp_path / "promptvault.yaml").write_text("name: existing\n")
        result = runner.invoke(app, ["init", str(tmp_path)])
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_init_default_values(self, tmp_path: Path) -> None:
        target = tmp_path / "init-test"
        target.mkdir()
        result = runner.invoke(app, ["init", str(target)])
        assert result.exit_code == 0
        data = yaml.safe_load(
            (target / "promptvault.yaml").read_text(encoding="utf-8")
        )
        assert data["version"] == "0.1.0"
        assert data["quality"]["lint"] == "optional"


class TestPublish:
    """Tests for the publish command."""

    def test_publish_text_output(self, tmp_path: Path) -> None:
        pkg_dir = _create_manifest_dir(tmp_path)
        reg_dir = tmp_path / "registry"
        result = runner.invoke(
            app, ["publish", str(pkg_dir), "--registry", str(reg_dir)]
        )
        assert result.exit_code == 0
        assert "Published" in result.output
        assert "@test/cli-pkg" in result.output

    def test_publish_json_output(self, tmp_path: Path) -> None:
        pkg_dir = _create_manifest_dir(tmp_path)
        reg_dir = tmp_path / "registry"
        result = runner.invoke(
            app,
            ["publish", str(pkg_dir), "--registry", str(reg_dir), "--format", "json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["name"] == "@test/cli-pkg"

    def test_publish_missing_manifest(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        reg_dir = tmp_path / "registry"
        result = runner.invoke(
            app, ["publish", str(empty_dir), "--registry", str(reg_dir)]
        )
        assert result.exit_code == 1


class TestSearch:
    """Tests for the search command."""

    def test_search_finds_package(self, tmp_path: Path) -> None:
        reg_dir = tmp_path / "registry"
        pkg_dir = _create_manifest_dir(tmp_path)
        runner.invoke(
            app, ["publish", str(pkg_dir), "--registry", str(reg_dir)]
        )
        result = runner.invoke(
            app, ["search", "cli", "--registry", str(reg_dir)]
        )
        assert result.exit_code == 0
        assert "@test/cli-pkg" in result.output

    def test_search_no_results(self, tmp_path: Path) -> None:
        reg_dir = tmp_path / "registry"
        reg_dir.mkdir(parents=True)
        result = runner.invoke(
            app, ["search", "nonexistent", "--registry", str(reg_dir)]
        )
        assert result.exit_code == 0
        assert "No packages" in result.output

    def test_search_json_output(self, tmp_path: Path) -> None:
        reg_dir = tmp_path / "registry"
        pkg_dir = _create_manifest_dir(tmp_path)
        runner.invoke(
            app, ["publish", str(pkg_dir), "--registry", str(reg_dir)]
        )
        result = runner.invoke(
            app, ["search", "cli", "--registry", str(reg_dir), "--format", "json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1


class TestInfo:
    """Tests for the info command."""

    def test_info_shows_details(self, tmp_path: Path) -> None:
        reg_dir = tmp_path / "registry"
        pkg_dir = _create_manifest_dir(tmp_path)
        runner.invoke(
            app, ["publish", str(pkg_dir), "--registry", str(reg_dir)]
        )
        result = runner.invoke(
            app, ["info", "@test/cli-pkg", "--registry", str(reg_dir)]
        )
        assert result.exit_code == 0
        assert "@test/cli-pkg" in result.output
        assert "1.0.0" in result.output

    def test_info_missing_package(self, tmp_path: Path) -> None:
        reg_dir = tmp_path / "registry"
        reg_dir.mkdir(parents=True)
        result = runner.invoke(
            app, ["info", "@test/nope", "--registry", str(reg_dir)]
        )
        assert result.exit_code == 1
        assert "not found" in result.output


class TestList:
    """Tests for the list command."""

    def test_list_empty(self, tmp_path: Path) -> None:
        reg_dir = tmp_path / "registry"
        reg_dir.mkdir(parents=True)
        result = runner.invoke(
            app, ["list", "--registry", str(reg_dir)]
        )
        assert result.exit_code == 0
        assert "No packages" in result.output

    def test_list_with_packages(self, tmp_path: Path) -> None:
        reg_dir = tmp_path / "registry"
        pkg_dir = _create_manifest_dir(tmp_path)
        runner.invoke(
            app, ["publish", str(pkg_dir), "--registry", str(reg_dir)]
        )
        result = runner.invoke(
            app, ["list", "--registry", str(reg_dir)]
        )
        assert result.exit_code == 0
        assert "@test/cli-pkg" in result.output


class TestInstall:
    """Tests for the install command."""

    def test_install_no_deps(self, tmp_path: Path) -> None:
        pkg_dir = _create_manifest_dir(tmp_path)
        reg_dir = tmp_path / "registry"
        result = runner.invoke(
            app, ["install", str(pkg_dir), "--registry", str(reg_dir)]
        )
        assert result.exit_code == 0
        assert "No dependencies" in result.output

    def test_install_with_deps(self, tmp_path: Path) -> None:
        reg_dir = tmp_path / "registry"

        # Publish a dependency
        dep_dir = tmp_path / "dep"
        dep_dir.mkdir()
        dep_manifest = {
            "name": "@test/dep",
            "version": "1.0.0",
            "description": "A dependency",
            "author": "Test",
            "prompts": [],
        }
        (dep_dir / "promptvault.yaml").write_text(
            yaml.dump(dep_manifest), encoding="utf-8"
        )
        runner.invoke(
            app, ["publish", str(dep_dir), "--registry", str(reg_dir)]
        )

        # Create a package that depends on it
        pkg_dir = tmp_path / "app"
        pkg_dir.mkdir()
        app_manifest = {
            "name": "@test/app",
            "version": "1.0.0",
            "description": "An app",
            "author": "Test",
            "prompts": [],
            "dependencies": {"@test/dep": "^1.0.0"},
        }
        (pkg_dir / "promptvault.yaml").write_text(
            yaml.dump(app_manifest), encoding="utf-8"
        )

        result = runner.invoke(
            app, ["install", str(pkg_dir), "--registry", str(reg_dir)]
        )
        assert result.exit_code == 0
        assert "Installed 1 dependencies" in result.output
        assert (pkg_dir / "promptvault.lock").exists()


class TestVerify:
    """Tests for the verify command."""

    def test_verify_no_lockfile(self, tmp_path: Path) -> None:
        reg_dir = tmp_path / "registry"
        reg_dir.mkdir(parents=True)
        result = runner.invoke(
            app, ["verify", str(tmp_path), "--registry", str(reg_dir)]
        )
        assert result.exit_code == 1
        assert "No promptvault.lock" in result.output

    def test_verify_valid_lockfile(self, tmp_path: Path) -> None:
        reg_dir = tmp_path / "registry"

        # Publish dep, install, then verify
        dep_dir = tmp_path / "dep"
        dep_dir.mkdir()
        dep_manifest = {
            "name": "@test/dep",
            "version": "1.0.0",
            "description": "Dep",
            "author": "Test",
            "prompts": [],
        }
        (dep_dir / "promptvault.yaml").write_text(
            yaml.dump(dep_manifest), encoding="utf-8"
        )
        runner.invoke(
            app, ["publish", str(dep_dir), "--registry", str(reg_dir)]
        )

        pkg_dir = tmp_path / "app"
        pkg_dir.mkdir()
        app_manifest = {
            "name": "@test/app",
            "version": "1.0.0",
            "description": "App",
            "author": "Test",
            "prompts": [],
            "dependencies": {"@test/dep": "^1.0.0"},
        }
        (pkg_dir / "promptvault.yaml").write_text(
            yaml.dump(app_manifest), encoding="utf-8"
        )

        runner.invoke(
            app, ["install", str(pkg_dir), "--registry", str(reg_dir)]
        )

        result = runner.invoke(
            app, ["verify", str(pkg_dir), "--registry", str(reg_dir)]
        )
        assert result.exit_code == 0
        assert "passed" in result.output
