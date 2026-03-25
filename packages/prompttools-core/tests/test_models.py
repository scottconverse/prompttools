"""Tests for prompttools_core.models."""

import hashlib
from pathlib import Path

import pytest

from prompttools_core.models import (
    Message,
    ModelProfile,
    PipelineStage,
    PromptFile,
    PromptFormat,
    PromptPipeline,
    ToolConfig,
)


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------


class TestMessage:
    def test_create_with_required_fields(self):
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_create_with_all_fields(self):
        msg = Message(
            role="system",
            content="You are helpful.",
            line_start=1,
            line_end=3,
            token_count=42,
            metadata={"source": "test"},
        )
        assert msg.role == "system"
        assert msg.content == "You are helpful."
        assert msg.line_start == 1
        assert msg.line_end == 3
        assert msg.token_count == 42
        assert msg.metadata == {"source": "test"}

    def test_defaults(self):
        msg = Message(role="user", content="hi")
        assert msg.line_start is None
        assert msg.line_end is None
        assert msg.token_count is None
        assert msg.metadata == {}

    def test_all_roles(self):
        for role in ("system", "user", "assistant", "tool"):
            msg = Message(role=role, content="test")
            assert msg.role == role

    def test_invalid_role_rejected(self):
        with pytest.raises(Exception):
            Message(role="invalid", content="test")


# ---------------------------------------------------------------------------
# PromptFile
# ---------------------------------------------------------------------------


class TestPromptFile:
    def _make_prompt_file(self, **kwargs):
        defaults = {
            "path": Path("test.yaml"),
            "format": PromptFormat.YAML,
            "raw_content": "test content",
            "messages": [Message(role="user", content="Hello")],
        }
        defaults.update(kwargs)
        return PromptFile(**defaults)

    def test_create_basic(self):
        pf = self._make_prompt_file()
        assert pf.format == PromptFormat.YAML
        assert len(pf.messages) == 1
        assert pf.variables == {}
        assert pf.total_tokens is None

    def test_content_hash_auto_generated(self):
        pf = self._make_prompt_file(raw_content="hello world")
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert pf.content_hash == expected

    def test_content_hash_not_overwritten_if_provided(self):
        pf = self._make_prompt_file(content_hash="custom_hash")
        assert pf.content_hash == "custom_hash"

    def test_system_message_found(self):
        msgs = [
            Message(role="system", content="sys"),
            Message(role="user", content="usr"),
        ]
        pf = self._make_prompt_file(messages=msgs)
        sys_msg = pf.system_message()
        assert sys_msg is not None
        assert sys_msg.role == "system"
        assert sys_msg.content == "sys"

    def test_system_message_none_when_absent(self):
        msgs = [Message(role="user", content="usr")]
        pf = self._make_prompt_file(messages=msgs)
        assert pf.system_message() is None

    def test_user_messages(self):
        msgs = [
            Message(role="system", content="sys"),
            Message(role="user", content="u1"),
            Message(role="user", content="u2"),
        ]
        pf = self._make_prompt_file(messages=msgs)
        users = pf.user_messages()
        assert len(users) == 2
        assert all(m.role == "user" for m in users)

    def test_has_role_true(self):
        msgs = [
            Message(role="system", content="sys"),
            Message(role="user", content="usr"),
        ]
        pf = self._make_prompt_file(messages=msgs)
        assert pf.has_role("system") is True
        assert pf.has_role("user") is True

    def test_has_role_false(self):
        msgs = [Message(role="user", content="usr")]
        pf = self._make_prompt_file(messages=msgs)
        assert pf.has_role("system") is False
        assert pf.has_role("assistant") is False


# ---------------------------------------------------------------------------
# PromptFormat
# ---------------------------------------------------------------------------


class TestPromptFormat:
    def test_enum_values(self):
        assert PromptFormat.TEXT == "text"
        assert PromptFormat.MARKDOWN == "md"
        assert PromptFormat.YAML == "yaml"
        assert PromptFormat.JSON == "json"

    def test_all_formats_present(self):
        names = {f.name for f in PromptFormat}
        assert names == {"TEXT", "MARKDOWN", "YAML", "JSON"}


# ---------------------------------------------------------------------------
# ModelProfile
# ---------------------------------------------------------------------------


class TestModelProfile:
    def test_create_with_pricing(self):
        profile = ModelProfile(
            name="test-model",
            context_window=4096,
            encoding="cl100k_base",
            provider="openai",
            input_price_per_mtok=10.0,
            output_price_per_mtok=30.0,
        )
        assert profile.name == "test-model"
        assert profile.context_window == 4096
        assert profile.input_price_per_mtok == 10.0
        assert profile.output_price_per_mtok == 30.0

    def test_tokenizer_encoding_alias(self):
        profile = ModelProfile(
            name="m",
            context_window=1000,
            encoding="cl100k_base",
        )
        assert profile.tokenizer_encoding == "cl100k_base"
        assert profile.tokenizer_encoding == profile.encoding

    def test_defaults(self):
        profile = ModelProfile(
            name="m",
            context_window=1000,
            encoding="cl100k_base",
        )
        assert profile.provider == "unknown"
        assert profile.input_price_per_mtok is None
        assert profile.output_price_per_mtok is None
        assert profile.max_output_tokens is None
        assert profile.supports_system_message is True
        assert profile.supports_tools is False
        assert profile.approximate_tokenizer is False

    def test_frozen(self):
        profile = ModelProfile(name="m", context_window=1000, encoding="cl100k_base")
        with pytest.raises(Exception):
            profile.name = "other"


# ---------------------------------------------------------------------------
# ToolConfig
# ---------------------------------------------------------------------------


class TestToolConfig:
    def test_defaults(self):
        config = ToolConfig()
        assert config.model is None
        assert config.tokenizer_encoding is None
        assert config.exclude == []
        assert config.plugins == []
        assert config.cache_enabled is False
        assert config.cache_dir == Path(".prompttools-cache")
        assert config.extra == {}

    def test_custom_values(self):
        config = ToolConfig(
            model="gpt-4",
            exclude=["*.bak"],
            cache_enabled=True,
        )
        assert config.model == "gpt-4"
        assert config.exclude == ["*.bak"]
        assert config.cache_enabled is True


# ---------------------------------------------------------------------------
# PipelineStage & PromptPipeline
# ---------------------------------------------------------------------------


class TestPipelineStage:
    def test_create_minimal(self):
        stage = PipelineStage(name="stage1")
        assert stage.name == "stage1"
        assert stage.file is None
        assert stage.persona is None
        assert stage.expected_output_tokens == 0
        assert stage.depends_on == []
        assert stage.prompt_file is None

    def test_create_with_all_fields(self):
        stage = PipelineStage(
            name="stage1",
            file=Path("prompt.yaml"),
            persona="analyst",
            expected_output_tokens=500,
            depends_on=["stage0"],
        )
        assert stage.file == Path("prompt.yaml")
        assert stage.persona == "analyst"
        assert stage.expected_output_tokens == 500
        assert stage.depends_on == ["stage0"]


class TestPromptPipeline:
    def test_create(self):
        pipeline = PromptPipeline(
            name="test-pipeline",
            manifest_path=Path("pipeline.yaml"),
            stages=[PipelineStage(name="s1")],
        )
        assert pipeline.name == "test-pipeline"
        assert pipeline.model is None
        assert len(pipeline.stages) == 1
        assert pipeline.cumulative_tokens is None

    def test_with_model(self):
        pipeline = PromptPipeline(
            name="p",
            manifest_path=Path("p.yaml"),
            model="gpt-4",
        )
        assert pipeline.model == "gpt-4"
