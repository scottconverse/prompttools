"""Tests for promptlint.core.parser."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from promptlint.core.parser import (
    _extract_variables,
    parse_file,
    parse_pipeline_manifest,
    parse_stdin,
)
from promptlint.models import PromptFormat


# ---------------------------------------------------------------------------
# _extract_variables
# ---------------------------------------------------------------------------


class TestExtractVariables:
    def test_jinja_vars(self) -> None:
        result = _extract_variables("Hello {{name}}, your order {{order_id}} is ready.")
        assert result["name"] == "jinja"
        assert result["order_id"] == "jinja"

    def test_fstring_vars(self) -> None:
        result = _extract_variables("Hello {name}, order {order_id}.")
        assert result["name"] == "fstring"
        assert result["order_id"] == "fstring"

    def test_xml_vars(self) -> None:
        result = _extract_variables("Process <user_input> and return <output_format>.")
        assert result["user_input"] == "xml"
        assert result["output_format"] == "xml"

    def test_excludes_html_tags(self) -> None:
        result = _extract_variables("Use <div> and <span> for layout.")
        assert "div" not in result
        assert "span" not in result

    def test_mixed_styles(self) -> None:
        result = _extract_variables("{{a}} and {b} and <c>")
        assert result["a"] == "jinja"
        assert result["b"] == "fstring"
        assert result["c"] == "xml"

    def test_no_vars(self) -> None:
        result = _extract_variables("No variables here.")
        assert result == {}


# ---------------------------------------------------------------------------
# parse_file — text
# ---------------------------------------------------------------------------


class TestParseText:
    def test_parses_txt(self, tmp_path: Path) -> None:
        f = tmp_path / "prompt.txt"
        f.write_text("Hello world", encoding="utf-8")
        pf = parse_file(f)
        assert pf.format == PromptFormat.TEXT
        assert len(pf.messages) == 1
        assert pf.messages[0].role == "user"
        assert pf.messages[0].content == "Hello world"
        assert pf.messages[0].line_start == 1

    def test_extracts_variables_from_txt(self, tmp_path: Path) -> None:
        f = tmp_path / "prompt.txt"
        f.write_text("Hello {{name}}", encoding="utf-8")
        pf = parse_file(f)
        assert "name" in pf.variables


# ---------------------------------------------------------------------------
# parse_file — markdown
# ---------------------------------------------------------------------------


class TestParseMarkdown:
    def test_parses_md_no_frontmatter(self, tmp_path: Path) -> None:
        f = tmp_path / "prompt.md"
        f.write_text("# Title\n\nBody text.", encoding="utf-8")
        pf = parse_file(f)
        assert pf.format == PromptFormat.MARKDOWN
        assert len(pf.messages) == 1
        assert pf.metadata == {}

    def test_parses_md_with_frontmatter(self, tmp_path: Path) -> None:
        content = "---\nmodel: gpt-4\ntags:\n  - test\n---\nBody text."
        f = tmp_path / "prompt.md"
        f.write_text(content, encoding="utf-8")
        pf = parse_file(f)
        assert pf.metadata["model"] == "gpt-4"
        assert "Body text." in pf.messages[0].content

    def test_frontmatter_line_offset(self, tmp_path: Path) -> None:
        content = "---\nkey: val\n---\nBody"
        f = tmp_path / "prompt.md"
        f.write_text(content, encoding="utf-8")
        pf = parse_file(f)
        assert pf.messages[0].line_start == 4


# ---------------------------------------------------------------------------
# parse_file — yaml
# ---------------------------------------------------------------------------


class TestParseYaml:
    def test_parses_yaml_messages(self, tmp_path: Path) -> None:
        data = {
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hi."},
            ]
        }
        f = tmp_path / "prompt.yaml"
        f.write_text(yaml.dump(data), encoding="utf-8")
        pf = parse_file(f)
        assert pf.format == PromptFormat.YAML
        assert len(pf.messages) == 2
        assert pf.messages[0].role == "system"

    def test_yaml_metadata_extracted(self, tmp_path: Path) -> None:
        content = "model: gpt-4\nmessages:\n  - role: user\n    content: hello\n"
        f = tmp_path / "prompt.yaml"
        f.write_text(content, encoding="utf-8")
        pf = parse_file(f)
        assert pf.metadata["model"] == "gpt-4"

    def test_yaml_malformed_no_messages(self, tmp_path: Path) -> None:
        f = tmp_path / "prompt.yaml"
        f.write_text("key: value\n", encoding="utf-8")
        with pytest.raises(ValueError, match="messages"):
            parse_file(f)

    def test_yaml_malformed_not_mapping(self, tmp_path: Path) -> None:
        f = tmp_path / "prompt.yaml"
        f.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="mapping"):
            parse_file(f)


# ---------------------------------------------------------------------------
# parse_file — json
# ---------------------------------------------------------------------------


class TestParseJson:
    def test_parses_json_messages(self, tmp_path: Path) -> None:
        data = {
            "messages": [
                {"role": "system", "content": "Be concise."},
                {"role": "user", "content": "Summarize this."},
            ]
        }
        f = tmp_path / "prompt.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        pf = parse_file(f)
        assert pf.format == PromptFormat.JSON
        assert len(pf.messages) == 2

    def test_parses_json_prompt_string(self, tmp_path: Path) -> None:
        data = {"prompt": "Tell me a joke."}
        f = tmp_path / "prompt.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        pf = parse_file(f)
        assert len(pf.messages) == 1
        assert pf.messages[0].content == "Tell me a joke."

    def test_json_malformed(self, tmp_path: Path) -> None:
        f = tmp_path / "prompt.json"
        f.write_text('{"other": 42}', encoding="utf-8")
        with pytest.raises(ValueError, match="messages"):
            parse_file(f)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestParseErrors:
    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            parse_file(tmp_path / "nonexistent.txt")

    def test_unsupported_extension(self, tmp_path: Path) -> None:
        f = tmp_path / "prompt.docx"
        f.write_text("content", encoding="utf-8")
        with pytest.raises(ValueError, match="Unsupported"):
            parse_file(f)


# ---------------------------------------------------------------------------
# parse_stdin
# ---------------------------------------------------------------------------


class TestParseStdin:
    def test_stdin_text(self) -> None:
        pf = parse_stdin("Hello world", "text")
        assert pf.path.name == "-"
        assert pf.format == PromptFormat.TEXT

    def test_stdin_yaml(self) -> None:
        content = yaml.dump({"messages": [{"role": "user", "content": "Hi"}]})
        pf = parse_stdin(content, "yaml")
        assert pf.format == PromptFormat.YAML

    def test_stdin_invalid_format(self) -> None:
        with pytest.raises(ValueError, match="Unsupported"):
            parse_stdin("content", "csv")


# ---------------------------------------------------------------------------
# parse_pipeline_manifest
# ---------------------------------------------------------------------------


class TestParsePipelineManifest:
    def test_parses_pipeline(self, tmp_path: Path) -> None:
        # Create stage prompt files
        (tmp_path / "stage1.txt").write_text("Stage 1 content", encoding="utf-8")
        (tmp_path / "stage2.txt").write_text("Stage 2 content", encoding="utf-8")

        manifest = {
            "name": "test-pipeline",
            "stages": [
                {"name": "step1", "file": "stage1.txt"},
                {"name": "step2", "file": "stage2.txt", "depends_on": ["step1"]},
            ],
        }
        mf = tmp_path / ".promptlint-pipeline.yaml"
        mf.write_text(yaml.dump(manifest), encoding="utf-8")

        pipeline = parse_pipeline_manifest(mf)
        assert pipeline.name == "test-pipeline"
        assert len(pipeline.stages) == 2
        assert pipeline.stages[1].depends_on == ["step1"]

    def test_manifest_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            parse_pipeline_manifest(tmp_path / "missing.yaml")

    def test_manifest_missing_file_key(self, tmp_path: Path) -> None:
        manifest = {"stages": [{"name": "step1"}]}
        mf = tmp_path / "pipeline.yaml"
        mf.write_text(yaml.dump(manifest), encoding="utf-8")
        with pytest.raises(ValueError, match="file"):
            parse_pipeline_manifest(mf)
