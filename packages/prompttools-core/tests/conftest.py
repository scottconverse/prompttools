import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def clean_yaml(fixtures_dir):
    return fixtures_dir / "clean.yaml"


@pytest.fixture
def clean_json(fixtures_dir):
    return fixtures_dir / "clean.json"


@pytest.fixture
def clean_txt(fixtures_dir):
    return fixtures_dir / "clean.txt"


@pytest.fixture
def with_variables(fixtures_dir):
    return fixtures_dir / "with_variables.yaml"
