"""Lockfile generation and verification for promptvault.

Provides reproducible dependency resolution by writing and reading
lockfiles that pin exact versions and integrity hashes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from promptvault.models import LockEntry, Lockfile
from promptvault.registry import _compute_integrity

if TYPE_CHECKING:
    from promptvault.models import PackageManifest
    from promptvault.registry import LocalRegistry


def generate_lockfile(
    manifest: "PackageManifest",
    resolved: dict[str, str],
    registry: "LocalRegistry",
) -> Lockfile:
    """Generate a lockfile from resolved dependency versions.

    Args:
        manifest: The package manifest (used for context).
        resolved: Mapping of dependency name to exact version.
        registry: The local registry (used to compute paths and integrity).

    Returns:
        A Lockfile with all resolved entries.
    """
    entries: dict[str, LockEntry] = {}

    for dep_name, dep_version in resolved.items():
        pkg_dir = registry.get_package_dir(dep_name, dep_version)
        integrity = _compute_integrity(pkg_dir)
        entries[dep_name] = LockEntry(
            version=dep_version,
            integrity=integrity,
            resolved=pkg_dir.as_posix(),
        )

    return Lockfile(lockfile_version=1, resolved=entries)


def write_lockfile(lockfile: Lockfile, path: Path) -> None:
    """Write a lockfile to disk as JSON.

    Args:
        lockfile: The Lockfile to serialize.
        path: Destination file path.
    """
    data = lockfile.model_dump()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True), encoding="utf-8"
    )


def read_lockfile(path: Path) -> Lockfile:
    """Read a lockfile from disk.

    Args:
        path: Path to the lockfile.

    Returns:
        Parsed Lockfile.

    Raises:
        FileNotFoundError: If the lockfile does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"Lockfile not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return Lockfile(**data)


def verify_lockfile(lockfile: Lockfile, registry: "LocalRegistry") -> bool:
    """Verify that all lockfile entries are still valid.

    Checks that each resolved package still exists in the registry and
    that its integrity hash matches.

    Args:
        lockfile: The lockfile to verify.
        registry: The local registry to check against.

    Returns:
        True if all entries are valid, False otherwise.
    """
    for dep_name, entry in lockfile.resolved.items():
        try:
            pkg_dir = registry.get_package_dir(dep_name, entry.version)
        except FileNotFoundError:
            return False

        current_integrity = _compute_integrity(pkg_dir)
        if current_integrity != entry.integrity:
            return False

    return True
