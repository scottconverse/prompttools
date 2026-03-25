"""Tests for promptfmt.rules.variables."""

from promptfmt.rules.variables import apply


class TestVariableNormalization:
    def test_fstring_to_double_brace(self):
        result = apply("Hello {name}", style="double_brace")
        assert result == "Hello {{name}}"

    def test_xml_to_double_brace(self):
        result = apply("Hello <name>", style="double_brace")
        assert result == "Hello {{name}}"

    def test_double_brace_to_single_brace(self):
        result = apply("Hello {{name}}", style="single_brace")
        assert result == "Hello {name}"

    def test_double_brace_to_angle_bracket(self):
        result = apply("Hello {{name}}", style="angle_bracket")
        assert result == "Hello <name>"

    def test_preserves_code_blocks(self):
        content = "Hello {{name}}\n```\n{code_block}\n```\nBye {{name}}"
        result = apply(content, style="double_brace")
        assert "{code_block}" in result

    def test_preserves_inline_code(self):
        result = apply("Use `{var}` for variables and {{name}}", style="double_brace")
        assert "`{var}`" in result

    def test_excludes_html_tags(self):
        result = apply("Hello <div> world <name>", style="double_brace")
        assert "<div>" in result  # HTML tag preserved
        assert "{{name}}" in result  # Variable converted

    def test_idempotent(self):
        content = "Hello {{name}} and {{role}}"
        assert apply(apply(content)) == apply(content)

    def test_mixed_styles_normalized(self):
        content = "Hello {{name}} and {role} and <task>"
        result = apply(content, style="double_brace")
        assert result == "Hello {{name}} and {{role}} and {{task}}"
