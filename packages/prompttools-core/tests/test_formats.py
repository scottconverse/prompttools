"""Tests for prompttools_core format sub-parsers (direct tests, not via parse_file)."""

from pathlib import Path

import pytest

from prompttools_core.errors import ParseError
from prompttools_core.models import PromptFormat
from prompttools_core.formats.text import parse_text
from prompttools_core.formats.markdown import parse_markdown
from prompttools_core.formats.yaml_parser import parse_yaml
from prompttools_core.formats.json_parser import parse_json
from prompttools_core.formats._variables import extract_variables, EXCLUDED_XML_TAGS


# ---------------------------------------------------------------------------
# parse_text
# ---------------------------------------------------------------------------


class TestParseText:
    def test_returns_text_format(self):
        pf = parse_text(Path("test.txt"), "Hello world")
        assert pf.format == PromptFormat.TEXT

    def test_single_user_message(self):
        pf = parse_text(Path("test.txt"), "Hello world")
        assert len(pf.messages) == 1
        assert pf.messages[0].role == "user"
        assert pf.messages[0].content == "Hello world"

    def test_line_start_is_1(self):
        pf = parse_text(Path("test.txt"), "Hello world")
        assert pf.messages[0].line_start == 1

    def test_extracts_variables(self):
        pf = parse_text(Path("test.txt"), "Hello {{name}}, status is {code}")
        assert "name" in pf.variables
        assert pf.variables["name"] == "jinja"
        assert "code" in pf.variables
        assert pf.variables["code"] == "fstring"


# ---------------------------------------------------------------------------
# parse_yaml
# ---------------------------------------------------------------------------


class TestParseYaml:
    def test_all_four_valid_roles(self):
        content = (
            "messages:\n"
            '  - role: system\n    content: "sys"\n'
            '  - role: user\n    content: "usr"\n'
            '  - role: assistant\n    content: "ast"\n'
            '  - role: tool\n    content: "tl"\n'
        )
        pf = parse_yaml(Path("test.yaml"), content)
        roles = [m.role for m in pf.messages]
        assert roles == ["system", "user", "assistant", "tool"]

    def test_variable_defaults_from_defaults_key(self):
        content = (
            "messages:\n"
            '  - role: user\n    content: "Hello {{name}}"\n'
            "defaults:\n"
            '  name: "World"\n'
        )
        pf = parse_yaml(Path("test.yaml"), content)
        assert pf.variable_defaults == {"name": "World"}

    def test_raises_parse_error_for_missing_messages(self):
        content = "model: gpt-4\n"
        with pytest.raises(ParseError, match="messages"):
            parse_yaml(Path("test.yaml"), content)

    def test_raises_parse_error_for_invalid_yaml(self):
        content = "{{: bad yaml"
        with pytest.raises(ParseError, match="Invalid YAML"):
            parse_yaml(Path("test.yaml"), content)

    def test_raises_parse_error_for_non_mapping(self):
        content = "- item1\n- item2\n"
        with pytest.raises(ParseError, match="mapping"):
            parse_yaml(Path("test.yaml"), content)

    def test_raises_parse_error_for_invalid_role(self):
        content = 'messages:\n  - role: villain\n    content: "evil"\n'
        with pytest.raises(ParseError, match="Invalid role"):
            parse_yaml(Path("test.yaml"), content)

    def test_extracts_metadata(self):
        content = (
            "model: gpt-4\n"
            "temperature: 0.7\n"
            "messages:\n"
            '  - role: user\n    content: "hi"\n'
        )
        pf = parse_yaml(Path("test.yaml"), content)
        assert pf.metadata.get("model") == "gpt-4"
        assert pf.metadata.get("temperature") == 0.7

    def test_extracts_variables_from_content(self):
        content = 'messages:\n  - role: user\n    content: "Process {{data}} now"\n'
        pf = parse_yaml(Path("test.yaml"), content)
        assert "data" in pf.variables
        assert pf.variables["data"] == "jinja"

    def test_messages_not_a_list_raises(self):
        content = "messages: not_a_list\n"
        with pytest.raises(ParseError, match="messages"):
            parse_yaml(Path("test.yaml"), content)


# ---------------------------------------------------------------------------
# parse_json
# ---------------------------------------------------------------------------


