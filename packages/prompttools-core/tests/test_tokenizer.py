"""Tests for prompttools_core.tokenizer."""

import pytest

from prompttools_core.errors import TokenizerError
from prompttools_core.models import Message, PromptFile, PromptFormat
from prompttools_core.tokenizer import Tokenizer, count_tokens, get_encoding
from pathlib import Path


# ---------------------------------------------------------------------------
# Tokenizer.count
# ---------------------------------------------------------------------------


class TestTokenizerCount:
    def test_count_positive_for_nonempty(self):
        tok = Tokenizer()
        assert tok.count("Hello, world!") > 0

    def test_count_zero_for_empty(self):
        tok = Tokenizer()
        assert tok.count("") == 0

    def test_count_is_int(self):
        tok = Tokenizer()
        result = tok.count("Some text for counting")
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# Tokenizer.count_messages
# ---------------------------------------------------------------------------


class TestTokenizerCountMessages:
    def test_count_messages_includes_overhead(self):
        tok = Tokenizer(provider="openai")
        msgs = [
            Message(role="system", content="You are helpful."),
            Message(role="user", content="Hello"),
        ]
        total = tok.count_messages(msgs)
        # Should be greater than just token counts since overhead is added
        content_only = tok.count("You are helpful.") + tok.count("Hello")
        assert total > content_only

    def test_count_messages_empty_list(self):
        tok = Tokenizer()
        assert tok.count_messages([]) == 0


# ---------------------------------------------------------------------------
# Tokenizer.count_file
# ---------------------------------------------------------------------------


class TestTokenizerCountFile:
    def test_count_file_populates_fields(self):
        tok = Tokenizer()
        pf = PromptFile(
            path=Path("test.yaml"),
            format=PromptFormat.YAML,
            raw_content="test",
            messages=[
                Message(role="system", content="Be helpful."),
                Message(role="user", content="Hello!"),
            ],
        )
        total = tok.count_file(pf)
        assert total > 0
        assert pf.total_tokens == total
        for msg in pf.messages:
            assert msg.token_count is not None
            assert msg.token_count > 0


# ---------------------------------------------------------------------------
# Tokenizer.for_model
# ---------------------------------------------------------------------------


class TestTokenizerForModel:
    def test_for_known_model(self):
        tok = Tokenizer.for_model("gpt-4")
        assert tok.encoding_name == "cl100k_base"

    def test_for_known_model_gpt4o(self):
        tok = Tokenizer.for_model("gpt-4o")
        assert tok.encoding_name == "o200k_base"

    def test_for_unknown_model_raises(self):
        with pytest.raises(TokenizerError, match="Unknown model profile"):
            Tokenizer.for_model("nonexistent-model-xyz")


# ---------------------------------------------------------------------------
# Backward compat: count_tokens and get_encoding
# ---------------------------------------------------------------------------


class TestBackwardCompat:
    def test_count_tokens_function(self):
        result = count_tokens("Hello world")
        assert isinstance(result, int)
        assert result > 0

    def test_count_tokens_empty(self):
        assert count_tokens("") == 0

    def test_get_encoding_default(self):
        enc = get_encoding()
        assert enc is not None

    def test_get_encoding_named(self):
        enc = get_encoding("cl100k_base")
        assert enc is not None

    def test_get_encoding_invalid(self):
        with pytest.raises(TokenizerError, match="Unknown encoding"):
            get_encoding("totally_fake_encoding_name")
