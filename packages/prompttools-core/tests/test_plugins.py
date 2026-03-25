"""Tests for prompttools_core.plugins."""

from pathlib import Path

import pytest

from prompttools_core.plugins import discover_plugins, load_plugin


class _MockBase:
    """Mock base class for plugin testing."""
    pass


class TestDiscoverPlugins:
    def test_empty_dirs_returns_empty(self, tmp_path):
        empty_dir = tmp_path / "plugins"
        empty_dir.mkdir()
        result = discover_plugins([empty_dir], _MockBase)
        assert result == []

    def test_nonexistent_dir_returns_empty(self, tmp_path):
        result = discover_plugins([tmp_path / "nonexistent"], _MockBase)
        assert result == []

    def test_discovers_subclass(self, tmp_path):
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()

        # Write a plugin file that defines a subclass of _MockBase.
        # Since _MockBase is defined in this test module, we need to
        # import it by path. Instead, define an independent base + subclass
        # in the plugin file itself.
        plugin_file = plugin_dir / "my_plugin.py"
        plugin_file.write_text(
            "class MyPlugin:\n    pass\n",
            encoding="utf-8",
        )

        # Use a base class that MyPlugin would NOT subclass — so result is empty
        result = discover_plugins([plugin_dir], _MockBase)
        assert result == []

    def test_discovers_actual_subclass(self, tmp_path):
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()

        # Create a shared base module and register it in sys.modules
        # so both the test and the plugin file reference the same class object.
        import importlib.util
        import sys

        base_file = plugin_dir / "base_mod.py"
        base_file.write_text(
            "class PluginBase:\n    pass\n",
            encoding="utf-8",
        )

        # Load and register the base module in sys.modules
        module_name = "prompttools_test_base_mod"
        spec = importlib.util.spec_from_file_location(module_name, base_file)
        base_mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = base_mod
        spec.loader.exec_module(base_mod)

        try:
            # Create a plugin that imports the base from sys.modules
            plugin_file = plugin_dir / "my_plugin.py"
            plugin_file.write_text(
                f"import sys\n"
                f"base_mod = sys.modules['{module_name}']\n"
                f"class MyPlugin(base_mod.PluginBase):\n"
                f"    pass\n",
                encoding="utf-8",
            )

            result = discover_plugins([plugin_dir], base_mod.PluginBase)
            assert len(result) == 1
            assert result[0].__name__ == "MyPlugin"
        finally:
            sys.modules.pop(module_name, None)

    def test_skips_underscore_files(self, tmp_path):
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        (plugin_dir / "_private.py").write_text(
            "class Private:\n    pass\n",
            encoding="utf-8",
        )
        result = discover_plugins([plugin_dir], _MockBase)
        assert result == []

    def test_multiple_dirs(self, tmp_path):
        dir1 = tmp_path / "plugins1"
        dir1.mkdir()
        dir2 = tmp_path / "plugins2"
        dir2.mkdir()
        result = discover_plugins([dir1, dir2], _MockBase)
        assert result == []


class TestLoadPlugin:
    def test_non_python_file_returns_empty(self, tmp_path):
        txt_file = tmp_path / "not_python.txt"
        txt_file.write_text("hello", encoding="utf-8")
        result = load_plugin(txt_file, _MockBase)
        assert result == []

    def test_nonexistent_file_returns_empty(self, tmp_path):
        result = load_plugin(tmp_path / "nonexistent.py", _MockBase)
        assert result == []
