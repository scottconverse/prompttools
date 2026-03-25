"""Shared fixtures for promptcost tests."""

import pytest
from prompttools_core import Message, PromptFile, PromptFormat
from pathlib import Path


@pytest.fixture
def simple_prompt():
    """A simple prompt file for testing."""
    return PromptFile(
        path=Path("test.yaml"),
        format=PromptFormat.YAML,
        raw_content="messages:\n  - role: user\n    content: Hello world\n",
        messages=[Message(role="user", content="Hello world", line_start=2)],
    )


@pytest.fixture
def detailed_prompt():
    """A prompt with structured output request."""
    content = (
        "You are a research analyst. Research the given topic and "
        "provide a comprehensive JSON report with citations and sources."
    )
    return PromptFile(
        path=Path("research.yaml"),
        format=PromptFormat.YAML,
        raw_content=f"messages:\n  - role: system\n    content: {content}\n",
        messages=[Message(role="system", content=content, line_start=2)],
    )
