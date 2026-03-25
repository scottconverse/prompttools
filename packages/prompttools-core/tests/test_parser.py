"""Tests for prompttools_core.parser."""

from pathlib import Path

import pytest

from prompttools_core.errors import ParseError
from prompttools_core.models import PromptFormat
from prompttools_core.parser import (
    extract_variables,
    parse_directory,
    parse_file,
    parse_stdin,
)


# ---------------------------------------------------------------------------
# parse_file — YAML
# ---------------------------------------------------------------------------


class TestParseYaml:
    def test_clean_yaml(self, clean_yaml):
        pf = parse_file(clean_yaml)
        assert pf.format == PromptFormat.YAML
        assert len(pf.messages) == 2
        assert pf.messages[0].role == "system"
        assert pf.messages[1].role == "user"
        assert pf.content_hash != ""

    def test_clean_yaml_has_system_message(self, clean_yaml):
        pf = parse_file(clean_yaml)
        sys_msg = pf.system_message()
        assert sys_msg is not None
        assert "helpful assistant" in sys_msg.content

    def test_clean_yaml_variables(self, clean_yaml):
        pf = parse_file(clean_yaml)
        # clean.yaml has {{input_text}} variable
        assert "input_text" in pf.variables
        assert pf.variables["input_text"] == "jinja"

    def test_with_variables_yaml(self, with_variables):
        pf = parse_file(with_variables)
        # with_variables.yaml has {{role}}, {language}, {{input_data}}
        assert "role" in pf.variables
        assert pf.variables["role"] == "jinja"
        assert "input_data" in pf.variables
        assert pf.variables["input_data"] == "jinja"
        # {language} is fstring style
        assert "language" in pf.variables
        assert pf.variables["language"] == "fstring"

    def test_with_variables_yaml_variable_defaults(self, with_variables):
        pf = parse_file(with_variables)
        # with_variables.yaml has variables section (treated as metadata)
        # The "variables" key in YAML is in metadata, not variable_defaults
        assert pf.metadata.get("variables") is not None


# ---------------------------------------------------------------------------
# parse_file — JSON
# ---------------------------------------------------------------------------


class TestParseJson:
    def test_clean_json(self, clean_json):
        pf = parse_file(clean_json)
        assert pf.format == PromptFormat.JSON
        assert len(pf.messages) == 2
        assert pf.messages[0].role == "system"
        assert pf.messages[1].role == "user"

    def test_clean_json_content(self, clean_json):
        pf = parse_file(clean_json)
        assert "helpful assistant" in pf.messages[0].content
        assert "exercise" in pf.messages[1].content

    def test_clean_json_content_hash(self, clean_json):
        pf = parse_file(clean_json)
        assert pf.content_hash != ""
        assert len(pf.content_hash) == 64  # SHA256 hex length


# ---------------------------------------------------------------------------
# parse_file — Text
# ---------------------------------------------------------------------------


class TestParseText:
    def test_clean_txt(self, clean_txt):
        pf = parse_file(clean_txt)
        assert pf.format == PromptFormat.TEXT
        assert len(pf.messages) == 1
        assert pf.messages[0].role == "user"

    def test_clean_txt_content(self, clean_txt):
        pf = parse_file(clean_txt)
        assert "summarizes documents" in pf.messages[0].content

    def test_clean_txt_no_variables(self, clean_txt):
        pf = parse_file(clean_txt)
        assert pf.variables == {}


# ---------------------------------------------------------------------------
# parse_stdin
# ---------------------------------------------------------------------------


class TestParseStdin:
    def test_stdin_text(self):
        content = "Hello world"
        pf = parse_stdin(content, "text")
        assert pf.format == PromptFormat.TEXT
        # parse_text resolves the path, so "-" becomes an absolute path ending in "-"
        assert pf.path.name == "-"
        assert len(pf.messages) == 1
        assert pf.messages[0].content == "Hello world"

    def test_stdin_yaml(self):
        content = 'messages:\n  - role: user\n    content: "hi"\n'
        pf = parse_stdin(content, "yaml")
        assert pf.format == PromptFormat.YAML
        assert len(pf.messages) == 1

    def test_stdin_json(self):
        content = '{"messages": [{"role": "user", "content": "hi"}]}'
        pf = parse_stdin(content, "json")
        assert pf.format == PromptFormat.JSON
        assert len(pf.messages) == 1

    def test_stdin_md(self):
        content = "# Title\nSome prompt text"
        pf = parse_stdin(content, "md")
        assert pf.format == PromptFormat.MARKDOWN

    def test_stdin_unsupported_format(self):
        with pytest.raises(ParseError, match="Unsupported"):
            parse_stdin("content", "xml")


