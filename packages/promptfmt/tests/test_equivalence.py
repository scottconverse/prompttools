"""Tests for promptfmt.equivalence."""

from pathlib import Path

from prompttools_core.models import Message, PromptFile, PromptFormat
from promptfmt.equivalence import is_equivalent, _normalize_whitespace


def _make_prompt_file(
    messages=None,
    variables=None,
    metadata=None,
) -> PromptFile:
    """Helper to create a PromptFile for testing."""
    return PromptFile(
        path=Path("test.txt"),
        format=PromptFormat.TEXT,
        raw_content="",
        messages=messages or [],
        variables=variables or {},
        metadata=metadata or {},
    )


class TestIsEquivalent:
    """Tests for semantic equivalence checking."""

    def test_identical_prompt_files(self):
        """Identical PromptFiles are equivalent."""
        pf1 = _make_prompt_file(
            messages=[Message(role="user", content="Hello world")],
            variables={"name": "double_brace"},
            metadata={"model": "gpt-4"},
        )
        pf2 = _make_prompt_file(
            messages=[Message(role="user", content="Hello world")],
            variables={"name": "double_brace"},
            metadata={"model": "gpt-4"},
        )
        assert is_equivalent(pf1, pf2) is True

    def test_different_message_counts(self):
        """Different message counts are not equivalent."""
        pf1 = _make_prompt_file(
            messages=[Message(role="user", content="Hello")],
        )
        pf2 = _make_prompt_file(
            messages=[
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi"),
            ],
        )
        assert is_equivalent(pf1, pf2) is False

    def test_different_message_roles(self):
        """Different message roles are not equivalent."""
        pf1 = _make_prompt_file(
            messages=[Message(role="user", content="Hello")],
        )
        pf2 = _make_prompt_file(
            messages=[Message(role="system", content="Hello")],
        )
        assert is_equivalent(pf1, pf2) is False

    def test_whitespace_only_content_difference(self):
        """Whitespace-only content differences are equivalent."""
        pf1 = _make_prompt_file(
            messages=[Message(role="user", content="Hello   world")],
        )
        pf2 = _make_prompt_file(
            messages=[Message(role="user", content="Hello world")],
        )
        assert is_equivalent(pf1, pf2) is True

    def test_semantic_content_difference(self):
        """Semantic content differences are not equivalent."""
        pf1 = _make_prompt_file(
            messages=[Message(role="user", content="Hello world")],
        )
        pf2 = _make_prompt_file(
            messages=[Message(role="user", content="Goodbye world")],
        )
        assert is_equivalent(pf1, pf2) is False

    def test_different_variable_names(self):
        """Different variable names are not equivalent."""
        pf1 = _make_prompt_file(
            variables={"name": "double_brace", "role": "double_brace"},
        )
        pf2 = _make_prompt_file(
            variables={"name": "double_brace", "task": "double_brace"},
        )
        assert is_equivalent(pf1, pf2) is False

    def test_same_variables_different_syntax(self):
        """Same variable names with different syntax styles are equivalent."""
        pf1 = _make_prompt_file(
            variables={"name": "double_brace", "role": "double_brace"},
        )
        pf2 = _make_prompt_file(
            variables={"name": "single_brace", "role": "angle_bracket"},
        )
        assert is_equivalent(pf1, pf2) is True

    def test_different_metadata_values(self):
        """Different metadata values are not equivalent."""
        pf1 = _make_prompt_file(
            metadata={"model": "gpt-4"},
        )
        pf2 = _make_prompt_file(
            metadata={"model": "gpt-3.5"},
        )
        assert is_equivalent(pf1, pf2) is False

    def test_empty_messages_variables_metadata(self):
        """Empty messages, variables, and metadata are equivalent."""
        pf1 = _make_prompt_file()
        pf2 = _make_prompt_file()
        assert is_equivalent(pf1, pf2) is True

    def test_extra_whitespace_tabs_newlines(self):
        """Content differing only by tabs and newlines is equivalent."""
        pf1 = _make_prompt_file(
            messages=[Message(role="user", content="Hello\t\tworld\n\n")],
        )
        pf2 = _make_prompt_file(
            messages=[Message(role="user", content="Hello world")],
        )
        assert is_equivalent(pf1, pf2) is True

    def test_missing_metadata_key(self):
        """One prompt with metadata, one without, are not equivalent."""
        pf1 = _make_prompt_file(metadata={"model": "gpt-4"})
        pf2 = _make_prompt_file(metadata={})
        assert is_equivalent(pf1, pf2) is False


class TestNormalizeWhitespace:
    """Tests for the _normalize_whitespace helper."""

    def test_collapses_runs(self):
        """Collapses multiple spaces into one."""
        assert _normalize_whitespace("hello   world") == "hello world"

    def test_strips_leading_trailing(self):
        """Strips leading and trailing whitespace."""
        assert _normalize_whitespace("  hello  ") == "hello"

    def test_handles_tabs_and_newlines(self):
        """Handles tabs and newlines."""
        assert _normalize_whitespace("hello\t\n\tworld") == "hello world"

    def test_empty_string(self):
        """Empty string returns empty string."""
        assert _normalize_whitespace("") == ""
