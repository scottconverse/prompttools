"""Shared fixtures for promptdiff tests."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from prompttools_core.models import Message, PromptFile

from promptdiff.models import (
    BreakingChange,
    ChangeStatus,
    MessageDiff,
    MetadataDiff,
    PromptDiff,
    TokenDelta,
    VariableDiff,
)


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def old_prompt_file(tmp_path):
    """Create a simple old prompt YAML file."""
    content = textwrap.dedent("""\
        model: gpt-4
        defaults:
          name: World
          tone: friendly
        messages:
          - role: system
            content: "You are a helpful assistant. Be {{tone}}."
          - role: user
            content: "Hello {{name}}, help me with my task."
    """)
    p = tmp_path / "old_prompt.yaml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def new_prompt_file(tmp_path):
    """Create a modified new prompt YAML file."""
    content = textwrap.dedent("""\
        model: gpt-4o
        defaults:
          name: World
        messages:
          - role: system
            content: "You are a helpful AI assistant. Be concise and accurate."
          - role: user
            content: "Hello {{name}}, help me with my task in {{language}}."
    """)
    p = tmp_path / "new_prompt.yaml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def identical_prompt_file(tmp_path):
    """Create a prompt file identical to old_prompt_file."""
    content = textwrap.dedent("""\
        model: gpt-4
        defaults:
          name: World
          tone: friendly
        messages:
          - role: system
            content: "You are a helpful assistant. Be {{tone}}."
          - role: user
            content: "Hello {{name}}, help me with my task."
    """)
    p = tmp_path / "identical.yaml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def simple_old_msg():
    """A simple old message list."""
    return [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Hello world."),
    ]


@pytest.fixture
def simple_new_msg():
    """A modified new message list."""
    return [
        Message(role="system", content="You are a helpful AI assistant."),
        Message(role="user", content="Hello world."),
        Message(role="assistant", content="How can I help?"),
    ]


@pytest.fixture
def sample_diff():
    """A pre-built PromptDiff for reporter tests."""
    return PromptDiff(
        file_path=Path("test_prompt.yaml"),
        old_hash="aaa111",
        new_hash="bbb222",
        message_diffs=[
            MessageDiff(
                status=ChangeStatus.MODIFIED,
                role="system",
                old_content="You are a helper.",
                new_content="You are a helpful AI.",
                content_diff="--- old\n+++ new\n-You are a helper.\n+You are a helpful AI.",
                token_delta=2,
                changes=["System message content modified"],
            ),
            MessageDiff(
                status=ChangeStatus.UNCHANGED,
                role="user",
                old_content="Hello",
                new_content="Hello",
            ),
            MessageDiff(
                status=ChangeStatus.ADDED,
                role="assistant",
                new_content="How can I help?",
                token_delta=5,
                changes=["Added assistant message (5 tokens)"],
            ),
        ],
        variable_diffs=[
            VariableDiff(
                name="name",
                status=ChangeStatus.UNCHANGED,
                old_default="World",
                new_default="World",
            ),
            VariableDiff(
                name="tone",
                status=ChangeStatus.REMOVED,
                old_default="friendly",
                is_breaking=True,
            ),
            VariableDiff(
                name="language",
                status=ChangeStatus.ADDED,
                new_default=None,
                is_breaking=True,
            ),
        ],
        metadata_diffs=[
            MetadataDiff(
                key="model",
                status=ChangeStatus.MODIFIED,
                old_value="gpt-4",
                new_value="gpt-4o",
            ),
        ],
        token_delta=TokenDelta(
            old_total=100,
            new_total=115,
            delta=15,
            percent_change=15.0,
        ),
        breaking_changes=[
            BreakingChange(
                category="variable",
                description="Variable 'tone' was removed",
                severity="high",
            ),
            BreakingChange(
                category="variable",
                description="New required variable 'language' added without a default value",
                severity="high",
            ),
            BreakingChange(
                category="model",
                description="Model changed from 'gpt-4' to 'gpt-4o'",
                severity="medium",
            ),
        ],
    )