# ---------------------------------------------------------------------------
# Variable extraction
# ---------------------------------------------------------------------------


class TestVariableExtraction:
    def test_jinja_variables(self):
        text = "Hello {{name}}, welcome to {{place}}"
        vars = extract_variables(text)
        assert "name" in vars
        assert vars["name"] == "jinja"
        assert "place" in vars
        assert vars["place"] == "jinja"

    def test_fstring_variables(self):
        text = "Hello {name}, welcome to {place}"
        vars = extract_variables(text)
        assert "name" in vars
        assert vars["name"] == "fstring"

    def test_xml_variables(self):
        text = "Process <input_data> and return <output>"
        vars = extract_variables(text)
        assert "input_data" in vars
        assert vars["input_data"] == "xml"
        assert "output" in vars

    def test_mixed_variable_styles(self):
        text = "{{jinja_var}} and {fstring_var} and <xml_var>"
        vars = extract_variables(text)
        assert vars["jinja_var"] == "jinja"
        assert vars["fstring_var"] == "fstring"
        assert vars["xml_var"] == "xml"

    def test_excluded_html_tags(self):
        text = "Use <div> and <span> tags"
        vars = extract_variables(text)
        # div and span are excluded HTML tags, should not appear as variables
        assert "div" not in vars
        assert "span" not in vars

    def test_empty_string(self):
        vars = extract_variables("")
        assert vars == {}

    def test_no_variables(self):
        vars = extract_variables("Just plain text with no variables")
        assert vars == {}


# ---------------------------------------------------------------------------
# Markdown frontmatter
# ---------------------------------------------------------------------------


class TestMarkdownFrontmatter:
    def test_with_frontmatter(self, tmp_path):
        md_file = tmp_path / "prompt.md"
        md_file.write_text(
            "---\ntitle: Test Prompt\nmodel: gpt-4\n---\n\nWrite me a poem about {{topic}}.\n",
            encoding="utf-8",
        )
        pf = parse_file(md_file)
        assert pf.format == PromptFormat.MARKDOWN
        assert pf.metadata.get("title") == "Test Prompt"
        assert pf.metadata.get("model") == "gpt-4"
        assert "topic" in pf.variables

    def test_without_frontmatter(self, tmp_path):
        md_file = tmp_path / "plain.md"
        md_file.write_text("Just a prompt\n", encoding="utf-8")
        pf = parse_file(md_file)
        assert pf.format == PromptFormat.MARKDOWN
        assert pf.metadata == {}


# ---------------------------------------------------------------------------
# JSON layouts
# ---------------------------------------------------------------------------


class TestJsonLayouts:
    def test_messages_layout(self, tmp_path):
        f = tmp_path / "chat.json"
        f.write_text(
            '{"messages": [{"role": "user", "content": "hi"}]}',
            encoding="utf-8",
        )
        pf = parse_file(f)
        assert len(pf.messages) == 1

    def test_prompt_layout(self, tmp_path):
        f = tmp_path / "simple.json"
        f.write_text('{"prompt": "Tell me a joke"}', encoding="utf-8")
        pf = parse_file(f)
        assert len(pf.messages) == 1
        assert pf.messages[0].content == "Tell me a joke"
        assert pf.messages[0].role == "user"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestParseErrors:
    def test_unsupported_extension(self, tmp_path):
        f = tmp_path / "prompt.xml"
        f.write_text("<prompt/>", encoding="utf-8")
        with pytest.raises(ParseError, match="Unsupported"):
            parse_file(f)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_file(Path("/nonexistent/path/prompt.yaml"))


# ---------------------------------------------------------------------------
# parse_directory
# ---------------------------------------------------------------------------


class TestParseDirectory:
    def test_parse_fixtures_dir(self, fixtures_dir):
        results = parse_directory(fixtures_dir)
        assert len(results) > 0
        # Should find yaml, json, and txt files
        formats_found = {pf.format for pf in results}
        assert PromptFormat.YAML in formats_found
        assert PromptFormat.JSON in formats_found
        assert PromptFormat.TEXT in formats_found

    def test_all_results_have_content_hash(self, fixtures_dir):
        results = parse_directory(fixtures_dir)
        for pf in results:
            assert pf.content_hash != ""
            assert len(pf.content_hash) == 64
