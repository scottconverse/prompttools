"""Shared pytest fixtures for promptlint tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from promptlint.core.parser import parse_file, parse_pipeline_manifest
from promptlint.models import LintConfig, PromptFile, PromptPipeline

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def sample_text_prompt() -> PromptFile:
    """Clean plain-text prompt that should pass all rules."""
    return parse_file(FIXTURES_DIR / "clean.txt")


@pytest.fixture()
def sample_yaml_prompt() -> PromptFile:
    """Clean YAML prompt (system + user) that should pass all rules."""
    return parse_file(FIXTURES_DIR / "clean.yaml")


@pytest.fixture()
def sample_json_prompt() -> PromptFile:
    """Clean JSON prompt in OpenAI chat format that should pass all rules."""
    return parse_file(FIXTURES_DIR / "clean.json")


@pytest.fixture()
def sample_prompt_with_injection() -> PromptFile:
    """Prompt containing multiple injection attack vectors."""
    return parse_file(FIXTURES_DIR / "injection.yaml")


@pytest.fixture()
def sample_prompt_with_variables() -> PromptFile:
    """Prompt with variable issues: undefined, unused, and mixed formats."""
    return parse_file(FIXTURES_DIR / "with_variables.yaml")


@pytest.fixture()
def sample_prompt_with_pii() -> PromptFile:
    """Prompt containing PII (SSN, email, phone, credit card) and API keys."""
    return parse_file(FIXTURES_DIR / "pii.yaml")


@pytest.fixture()
def sample_pipeline() -> PromptPipeline:
    """Two-stage research-to-report pipeline for pipeline rule testing."""
    return parse_pipeline_manifest(
        FIXTURES_DIR / "pipeline" / ".promptlint-pipeline.yaml"
    )


@pytest.fixture()
def sample_violations_prompt() -> PromptFile:
    """Prompt designed to trigger multiple violations (PL010-PL013, PL050, PL051, PL070, PL072)."""
    return parse_file(FIXTURES_DIR / "violations.yaml")


@pytest.fixture()
def default_config() -> LintConfig:
    """LintConfig with all default values."""
    return LintConfig()
