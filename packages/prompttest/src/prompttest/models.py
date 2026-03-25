"""Data models for prompttest.

Defines test cases, test suites, assertion results, and test reports
using Pydantic v2 models.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class AssertionType(str, Enum):
    """Supported assertion types for prompt tests."""

    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    HAS_ROLE = "has_role"
    HAS_VARIABLES = "has_variables"
    MAX_TOKENS = "max_tokens"
    MIN_TOKENS = "min_tokens"
    MAX_MESSAGES = "max_messages"
    MIN_MESSAGES = "min_messages"
    MAX_COST = "max_cost"
    VALID_FORMAT = "valid_format"
    MATCHES_REGEX = "matches_regex"
    NOT_MATCHES_REGEX = "not_matches_regex"
    TOKEN_RATIO = "token_ratio"
    HAS_METADATA = "has_metadata"
    CONTENT_HASH = "content_hash"


class TestStatus(str, Enum):
    """Outcome of a single test case."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class TestCase(BaseModel):
    """A single test assertion within a test suite.

    Parsed from a YAML test file entry. The ``assert`` field maps to
    ``assert_type`` via the Pydantic alias.
    """

    model_config = {"populate_by_name": True}

    name: str
    assert_type: AssertionType = Field(alias="assert")

    # Assertion-specific parameters
    text: Optional[str] = None
    role: Optional[str] = None
    variables: Optional[list[str]] = None
    max: Optional[float] = None
    min: Optional[float] = None
    pattern: Optional[str] = None
    model: Optional[str] = None
    keys: Optional[list[str]] = None
    hash: Optional[str] = None
    ratio_max: Optional[float] = None
    case_sensitive: bool = False
    skip: bool = False
    skip_reason: Optional[str] = None

    @model_validator(mode="after")
    def _validate_bounds(self) -> "TestCase":
        """Ensure max/min/ratio_max values are positive when provided."""
        if self.max is not None and self.max < 0:
            raise ValueError(f"'max' must be non-negative, got {self.max}")
        if self.min is not None and self.min < 0:
            raise ValueError(f"'min' must be non-negative, got {self.min}")
        if self.ratio_max is not None and self.ratio_max < 0:
            raise ValueError(f"'ratio_max' must be non-negative, got {self.ratio_max}")
        return self


class AssertionResult(BaseModel):
    """Result of running a single test assertion."""

    test_name: str
    status: TestStatus
    assert_type: AssertionType
    message: str
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    duration_ms: float = 0.0


class TestSuite(BaseModel):
    """A collection of test cases targeting a single prompt file.

    Parsed from a YAML test file.
    """

    name: str
    prompt_path: Path
    model: Optional[str] = None
    tests: list[TestCase]


class TestReport(BaseModel):
    """Aggregated results from running one or more test suites."""

    suites: list[dict] = Field(default_factory=list)
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    duration_ms: float = 0.0
