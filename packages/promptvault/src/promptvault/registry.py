"""Local registry operations for promptvault.

Handles publishing, installing, searching, and listing prompt packages
in a local file-system-based registry.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from promptvault.models import CatalogEntry, LockEntry, PackageManifest


DEFAULT_REGISTRY_DIR = Path.home() / ".promptvault" / "registry"


def _compute_integrity(directory: Path) -> str:
    """Compute a SHA-256 hash over all files in a directory (sorted, deterministic)."""
    hasher = hashlib.sha256()
    for file_path in sorted(directory.rglob("*")):
        if file_path.is_file():
            rel = file_path.relative_to(directory).as_posix()
            hasher.update(rel.encode("utf-8"))
            hasher.update(file_path.read_bytes())
    return hasher.hexdigest()


def _load_index(index_path: Path) -> dict[str, dict]:
    """Load the catalog index from disk."""
    if index_path.exists():
        return json.loads(index_path.read_text(encoding="utf-8"))
    return {}


def _save_index(index_path: Path, index: dict[str, dict]) -> None:
    """Save the catalog index to disk."""
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(index, indent=2, sort_keys=True), encoding="utf-8"
    )


def _read_manifest(manifest_dir: Path) -> PackageManifest:
    """Read a promptvault.yaml manifest from a directory."""
    manifest_path = manifest_dir / "promptvault.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"No promptvault.yaml found in {manifest_dir}"
        )
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    return PackageManifest(**data)


class LocalRegistry:
    """File-system-based local registry for prompt packages.

    The registry directory structure is::

        registry_dir/
            index.json          # catalog of all packages
            packages/
                @scope/
                    name/
                        1.0.0/  # package contents for each version
    """

    def __init__(self, registry_dir: Optional[Path] = None) -> None:
        self.registry_dir = registry_dir or DEFAULT_REGISTRY_DIR
        self.packages_dir = self.registry_dir / "packages"
        self.index_path = self.registry_dir / "index.json"
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.packages_dir.mkdir(parents=True, exist_ok=True)

    def publish(self, manifest_dir: Path) -> CatalogEntry:
        """Publish a package from a manifest directory to the local registry.

        Args:
            manifest_dir: Directory containing promptvault.yaml and prompt files.

        Returns:
            CatalogEntry for the published package.

        Raises:
            FileNotFoundError: If promptvault.yaml is missing.
            ValueError: If the version already exists in the registry.
        """
        manifest = _read_manifest(manifest_dir)

        # Determine destination in registry
        dest_dir = self.packages_dir / manifest.name / manifest.version
        if dest_dir.exists():
            raise ValueError(
                f"Version {manifest.version} of {manifest.name} already exists"
            )
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Copy package contents
        for item in manifest_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, dest_dir / item.name)
            elif item.is_dir() and item.name not in {"__pycache__", ".git"}:
                shutil.copytree(item, dest_dir / item.name)

        # Compute integrity hash
        integrity = _compute_integrity(dest_dir)

        # Update the catalog index
        index = _load_index(self.index_path)
        now = datetime.now(timezone.utc).isoformat()

        if manifest.name in index:
            entry_data = index[manifest.name]
            versions = entry_data.get("versions", [])
            if manifest.version not in versions:
                versions.append(manifest.version)
            entry_data["versions"] = versions
            entry_data["latest_version"] = manifest.version
            entry_data["description"] = manifest.description
            entry_data["model"] = manifest.model
            entry_data["total_prompts"] = len(manifest.prompts)
            entry_data["published_at"] = now
            entry_data["integrity"] = integrity
        else:
            index[manifest.name] = {
                "name": manifest.name,
                "latest_version": manifest.version,
                "versions": [manifest.version],
                "description": manifest.description,
                "model": manifest.model,
                "total_prompts": len(manifest.prompts),
                "published_at": now,
                "integrity": integrity,
            }

        _save_index(self.index_path, index)
        return CatalogEntry(**index[manifest.name])

    def install(self, manifest: PackageManifest) -> list[LockEntry]:
        """Resolve dependencies and produce lock entries for installation.

        Args:
            manifest: The package manifest with dependencies to resolve.

        Returns:
            List of LockEntry for each resolved dependency.

        Raises:
            ValueError: If a dependency cannot be found in the registry.
        """
        from promptvault.resolver import resolve_dependencies

        resolved = resolve_dependencies(manifest, self)
        lock_entries: list[LockEntry] = []

        for dep_name, dep_version in resolved.items():
            dep_dir = self.packages_dir / dep_name / dep_version
            if not dep_dir.exists():
                raise ValueError(
                    f"Resolved package {dep_name}@{dep_version} not found in registry"
                )
            integrity = _compute_integrity(dep_dir)
            lock_entries.append(
                LockEntry(
                    version=dep_version,
                    integrity=integrity,
                    resolved=dep_dir.as_posix(),
                )
            )

        return lock_entries

    def search(self, query: str) -> list[CatalogEntry]:
        """Search the catalog by name or description substring.

        Args:
            query: Case-insensitive search string.

        Returns:
            Matching CatalogEntry objects.
        """
        index = _load_index(self.index_path)
        query_lower = query.lower()
        results: list[CatalogEntry] = []
        for entry_data in index.values():
            name = entry_data.get("name", "").lower()
            desc = entry_data.get("description", "").lower()
            if query_lower in name or query_lower in desc:
                results.append(CatalogEntry(**entry_data))
        return results

    def info(self, package_name: str) -> CatalogEntry:
        """Get detailed information about a specific package.

        Args:
            package_name: Full package name (e.g. ``@scope/name``).

        Returns:
            CatalogEntry for the package.

        Raises:
            KeyError: If the package is not found.
        """
        index = _load_index(self.index_path)
        if package_name not in index:
            raise KeyError(f"Package '{package_name}' not found in registry")
        return CatalogEntry(**index[package_name])

    def list_packages(self) -> list[CatalogEntry]:
        """List all packages in the registry.

        Returns:
            List of all CatalogEntry objects.
        """
        index = _load_index(self.index_path)
        return [CatalogEntry(**data) for data in index.values()]

    def get_versions(self, package_name: str) -> list[str]:
        """Get all published versions of a package.

        Args:
            package_name: Full package name.

        Returns:
            List of version strings.

        Raises:
            KeyError: If the package is not found.
        """
        entry = self.info(package_name)
        return entry.versions

    def get_package_dir(self, package_name: str, version: str) -> Path:
        """Get the directory path for a specific package version.

        Args:
            package_name: Full package name.
            version: Exact version string.

        Returns:
            Path to the package directory.

        Raises:
            FileNotFoundError: If the version directory does not exist.
        """
        pkg_dir = self.packages_dir / package_name / version
        if not pkg_dir.exists():
            raise FileNotFoundError(
                f"Package {package_name}@{version} not found at {pkg_dir}"
            )
        return pkg_dir
