"""Shared fixtures for prompttest tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from prompttools_core import Message, PromptFile, PromptFormat


@pytest.fixture
def simple_prompt() -> PromptFile:
    """A simple prompt with system and user messages."""
    return PromptFile(
        path=Path("prompts/greeting.yaml"),
        format=PromptFormat.YAML,
        raw_content=(
            "messages:\n"
            "  - role: system\n"
            "    content: You are a helpful assistant. Greet the user warmly.\n"
            "  - role: user\n"
            "    content: Hello, my name is {{user_name}}.\n"
        ),
        messages=[
            Message(
                role="system",
                content="You are a helpful assistant. Greet the user warmly.",
                line_start=2,
            ),
            Message(
                role="user",
                content="Hello, my name is {{user_name}}.",
                line_start=4,
            ),
        ],
        variables={"user_name": "double_brace"},
        metadata={"version": "1.0", "author": "test"},
    )


@pytest.fixture
def multi_message_prompt() -> PromptFile:
    """A prompt with multiple messages including assistant turns."""
    return PromptFile(
        path=Path("prompts/chat.yaml"),
        format=PromptFormat.YAML,
        raw_content=(
            "messages:\n"
            "  - role: system\n"
            "    content: You are a coding assistant.\n"
            "  - role: user\n"
            "    content: Write a function in {{language}}.\n"
            "  - role: assistant\n"
            "    content: Sure, here is a function.\n"
            "  - role: user\n"
            "    content: Now add error handling.\n"
        ),
        messages=[
            Message(role="system", content="You are a coding assistant."),
            Message(
                role="user", content="Write a function in {{language}}."
            ),
            Message(
                role="assistant", content="Sure, here is a function."
            ),
            Message(role="user", content="Now add error handling."),
        ],
        variables={"language": "double_brace"},
        metadata={},
    )


@pytest.fixture
def minimal_prompt() -> PromptFile:
    """A minimal prompt with only a user message."""
    return PromptFile(
        path=Path("prompts/minimal.yaml"),
        format=PromptFormat.YAML,
        raw_content="messages:\n  - role: user\n    content: Hello\n",
        messages=[Message(role="user", content="Hello")],
    )


@pytest.fixture
def empty_prompt() -> PromptFile:
    """A prompt file with no messages (parse edge case)."""
    return PromptFile(
        path=Path("prompts/empty.yaml"),
        format=PromptFormat.YAML,
        raw_content="messages: []\n",
        messages=[],
    )


@pytest.fixture
def tmp_prompt_file(tmp_path: Path) -> Path:
    """Create a real prompt file on disk for runner tests."""
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    prompt_file = prompt_dir / "greeting.yaml"
    prompt_file.write_text(
        "messages:\n"
        "  - role: system\n"
        "    content: You are a helpful assistant. Greet the user.\n"
        "  - role: user\n"
        "    content: Hello, my name is {{user_name}}.\n",
        encoding="utf-8",
    )
    return prompt_file


@pytest.fixture
def tmp_test_file(tmp_path: Path, tmp_prompt_file: Path) -> Path:
    """Create a real YAML test file on disk."""
    test_file = tmp_path / "test_greeting.yaml"
    # Use relative path from test file to prompt file
    rel_prompt = tmp_prompt_file.relative_to(tmp_path)
    test_file.write_text(
        f"suite: greeting-tests\n"
        f"prompt: {rel_prompt}\n"
        f"tests:\n"
        f"  - name: has-system-message\n"
        f"    assert: has_role\n"
        f"    role: system\n"
        f"  - name: format-is-valid\n"
        f"    assert: valid_format\n"
        f"  - name: contains-greet\n"
        f"    assert: contains\n"
        f'    text: "greet the user"\n',
        encoding="utf-8",
    )
    return test_file
