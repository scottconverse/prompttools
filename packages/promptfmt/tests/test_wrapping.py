"""Tests for promptfmt.rules.wrapping."""

from promptfmt.rules.wrapping import apply


class TestLineWrapping:
    """Tests for line wrapping at word boundaries with exclusions."""

    def test_wraps_long_line(self):
        """Wraps lines exceeding max_length at word boundaries."""
        long_line = "word " * 30  # ~150 chars
        result = apply(long_line.strip(), max_length=80)
        for line in result.split("\n"):
            # Each line should be at or under max_length
            # (unless a single word exceeds it)
            assert len(line) <= 80 or " " not in line.strip()

    def test_short_lines_unchanged(self):
        """Short lines (under max_length) are not modified."""
        content = "Hello world\nThis is fine\nShort line"
        result = apply(content, max_length=80)
        assert result == content

    def test_code_blocks_not_wrapped(self):
        """Lines inside code blocks are never wrapped."""
        long_code = "x " * 100
        content = f"normal\n```\n{long_code}\n```\nnormal"
        result = apply(content, max_length=40)
        lines = result.split("\n")
        # The code block line should remain intact
        assert long_code in result

    def test_url_lines_not_wrapped(self):
        """URL lines are never wrapped."""
        url_line = "https://example.com/very/long/path/that/exceeds/the/maximum/line/length/significantly"
        content = f"See: {url_line}"
        # The line starts with "See:" not a URL, so let's test a pure URL line
        result = apply(url_line, max_length=40)
        assert result == url_line

    def test_table_rows_not_wrapped(self):
        """Table rows (starting with |) are never wrapped."""
        table_row = "| Column 1 | Column 2 | Column 3 | Column 4 | Column 5 | Column 6 | Column 7 | Column 8 |"
        result = apply(table_row, max_length=40)
        assert result == table_row

    def test_heading_lines_not_wrapped(self):
        """Heading lines (starting with #) are never wrapped."""
        heading = "# This is a very long heading that should not be wrapped even if it exceeds the maximum line length"
        result = apply(heading, max_length=40)
        assert result == heading

    def test_preserves_indentation(self):
        """Leading indentation is preserved on continuation lines."""
        content = "    " + "word " * 30  # indented long line
        result = apply(content, max_length=60)
        lines = result.split("\n")
        # All continuation lines should preserve the indentation
        for line in lines:
            if line.strip():
                assert line.startswith("    ")

    def test_max_length_zero_disables(self):
        """max_length=0 disables wrapping entirely."""
        long_line = "word " * 100
        result = apply(long_line, max_length=0)
        assert result == long_line

    def test_max_length_negative_disables(self):
        """max_length with negative value disables wrapping."""
        long_line = "word " * 100
        result = apply(long_line, max_length=-1)
        assert result == long_line

    def test_idempotent(self):
        """apply(apply(content, n), n) == apply(content, n)."""
        content = "This is a line that is quite long and should be wrapped at word boundaries to fit within the specified maximum length"
        once = apply(content, max_length=60)
        twice = apply(once, max_length=60)
        assert once == twice

    def test_multiple_lines_mixed(self):
        """File with mix of long and short lines."""
        content = "Short line\n" + "word " * 30 + "\nAnother short line"
        result = apply(content, max_length=80)
        lines = result.split("\n")
        assert lines[0] == "Short line"
        assert lines[-1] == "Another short line"

    def test_empty_content(self):
        """Empty content returns empty."""
        result = apply("", max_length=80)
        assert result == ""
