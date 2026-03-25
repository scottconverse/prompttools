"""Dependency resolution with semver support.

Resolves package dependencies to exact versions using the local registry.
Supports standard semver range specifiers via the ``packaging`` library.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.specifiers import SpecifierSet
from packaging.version import Version

if TYPE_CHECKING:
    from promptvault.models import PackageManifest
    from promptvault.registry import LocalRegistry


class DependencyConflictError(Exception):
    """Raised when dependency versions cannot be resolved."""


def _parse_version_range(range_str: str) -> SpecifierSet:
    """Convert a version range string to a packaging SpecifierSet.

    Supports:
        - Exact: ``1.2.3`` -> ``==1.2.3``
        - Caret: ``^1.2.3`` -> ``>=1.2.3,<2.0.0``
        - Tilde: ``~1.2.3`` -> ``>=1.2.3,<1.3.0``
        - Standard PEP 440: ``>=1.0,<2.0``
    """
    range_str = range_str.strip()

    if range_str.startswith("^"):
        base = range_str[1:]
        ver = Version(base)
        if ver.major > 0:
            upper = f"{ver.major + 1}.0.0"
        elif ver.minor > 0:
            upper = f"0.{ver.minor + 1}.0"
        else:
            upper = f"0.0.{ver.micro + 1}"
        return SpecifierSet(f">={base},<{upper}")

    if range_str.startswith("~"):
        base = range_str[1:]
        ver = Version(base)
        upper = f"{ver.major}.{ver.minor + 1}.0"
        return SpecifierSet(f">={base},<{upper}")

    # Check if it looks like a bare version number (no operators)
    if range_str and range_str[0].isdigit():
        try:
            Version(range_str)
            return SpecifierSet(f"=={range_str}")
        except Exception:
            pass

    # Standard PEP 440 specifier
    return SpecifierSet(range_str)


def _find_best_match(
    versions: list[str], spec: SpecifierSet
) -> str | None:
    """Find the highest version matching a specifier set.

    Args:
        versions: Available version strings.
        spec: The version specifier set to match against.

    Returns:
        The highest matching version string, or None if no match.
    """
    matching = []
    for v_str in versions:
        try:
            v = Version(v_str)
        except Exception:
            continue
        if v in spec:
            matching.append((v, v_str))

    if not matching:
        return None
    matching.sort(key=lambda x: x[0])
    return matching[-1][1]


def resolve_dependencies(
    manifest: "PackageManifest",
    registry: "LocalRegistry",
) -> dict[str, str]:
    """Resolve all dependencies in a manifest to exact versions.

    Uses a simple flat resolution strategy: for each dependency, find the
    highest version in the registry that satisfies the version range.

    Args:
        manifest: The package manifest with dependency declarations.
        registry: The local registry to search for packages.

    Returns:
        Mapping of dependency name to resolved exact version.

    Raises:
        DependencyConflictError: If a dependency cannot be satisfied.
    """
    resolved: dict[str, str] = {}

    for dep_name, range_str in manifest.dependencies.items():
        spec = _parse_version_range(range_str)

        try:
            available_versions = registry.get_versions(dep_name)
        except KeyError:
            raise DependencyConflictError(
                f"Dependency '{dep_name}' not found in registry"
            )

        best = _find_best_match(available_versions, spec)
        if best is None:
            raise DependencyConflictError(
                f"No version of '{dep_name}' satisfies {spec}. "
                f"Available: {available_versions}"
            )

        resolved[dep_name] = best

    return resolved
