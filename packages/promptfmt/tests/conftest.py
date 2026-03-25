"""Shared fixtures for promptfmt tests."""

import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir():
    """Path to test fixtures (shared with prompttools-core)."""
    return Path(__file__).parent / "../../prompttools-core/tests/fixtures"
