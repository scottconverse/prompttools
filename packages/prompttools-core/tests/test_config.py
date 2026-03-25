"""Tests for prompttools_core.config."""

from pathlib import Path

import pytest

from prompttools_core.config import find_config_file, load_config
from prompttools_core.models import ToolConfig


class TestLoadConfig:
    def test_returns_tool_config(self):
        config = load_config("test", start_dir=Path("/nonexistent"))
        assert isinstance(config, ToolConfig)

    def test_defaults_when_no_config_file(self, tmp_path):
        config = load_config("test", start_dir=tmp_path)
        assert config.model is None
        assert config.exclude == []
        assert config.plugins == []
        assert config.cache_enabled is False

    def test_loads_config_from_file(self, tmp_path):
        config_file = tmp_path / ".prompttools.yaml"
        config_file.write_text(
            "model: gpt-4\nexclude:\n  - '*.bak'\ncache:\n  enabled: true\n",
            encoding="utf-8",
        )
        config = load_config("test", start_dir=tmp_path)
        assert config.model == "gpt-4"
        assert config.exclude == ["*.bak"]
        assert config.cache_enabled is True

    def test_cli_overrides(self, tmp_path):
        config_file = tmp_path / ".prompttools.yaml"
        config_file.write_text("model: gpt-4\n", encoding="utf-8")
        config = load_config(
            "test",
            start_dir=tmp_path,
            cli_overrides={"model": "gpt-4o"},
        )
        assert config.model == "gpt-4o"


class TestFindConfigFile:
    def test_returns_none_when_no_config(self, tmp_path):
        result = find_config_file(tmp_path)
        assert result is None

    def test_finds_prompttools_yaml(self, tmp_path):
        config_file = tmp_path / ".prompttools.yaml"
        config_file.write_text("model: gpt-4\n", encoding="utf-8")
        result = find_config_file(tmp_path)
        assert result is not None
        assert result.name == ".prompttools.yaml"

    def test_finds_tool_specific_config(self, tmp_path):
        config_file = tmp_path / ".promptlint.yaml"
        config_file.write_text("model: gpt-4\n", encoding="utf-8")
        result = find_config_file(tmp_path, tool_name="lint")
        # .promptlint.yaml is searched as tool-specific
        assert result is not None

    def test_walks_up_directories(self, tmp_path):
        # Create config in parent, search from child
        config_file = tmp_path / ".prompttools.yaml"
        config_file.write_text("model: gpt-4\n", encoding="utf-8")
        child = tmp_path / "sub" / "dir"
        child.mkdir(parents=True)
        result = find_config_file(child)
        assert result is not None
        assert result.name == ".prompttools.yaml"

    def test_tool_specific_takes_priority(self, tmp_path):
        # Both exist - tool-specific should be found first
        (tmp_path / ".prompttools.yaml").write_text("model: gpt-4\n", encoding="utf-8")
        (tmp_path / ".promptfmt.yaml").write_text("model: gpt-4o\n", encoding="utf-8")
        result = find_config_file(tmp_path, tool_name="fmt")
        assert result is not None
        assert result.name == ".promptfmt.yaml"
