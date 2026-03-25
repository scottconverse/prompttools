"""Tests for promptfmt.rules.whitespace."""

from promptfmt.rules.whitespace import apply


class TestWhitespace:
    def test_strips_trailing_whitespace(self):
        result = apply("hello   \nworld  \n")
        assert result == "hello\nworld\n"

    def test_normalizes_crlf(self):
        result = apply("hello\r\nworld\r\n")
        assert result == "hello\nworld\n"

    def test_removes_leading_blank_lines(self):
        result = apply("\n\n\nhello\n")
        assert result == "hello\n"

    def test_collapses_multiple_blank_lines(self):
        result = apply("hello\n\n\n\n\nworld\n")
        assert result == "hello\n\n\nworld\n"

    def test_ensures_final_newline(self):
        result = apply("hello")
        assert result == "hello\n"

    def test_removes_trailing_blank_lines(self):
        result = apply("hello\n\n\n\n")
        assert result == "hello\n"

    def test_empty_input(self):
        result = apply("")
        assert result == ""

    def test_whitespace_only(self):
        result = apply("   \n   \n")
        assert result == ""

    def test_idempotent(self):
        content = "hello\n\nworld\n"
        assert apply(apply(content)) == apply(content)
