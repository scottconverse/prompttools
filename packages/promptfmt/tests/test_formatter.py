"""Tests for promptfmt.formatter."""

import pytest
from pathlib import Path

from promptfmt.formatter import FmtConfig, format_file, format_content
from prompttools_core import PromptFormat


class TestFormatContent:
    def test_normalizes_whitespace(self):
        messy = "hello   \r\n\r\n\r\n\r\nworld  \n"
        result = format_content(messy, PromptFormat.TEXT, FmtConfig())
        assert "   " not in result
        assert "\r" not in result

    def test_normalizes_variables(self):
        mixed = "Hello {name} and <role>"
        result = format_content(mixed, PromptFormat.TEXT, FmtConfig())
        assert "{{name}}" in result
        assert "{{role}}" in result

    def test_custom_variable_style(self):
        content = "Hello {{name}}"
        config = FmtConfig(variable_style="angle_bracket")
        result = format_content(content, PromptFormat.TEXT, config)
        assert "<name>" in result

    def test_line_wrapping_disabled(self):
        long_line = "x " * 200
        config = FmtConfig(max_line_length=0)
        result = format_content(long_line, PromptFormat.TEXT, config)
        # Should not wrap when disabled
        lines = result.strip().split("\n")
        assert len(lines) == 1

    def test_idempotent(self):
        content = "Hello {{name}}, you are a {{role}}.\n"
        config = FmtConfig()
        once = format_content(content, PromptFormat.TEXT, config)
        twice = format_content(once, PromptFormat.TEXT, config)
        assert once == twice


class TestFormatFile:
    def test_formats_txt_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello   \nworld  \n", encoding="utf-8")
        result = format_file(f)
        assert result.changed
        assert result.equivalent

    def test_unchanged_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello\n", encoding="utf-8")
        result = format_file(f)
        assert not result.changed

    def test_yaml_file(self, tmp_path):
        content = "messages:\n  - role: user\n    content: hello {{name}}   \n"
        f = tmp_path / "test.yaml"
        f.write_text(content, encoding="utf-8")
        result = format_file(f)
        assert result.equivalent

    def test_variable_syntax_change_detected(self, tmp_path):
        """Variable syntax normalization changes content — equivalence check catches it."""
        content = "messages:\n  - role: user\n    content: Tell me about {topic}\n"
        f = tmp_path / "test.yaml"
        f.write_text(content, encoding="utf-8")
        result = format_file(f)
        # Content changes because {topic} -> {{topic}}
        assert result.changed
        assert "{{topic}}" in result.formatted_content

    def test_already_normalized_is_equivalent(self, tmp_path):
        """If variables are already in target style, equivalence is preserved."""
        content = "messages:\n  - role: user\n    content: Tell me about {{topic}}\n"
        f = tmp_path / "test.yaml"
        f.write_text(content, encoding="utf-8")
        result = format_file(f)
        # May still change due to YAML reformatting, but content semantics preserved
        if result.changed:
            assert result.equivalent
