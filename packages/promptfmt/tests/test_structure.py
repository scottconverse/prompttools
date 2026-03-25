"""Tests for promptfmt.rules.structure."""

import json

import yaml

from prompttools_core.models import PromptFormat
from promptfmt.rules.structure import apply, apply_yaml, apply_json


class TestApplyYaml:
    """Tests for YAML structure normalization."""

    def test_sorts_metadata_keys_with_priority(self):
        """Sorts metadata keys: model, name, description, defaults first."""
        content = "description: A prompt\nmodel: gpt-4\nzoo: animals\nname: test\n"
        result = apply_yaml(content)
        data = yaml.safe_load(result)
        keys = list(data.keys())
        # model, name, description should come before zoo
        assert keys.index("model") < keys.index("zoo")
        assert keys.index("name") < keys.index("zoo")
        assert keys.index("description") < keys.index("zoo")

    def test_sorts_message_role_before_content(self):
        """In message objects, role comes before content."""
        content = "messages:\n  - content: hello\n    role: user\n"
        result = apply_yaml(content)
        # In the output, role should appear before content
        role_pos = result.find("role:")
        content_pos = result.find("content:")
        assert role_pos < content_pos

    def test_consistent_indentation(self):
        """Uses consistent indentation (default 2 spaces)."""
        content = "messages:\n    - role: user\n      content: hello\n"
        result = apply_yaml(content, indent=2)
        # yaml.dump uses its own indent scheme; verify it parses back
        data = yaml.safe_load(result)
        assert data["messages"][0]["role"] == "user"

    def test_invalid_yaml_returns_original(self):
        """Gracefully handles invalid YAML (returns original content)."""
        content = ":::not valid yaml:::\n{{{invalid"
        result = apply_yaml(content)
        assert result == content

    def test_non_mapping_yaml_returns_original(self):
        """Non-mapping YAML (e.g., a list) returns original content."""
        content = "- item1\n- item2\n- item3\n"
        result = apply_yaml(content)
        assert result == content

    def test_sort_keys_false_preserves_order(self):
        """sort_keys=False preserves original key ordering."""
        content = "zoo: 1\nalpha: 2\nmodel: 3\n"
        result = apply_yaml(content, sort_keys=False)
        data = yaml.safe_load(result)
        keys = list(data.keys())
        # Order should be preserved from original
        assert keys == ["zoo", "alpha", "model"]

    def test_defaults_priority_key(self):
        """The 'defaults' key is a priority key and should appear early."""
        content = "zebra: 1\ndefaults:\n  temp: 0.7\nmodel: gpt-4\n"
        result = apply_yaml(content, sort_keys=True)
        data = yaml.safe_load(result)
        keys = list(data.keys())
        assert keys.index("model") < keys.index("zebra")
        assert keys.index("defaults") < keys.index("zebra")


class TestApplyJson:
    """Tests for JSON structure normalization."""

    def test_sorts_keys_with_priority(self):
        """Sorts keys: model, name, description, defaults first."""
        content = json.dumps({"zoo": 1, "model": "gpt-4", "name": "test", "alpha": 2})
        result = apply_json(content)
        data = json.loads(result)
        keys = list(data.keys())
        assert keys.index("model") < keys.index("alpha")
        assert keys.index("model") < keys.index("zoo")
        assert keys.index("name") < keys.index("zoo")

    def test_consistent_indentation(self):
        """Uses consistent indentation (default 2 spaces)."""
        content = json.dumps({"model": "gpt-4", "messages": []})
        result = apply_json(content, indent=2)
        assert "  " in result
        # Verify it parses back correctly
        data = json.loads(result)
        assert data["model"] == "gpt-4"

    def test_invalid_json_returns_original(self):
        """Gracefully handles invalid JSON (returns original content)."""
        content = "{not valid json!!!"
        result = apply_json(content)
        assert result == content

    def test_non_object_json_returns_original(self):
        """Non-object JSON (e.g., an array) returns original content."""
        content = "[1, 2, 3]"
        result = apply_json(content)
        assert result == content

    def test_sort_keys_false_preserves_order(self):
        """sort_keys=False preserves original key ordering."""
        content = json.dumps({"zoo": 1, "alpha": 2, "model": 3})
        result = apply_json(content, sort_keys=False)
        data = json.loads(result)
        keys = list(data.keys())
        assert keys == ["zoo", "alpha", "model"]


class TestApplyDispatch:
    """Tests for the apply() dispatch function."""

    def test_routes_yaml(self):
        """Routes YAML format to apply_yaml."""
        content = "model: gpt-4\nname: test\n"
        result = apply(content, fmt=PromptFormat.YAML)
        data = yaml.safe_load(result)
        assert data["model"] == "gpt-4"

    def test_routes_json(self):
        """Routes JSON format to apply_json."""
        content = json.dumps({"model": "gpt-4"})
        result = apply(content, fmt=PromptFormat.JSON)
        data = json.loads(result)
        assert data["model"] == "gpt-4"

    def test_text_format_unchanged(self):
        """Returns content unchanged for TEXT format."""
        content = "Hello world\nThis is text\n"
        result = apply(content, fmt=PromptFormat.TEXT)
        assert result == content

    def test_markdown_format_unchanged(self):
        """Returns content unchanged for MARKDOWN format."""
        content = "# Hello\n\nThis is markdown\n"
        result = apply(content, fmt=PromptFormat.MARKDOWN)
        assert result == content
