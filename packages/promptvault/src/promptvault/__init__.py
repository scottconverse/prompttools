"""promptvault: Version control and registry for prompt assets.

Public API exports for convenience imports::

    from promptvault import PackageManifest, LocalRegistry, resolve_dependencies
"""

from promptvault.lockfile import (
    generate_lockfile,
    read_lockfile,
    verify_lockfile,
    write_lockfile,
)
from promptvault.models import (
    CatalogEntry,
    LockEntry,
    Lockfile,
    PackageManifest,
    PromptEntry,
    QualityConfig,
)
from promptvault.registry import LocalRegistry
from promptvault.resolver import DependencyConflictError, resolve_dependencies

__version__ = "1.0.0"

__all__ = [
    # Models
    "CatalogEntry",
    "LockEntry",
    "Lockfile",
    "PackageManifest",
    "PromptEntry",
    "QualityConfig",
    # Registry
    "LocalRegistry",
    # Resolver
    "DependencyConflictError",
    "resolve_dependencies",
    # Lockfile
    "generate_lockfile",
    "read_lockfile",
    "verify_lockfile",
    "write_lockfile",
]
