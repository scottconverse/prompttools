"""Tests for promptfmt.rules.delimiters."""

from promptfmt.rules.delimiters import apply


class TestDelimiterNormalization:
    """Tests for section delimiter normalization across 5 styles."""

    def test_convert_dashes_to_hashes(self):
        """Convert --- to ### (default target)."""
        content = "hello\n---\nworld"
        result = apply(content, style="###")
        assert "###" in result
        assert "---" not in result

    def test_convert_equals_to_hashes(self):
        """Convert === to ###."""
        content = "hello\n===\nworld"
        result = apply(content, style="###")
        assert "###" in result
        assert "===" not in result

    def test_convert_stars_to_hashes(self):
        """Convert *** to ###."""
        content = "hello\n***\nworld"
        result = apply(content, style="###")
        assert "###" in result
        assert "***" not in result

    def test_convert_tildes_to_hashes(self):
        """Convert ~~~ to ###."""
        content = "hello\n~~~\nworld"
        result = apply(content, style="###")
        assert "###" in result
        assert "~~~" not in result

    def test_convert_dashes_to_equals(self):
        """Convert --- to === when target is ===."""
        content = "hello\n---\nworld"
        result = apply(content, style="===")
        assert "===" in result
        assert "---" not in result

    def test_convert_dashes_to_tildes(self):
        """Convert --- to ~~~ when target is ~~~."""
        content = "hello\n---\nworld"
        result = apply(content, style="~~~")
        assert "~~~" in result.split("\n")[1]
        assert result.split("\n")[1].strip() == "~~~"

    def test_convert_dashes_to_stars(self):
        """Convert --- to *** when target is ***."""
        content = "hello\n---\nworld"
        result = apply(content, style="***")
        assert "***" in result
        assert "---" not in result

    def test_preserves_code_blocks(self):
        """Delimiters inside code blocks are not converted."""
        content = "hello\n```\n---\n===\n```\nworld"
        result = apply(content, style="###")
        lines = result.split("\n")
        # The --- and === inside the code block should remain
        assert "---" in result
        assert "===" in result

    def test_non_delimiter_lines_unchanged(self):
        """Non-delimiter lines are not modified."""
        content = "hello world\nthis is normal text\nmore text"
        result = apply(content, style="###")
        assert result == content

    def test_mixed_delimiter_styles(self):
        """File with mixed delimiter styles all get normalized."""
        content = "part1\n---\npart2\n===\npart3\n***\npart4\n~~~\npart5"
        result = apply(content, style="###")
        lines = result.split("\n")
        # All delimiters should be ###
        for line in lines:
            assert "---" not in line or line.startswith("```")
            assert "===" not in line
            assert "***" not in line
            assert "~~~" not in line

    def test_idempotent(self):
        """apply(apply(content, style), style) == apply(content, style)."""
        content = "hello\n---\nworld\n===\nend"
        once = apply(content, style="###")
        twice = apply(once, style="###")
        assert once == twice

    def test_long_delimiters_converted(self):
        """Delimiters with more than 3 characters (e.g., -----) are also converted."""
        content = "hello\n-----\nworld"
        result = apply(content, style="###")
        assert "###" in result
        assert "-----" not in result

    def test_default_style_is_hashes(self):
        """Default style parameter is ###."""
        content = "hello\n---\nworld"
        result = apply(content)
        assert "###" in result
