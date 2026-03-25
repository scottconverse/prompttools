"""Tests for prompttools_core.errors -- explicit error hierarchy coverage."""

import pytest

from prompttools_core.errors import (
    CacheError,
    ConfigError,
    ParseError,
    PluginError,
    ProfileNotFoundError,
    PromptToolsError,
    TokenizerError,
)


class TestPromptToolsError:
    def test_is_exception(self):
        assert issubclass(PromptToolsError, Exception)

    def test_catchable_as_exception(self):
        with pytest.raises(Exception):
            raise PromptToolsError("base error")

    def test_preserves_message(self):
        err = PromptToolsError("something went wrong")
        assert str(err) == "something went wrong"

    def test_correct_name(self):
        assert PromptToolsError.__name__ == "PromptToolsError"


class TestParseError:
    def test_catchable_as_prompt_tools_error(self):
        with pytest.raises(PromptToolsError):
            raise ParseError("bad parse")

    def test_catchable_as_value_error(self):
        with pytest.raises(ValueError):
            raise ParseError("bad value")

    def test_correct_name(self):
        assert ParseError.__name__ == "ParseError"

    def test_preserves_message(self):
        err = ParseError("invalid syntax")
        assert str(err) == "invalid syntax"


class TestConfigError:
    def test_catchable_as_prompt_tools_error(self):
        with pytest.raises(PromptToolsError):
            raise ConfigError("bad config")

    def test_not_value_error(self):
        err = ConfigError("oops")
        assert not isinstance(err, ValueError)

    def test_correct_name(self):
        assert ConfigError.__name__ == "ConfigError"


class TestTokenizerError:
    def test_catchable_as_prompt_tools_error(self):
        with pytest.raises(PromptToolsError):
            raise TokenizerError("bad tokenizer")

    def test_correct_name(self):
        assert TokenizerError.__name__ == "TokenizerError"

    def test_preserves_message(self):
        err = TokenizerError("encoding not found")
        assert str(err) == "encoding not found"


class TestProfileNotFoundError:
    def test_catchable_as_prompt_tools_error(self):
        with pytest.raises(PromptToolsError):
            raise ProfileNotFoundError("unknown model")

    def test_correct_name(self):
        assert ProfileNotFoundError.__name__ == "ProfileNotFoundError"


class TestPluginError:
    def test_catchable_as_prompt_tools_error(self):
        with pytest.raises(PromptToolsError):
            raise PluginError("bad plugin")

    def test_correct_name(self):
        assert PluginError.__name__ == "PluginError"


class TestCacheError:
    def test_catchable_as_prompt_tools_error(self):
        with pytest.raises(PromptToolsError):
            raise CacheError("cache fail")

    def test_correct_name(self):
        assert CacheError.__name__ == "CacheError"

    def test_preserves_message(self):
        err = CacheError("disk full")
        assert str(err) == "disk full"


class TestAllErrorClasses:
    """Cross-cutting tests for all 7 error classes."""

    @pytest.mark.parametrize(
        "cls",
        [
            PromptToolsError,
            ParseError,
            ConfigError,
            TokenizerError,
            ProfileNotFoundError,
            PluginError,
            CacheError,
        ],
    )
    def test_all_are_subclasses_of_base(self, cls):
        assert issubclass(cls, PromptToolsError)

    @pytest.mark.parametrize(
        "cls",
        [
            PromptToolsError,
            ParseError,
            ConfigError,
            TokenizerError,
            ProfileNotFoundError,
            PluginError,
            CacheError,
        ],
    )
    def test_all_are_instantiable_with_message(self, cls):
        err = cls("test message")
        assert str(err) == "test message"
