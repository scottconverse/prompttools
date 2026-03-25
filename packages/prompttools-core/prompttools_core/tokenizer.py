"""Tokenization engine for the prompttools suite.

Wraps tiktoken with caching, encoding selection based on model profiles,
and a consistent interface for all tools.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Any

from prompttools_core.errors import TokenizerError

if TYPE_CHECKING:
    from prompttools_core.models import Message, PromptFile

_TIKTOKEN_AVAILABLE = True

try:
    import tiktoken
except ImportError:
    tiktoken = None  # type: ignore[assignment]
    _TIKTOKEN_AVAILABLE = False

# Approximate per-message token overhead by provider.
# OpenAI chat format adds ~4 tokens per message for role markers.
_ROLE_OVERHEAD: dict[str, int] = {
    "openai": 4,
    "anthropic": 3,
    "google": 3,
    "default": 4,
}


@lru_cache(maxsize=8)
def get_encoding(name: str = "cl100k_base") -> Any:
    """Return a cached tiktoken encoding by name.

    Raises
    ------
    TokenizerError
        If tiktoken is not installed or encoding is unrecognized.
    """
    if not _TIKTOKEN_AVAILABLE:
        raise TokenizerError(
            "tiktoken is not installed. Install it with: pip install tiktoken"
        )
    try:
        return tiktoken.get_encoding(name)
    except Exception as exc:
        raise TokenizerError(f"Unknown encoding '{name}': {exc}") from exc


def count_tokens(text: str, encoding: str = "cl100k_base") -> int:
    """Count the number of tokens in *text* using the specified encoding.

    Backward-compatible free function.
    """
    enc = get_encoding(encoding)
    return len(enc.encode(text))


class Tokenizer:
    """Token counting engine with model-aware encoding selection."""

    _VALID_PROVIDERS = tuple(_ROLE_OVERHEAD.keys())

    def __init__(self, encoding: str = "cl100k_base", provider: str = "default") -> None:
        if provider not in self._VALID_PROVIDERS:
            raise ValueError(
                f"Unknown provider '{provider}'. "
                f"Valid providers: {', '.join(self._VALID_PROVIDERS)}"
            )
        self._encoding_name = encoding
        self._provider = provider
        self._enc = get_encoding(encoding)

    @property
    def encoding_name(self) -> str:
        return self._encoding_name

    def count(self, text: str) -> int:
        """Count tokens in a string."""
        return len(self._enc.encode(text))

    def count_messages(self, messages: list[Message]) -> int:
        """Count total tokens across messages including role overhead."""
        overhead = _ROLE_OVERHEAD.get(self._provider, _ROLE_OVERHEAD["default"])
        total = 0
        for msg in messages:
            total += self.count(msg.content) + overhead
        return total

    def count_file(self, prompt_file: PromptFile) -> int:
        """Count total tokens for a prompt file.

        Populates ``token_count`` on each message and ``total_tokens``
        on the prompt file.
        """
        overhead = _ROLE_OVERHEAD.get(self._provider, _ROLE_OVERHEAD["default"])
        total = 0
        for msg in prompt_file.messages:
            msg_tokens = self.count(msg.content) + overhead
            msg.token_count = msg_tokens
            total += msg_tokens
        prompt_file.total_tokens = total
        return total

    @staticmethod
    def for_model(model_name: str) -> Tokenizer:
        """Create a Tokenizer using the correct encoding for a model.

        Raises
        ------
        TokenizerError
            If the model profile is not found.
        """
        from prompttools_core.profiles import get_profile

        profile = get_profile(model_name)
        if profile is None:
            raise TokenizerError(f"Unknown model profile: '{model_name}'")
        return Tokenizer(encoding=profile.encoding, provider=profile.provider)