class TestParseJson:
    def test_messages_layout_multiple_roles(self):
        content = (
            '{"messages": ['
            '{"role": "system", "content": "sys"},'
            '{"role": "user", "content": "usr"},'
            '{"role": "assistant", "content": "ast"}'
            "]}"
        )
        pf = parse_json(Path("test.json"), content)
        assert len(pf.messages) == 3
        assert pf.messages[0].role == "system"
        assert pf.messages[1].role == "user"
        assert pf.messages[2].role == "assistant"

    def test_prompt_layout_single_user_message(self):
        content = '{"prompt": "Tell me a joke"}'
        pf = parse_json(Path("test.json"), content)
        assert len(pf.messages) == 1
        assert pf.messages[0].role == "user"
        assert pf.messages[0].content == "Tell me a joke"

    def test_raises_parse_error_for_invalid_json(self):
        with pytest.raises(ParseError, match="Invalid JSON"):
            parse_json(Path("test.json"), "{bad json")

    def test_raises_parse_error_for_missing_keys(self):
        with pytest.raises(ParseError, match="messages.*prompt"):
            parse_json(Path("test.json"), '{"model": "gpt-4"}')

    def test_validates_roles(self):
        content = '{"messages": [{"role": "villain", "content": "evil"}]}'
        with pytest.raises(ParseError, match="Invalid role"):
            parse_json(Path("test.json"), content)

    def test_extracts_variable_defaults(self):
        content = '{"messages": [{"role": "user", "content": "hi"}], "defaults": {"name": "World"}}'
        pf = parse_json(Path("test.json"), content)
        assert pf.variable_defaults == {"name": "World"}

    def test_extracts_variables_from_content(self):
        content = '{"messages": [{"role": "user", "content": "Hello {{name}}"}]}'
        pf = parse_json(Path("test.json"), content)
        assert "name" in pf.variables


# ---------------------------------------------------------------------------
# parse_markdown
# ---------------------------------------------------------------------------


class TestParseMarkdown:
    def test_with_frontmatter_defaults(self):
        content = "---\ntitle: Test\ndefaults:\n  name: World\n---\n\nHello {{name}}.\n"
        pf = parse_markdown(Path("test.md"), content)
        assert pf.variable_defaults == {"name": "World"}
        assert pf.metadata.get("title") == "Test"

    def test_without_frontmatter(self):
        content = "Just plain markdown\n"
        pf = parse_markdown(Path("test.md"), content)
        assert pf.metadata == {}
        assert len(pf.messages) == 1
        assert pf.messages[0].role == "user"

    def test_body_is_single_user_message(self):
        content = "---\ntitle: Test\n---\n\nBody text here.\n"
        pf = parse_markdown(Path("test.md"), content)
        assert len(pf.messages) == 1
        assert pf.messages[0].role == "user"
        assert "Body text here." in pf.messages[0].content

    def test_extracts_variables_from_body(self):
        content = "Hello {{name}} and {code}\n"
        pf = parse_markdown(Path("test.md"), content)
        assert "name" in pf.variables
        assert "code" in pf.variables


# ---------------------------------------------------------------------------
# extract_variables
# ---------------------------------------------------------------------------


class TestExtractVariables:
    def test_all_three_patterns(self):
        text = "{{jinja_var}} and {fstring_var} and <xml_var>"
        result = extract_variables(text)
        assert result["jinja_var"] == "jinja"
        assert result["fstring_var"] == "fstring"
        assert result["xml_var"] == "xml"

    def test_jinja_priority_over_fstring(self):
        # If same var name appears as both {{name}} and {name},
        # jinja should win
        text = "{{name}} and also {name}"
        result = extract_variables(text)
        assert result["name"] == "jinja"

    def test_excluded_xml_tags_contains_expected(self):
        for tag in ("div", "span", "p", "html", "body"):
            assert tag in EXCLUDED_XML_TAGS

    def test_excluded_xml_tags_has_at_least_30(self):
        assert len(EXCLUDED_XML_TAGS) >= 30

    def test_empty_string_returns_empty(self):
        assert extract_variables("") == {}

    def test_no_variables_returns_empty(self):
        assert extract_variables("Just plain text") == {}
