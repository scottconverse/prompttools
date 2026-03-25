"""Generic plugin discovery and loading for the prompttools suite.

Each tool defines its own base class (e.g. BaseRule for promptlint,
BaseFormatter for promptfmt). This module provides the shared mechanism
for finding and loading plugin classes from directories.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

from prompttools_core.errors import PluginError

logger = logging.getLogger(__name__)


def _is_subclass_of(obj: object, base_class: type) -> bool:
    """Return True if *obj* is a concrete subclass of *base_class*."""
    try:
        return (
            isinstance(obj, type)
            and issubclass(obj, base_class)
            and obj is not base_class
            and not getattr(obj, "__abstractmethods__", None)
        )
    except TypeError:
        return False


def load_plugin(path: Path, base_class: type) -> list[type]:
    """Load a single plugin module and return all matching classes.

    Parameters
    ----------
    path:
        Path to a Python file containing plugin classes.
    base_class:
        The base class that plugin classes must subclass.

    Returns
    -------
    list[type]
        Discovered plugin classes (not instantiated).
    """
    if not path.is_file() or not path.suffix == ".py":
        return []

    module_name = f"prompttools_plugin_{path.stem}"
    classes: list[type] = []

    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            logger.warning("Could not load module spec for %s", path)
            return classes

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)  # type: ignore[union-attr]

        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if _is_subclass_of(obj, base_class):
                classes.append(obj)
                logger.debug("Discovered plugin class %s from %s", obj.__name__, path)

    except Exception as exc:
        logger.exception("Failed to import plugin file %s", path)
        raise PluginError(f"Failed to load plugin {path}: {exc}") from exc
    finally:
        sys.modules.pop(module_name, None)

    return classes


def discover_plugins(
    plugin_dirs: list[Path],
    base_class: type,
) -> list[type]:
    """Find all classes that subclass *base_class* in plugin directories.

    Parameters
    ----------
    plugin_dirs:
        Directories to scan for plugin ``.py`` files.
    base_class:
        The base class that plugin classes must subclass.

    Returns
    -------
    list[type]
        All discovered plugin classes (not instantiated).
    """
    all_classes: list[type] = []
    seen_names: set[str] = set()

    for directory in plugin_dirs:
        directory = Path(directory)
        if not directory.is_dir():
            logger.warning("Plugin directory does not exist: %s", directory)
            continue

        for py_file in sorted(directory.glob("*.py")):
            if py_file.name.startswith("_"):
                continue

            try:
                classes = load_plugin(py_file, base_class)
                for cls in classes:
                    if cls.__name__ in seen_names:
                        logger.warning(
                            "Duplicate plugin class '%s' from %s. Skipping.",
                            cls.__name__,
                            py_file,
                        )
                        continue
                    seen_names.add(cls.__name__)
                    all_classes.append(cls)
            except PluginError:
                continue

    return all_classes
