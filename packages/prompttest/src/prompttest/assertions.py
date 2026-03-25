"""Assertion functions for prompt testing.

Each assertion takes a parsed PromptFile, a TestCase, and an optional model
override, then returns an AssertionResult indicating pass/fail/error.
"""

from __future__ import annotations

import re
import time
from typing import Callable, Optional

from prompttools_core import PromptFile, Tokenizer
from prompttools_core.errors import TokenizerError

from prompttest.models import AssertionResult, AssertionType, TestCase, TestStatus

# Type alias for assertion functions
AssertionFn = Callable[[PromptFile, TestCase, Optional[str]], AssertionResult]

# Registry of assertion functions keyed by AssertionType
_ASSERTIONS: dict[AssertionType, AssertionFn] = {}


def _register(assert_type: AssertionType) -> Callable[[AssertionFn], AssertionFn]:
    """Decorator to register an assertion function."""

    def decorator(fn: AssertionFn) -> AssertionFn:
        _ASSERTIONS[assert_type] = fn
        return fn

    return decorator


def run_assertion(
    prompt_file: PromptFile,
    test_case: TestCase,
    suite_model: Optional[str] = None,
) -> AssertionResult:
    """Execute a single assertion against a prompt file.

    Parameters
    ----------
    prompt_file:
        The parsed prompt to test.
    test_case:
        The test case defining the assertion.
    suite_model:
        Default model from the test suite (used if test_case.model is None).

    Returns
    -------
    AssertionResult
    """
    if test_case.skip:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.SKIPPED,
            assert_type=test_case.assert_type,
            message=test_case.skip_reason or "Test skipped",
        )

    fn = _ASSERTIONS.get(test_case.assert_type)
    if fn is None:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.ERROR,
            assert_type=test_case.assert_type,
            message=f"Unknown assertion type: {test_case.assert_type.value}",
        )

    model = test_case.model or suite_model

    start = time.perf_counter()
    try:
        result = fn(prompt_file, test_case, model)
    except Exception as exc:
        result = AssertionResult(
            test_name=test_case.name,
            status=TestStatus.ERROR,
            assert_type=test_case.assert_type,
            message=f"Assertion raised an exception: {exc}",
        )
    elapsed = (time.perf_counter() - start) * 1000
    result.duration_ms = elapsed
    return result


def _full_content(prompt_file: PromptFile) -> str:
    """Concatenate all message content from a prompt file."""
    return "\n".join(msg.content for msg in prompt_file.messages)


def _get_tokenizer(model: Optional[str]) -> Tokenizer:
    """Build a tokenizer for the given model, falling back to cl100k_base."""
    if model:
        try:
            return Tokenizer.for_model(model)
        except (TokenizerError, Exception):
            pass
    return Tokenizer()


def _count_tokens(prompt_file: PromptFile, model: Optional[str]) -> int:
    """Count total tokens in a prompt file."""
    tokenizer = _get_tokenizer(model)
    return tokenizer.count_file(prompt_file)


# ---------------------------------------------------------------------------
# Assertion implementations
# ---------------------------------------------------------------------------


@_register(AssertionType.CONTAINS)
def _assert_contains(
    prompt_file: PromptFile,
    test_case: TestCase,
    model: Optional[str],
) -> AssertionResult:
    """Assert that the prompt content contains specific text."""
    if test_case.text is None:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.ERROR,
            assert_type=AssertionType.CONTAINS,
            message="'text' parameter is required for 'contains' assertion",
        )

    content = _full_content(prompt_file)
    search_text = test_case.text

    if test_case.case_sensitive:
        found = search_text in content
    else:
        found = search_text.lower() in content.lower()

    if found:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.PASSED,
            assert_type=AssertionType.CONTAINS,
            message=f"Content contains '{search_text}'",
            expected=search_text,
        )
    return AssertionResult(
        test_name=test_case.name,
        status=TestStatus.FAILED,
        assert_type=AssertionType.CONTAINS,
        message=f"Content does not contain '{search_text}'",
        expected=search_text,
    )


@_register(AssertionType.NOT_CONTAINS)
def _assert_not_contains(
    prompt_file: PromptFile,
    test_case: TestCase,
    model: Optional[str],
) -> AssertionResult:
    """Assert that the prompt content does NOT contain specific text."""
    if test_case.text is None:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.ERROR,
            assert_type=AssertionType.NOT_CONTAINS,
            message="'text' parameter is required for 'not_contains' assertion",
        )

    content = _full_content(prompt_file)
    search_text = test_case.text

    if test_case.case_sensitive:
        found = search_text in content
    else:
        found = search_text.lower() in content.lower()

    if not found:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.PASSED,
            assert_type=AssertionType.NOT_CONTAINS,
            message=f"Content does not contain '{search_text}'",
            expected=f"not '{search_text}'",
        )
    return AssertionResult(
        test_name=test_case.name,
        status=TestStatus.FAILED,
        assert_type=AssertionType.NOT_CONTAINS,
        message=f"Content unexpectedly contains '{search_text}'",
        expected=f"not '{search_text}'",
        actual=search_text,
    )


@_register(AssertionType.HAS_ROLE)
def _assert_has_role(
    prompt_file: PromptFile,
    test_case: TestCase,
    model: Optional[str],
) -> AssertionResult:
    """Assert that the prompt has a message with a given role."""
    if test_case.role is None:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.ERROR,
            assert_type=AssertionType.HAS_ROLE,
            message="'role' parameter is required for 'has_role' assertion",
        )

    roles = [msg.role for msg in prompt_file.messages]

    if prompt_file.has_role(test_case.role):
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.PASSED,
            assert_type=AssertionType.HAS_ROLE,
            message=f"Prompt has '{test_case.role}' message",
            expected=test_case.role,
            actual=roles,
        )
    return AssertionResult(
        test_name=test_case.name,
        status=TestStatus.FAILED,
        assert_type=AssertionType.HAS_ROLE,
        message=f"Prompt has no '{test_case.role}' message (found: {roles})",
        expected=test_case.role,
        actual=roles,
    )


@_register(AssertionType.HAS_VARIABLES)
def _assert_has_variables(
    prompt_file: PromptFile,
    test_case: TestCase,
    model: Optional[str],
) -> AssertionResult:
    """Assert that the prompt uses specific template variables."""
    if not test_case.variables:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.ERROR,
            assert_type=AssertionType.HAS_VARIABLES,
            message="'variables' parameter is required for 'has_variables' assertion",
        )

    found_vars = set(prompt_file.variables.keys())
    required_vars = set(test_case.variables)
    missing = required_vars - found_vars

    if not missing:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.PASSED,
            assert_type=AssertionType.HAS_VARIABLES,
            message=f"All required variables present: {sorted(required_vars)}",
            expected=sorted(required_vars),
            actual=sorted(found_vars),
        )
    return AssertionResult(
        test_name=test_case.name,
        status=TestStatus.FAILED,
        assert_type=AssertionType.HAS_VARIABLES,
        message=f"Missing variables: {sorted(missing)} (found: {sorted(found_vars)})",
        expected=sorted(required_vars),
        actual=sorted(found_vars),
    )


@_register(AssertionType.MAX_TOKENS)
def _assert_max_tokens(
    prompt_file: PromptFile,
    test_case: TestCase,
    model: Optional[str],
) -> AssertionResult:
    """Assert that total token count is under a maximum."""
    if test_case.max is None:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.ERROR,
            assert_type=AssertionType.MAX_TOKENS,
            message="'max' parameter is required for 'max_tokens' assertion",
        )

    total = _count_tokens(prompt_file, model)
    limit = int(test_case.max)

    if total <= limit:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.PASSED,
            assert_type=AssertionType.MAX_TOKENS,
            message=f"Token count {total:,} is within limit of {limit:,}",
            expected=limit,
            actual=total,
        )
    return AssertionResult(
        test_name=test_case.name,
        status=TestStatus.FAILED,
        assert_type=AssertionType.MAX_TOKENS,
        message=f"Token count {total:,} exceeds limit of {limit:,}",
        expected=limit,
        actual=total,
    )


@_register(AssertionType.MIN_TOKENS)
def _assert_min_tokens(
    prompt_file: PromptFile,
    test_case: TestCase,
    model: Optional[str],
) -> AssertionResult:
    """Assert that total token count is above a minimum."""
    if test_case.min is None:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.ERROR,
            assert_type=AssertionType.MIN_TOKENS,
            message="'min' parameter is required for 'min_tokens' assertion",
        )

    total = _count_tokens(prompt_file, model)
    minimum = int(test_case.min)

    if total >= minimum:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.PASSED,
            assert_type=AssertionType.MIN_TOKENS,
            message=f"Token count {total:,} meets minimum of {minimum:,}",
            expected=minimum,
            actual=total,
        )
    return AssertionResult(
        test_name=test_case.name,
        status=TestStatus.FAILED,
        assert_type=AssertionType.MIN_TOKENS,
        message=f"Token count {total:,} is below minimum of {minimum:,}",
        expected=minimum,
        actual=total,
    )


@_register(AssertionType.MAX_MESSAGES)
def _assert_max_messages(
    prompt_file: PromptFile,
    test_case: TestCase,
    model: Optional[str],
) -> AssertionResult:
    """Assert that message count is under a maximum."""
    if test_case.max is None:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.ERROR,
            assert_type=AssertionType.MAX_MESSAGES,
            message="'max' parameter is required for 'max_messages' assertion",
        )

    count = len(prompt_file.messages)
    limit = int(test_case.max)

    if count <= limit:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.PASSED,
            assert_type=AssertionType.MAX_MESSAGES,
            message=f"Message count {count} is within limit of {limit}",
            expected=limit,
            actual=count,
        )
    return AssertionResult(
        test_name=test_case.name,
        status=TestStatus.FAILED,
        assert_type=AssertionType.MAX_MESSAGES,
        message=f"Message count {count} exceeds limit of {limit}",
        expected=limit,
        actual=count,
    )


@_register(AssertionType.MIN_MESSAGES)
def _assert_min_messages(
    prompt_file: PromptFile,
    test_case: TestCase,
    model: Optional[str],
) -> AssertionResult:
    """Assert that message count is above a minimum."""
    if test_case.min is None:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.ERROR,
            assert_type=AssertionType.MIN_MESSAGES,
            message="'min' parameter is required for 'min_messages' assertion",
        )

    count = len(prompt_file.messages)
    minimum = int(test_case.min)

    if count >= minimum:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.PASSED,
            assert_type=AssertionType.MIN_MESSAGES,
            message=f"Message count {count} meets minimum of {minimum}",
            expected=minimum,
            actual=count,
        )
    return AssertionResult(
        test_name=test_case.name,
        status=TestStatus.FAILED,
        assert_type=AssertionType.MIN_MESSAGES,
        message=f"Message count {count} is below minimum of {minimum}",
        expected=minimum,
        actual=count,
    )


@_register(AssertionType.MAX_COST)
def _assert_max_cost(
    prompt_file: PromptFile,
    test_case: TestCase,
    model: Optional[str],
) -> AssertionResult:
    """Assert that estimated cost is under a budget ceiling."""
    if test_case.max is None:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.ERROR,
            assert_type=AssertionType.MAX_COST,
            message="'max' parameter is required for 'max_cost' assertion",
        )

    effective_model = model
    if not effective_model:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.ERROR,
            assert_type=AssertionType.MAX_COST,
            message="'model' is required for 'max_cost' assertion (set on test or suite)",
        )

    try:
        from promptcost import estimate_file

        estimate = estimate_file(prompt_file, effective_model)
        cost = estimate.total_cost
    except Exception as exc:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.ERROR,
            assert_type=AssertionType.MAX_COST,
            message=f"Cost estimation failed: {exc}",
        )

    budget = test_case.max

    if cost <= budget:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.PASSED,
            assert_type=AssertionType.MAX_COST,
            message=f"Estimated cost ${cost:.4f} is within budget of ${budget:.4f}",
            expected=budget,
            actual=cost,
        )
    return AssertionResult(
        test_name=test_case.name,
        status=TestStatus.FAILED,
        assert_type=AssertionType.MAX_COST,
        message=f"Estimated cost ${cost:.4f} exceeds budget of ${budget:.4f}",
        expected=budget,
        actual=cost,
    )


@_register(AssertionType.VALID_FORMAT)
def _assert_valid_format(
    prompt_file: PromptFile,
    test_case: TestCase,
    model: Optional[str],
) -> AssertionResult:
    """Assert that the prompt file parsed without errors.

    Since the prompt file has already been parsed by the runner, this
    checks that parsing produced at least one message.
    """
    if prompt_file.messages:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.PASSED,
            assert_type=AssertionType.VALID_FORMAT,
            message=f"Prompt has valid format ({prompt_file.format.value}) "
            f"with {len(prompt_file.messages)} message(s)",
            actual=prompt_file.format.value,
        )
    return AssertionResult(
        test_name=test_case.name,
        status=TestStatus.FAILED,
        assert_type=AssertionType.VALID_FORMAT,
        message="Prompt parsed but contains no messages",
        actual=0,
    )


@_register(AssertionType.MATCHES_REGEX)
def _assert_matches_regex(
    prompt_file: PromptFile,
    test_case: TestCase,
    model: Optional[str],
) -> AssertionResult:
    """Assert that the prompt content matches a regex pattern."""
    if test_case.pattern is None:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.ERROR,
            assert_type=AssertionType.MATCHES_REGEX,
            message="'pattern' parameter is required for 'matches_regex' assertion",
        )

    content = _full_content(prompt_file)
    flags = 0 if test_case.case_sensitive else re.IGNORECASE

    try:
        match = re.search(test_case.pattern, content, flags)
    except re.error as exc:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.ERROR,
            assert_type=AssertionType.MATCHES_REGEX,
            message=f"Invalid regex pattern: {exc}",
        )

    if match:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.PASSED,
            assert_type=AssertionType.MATCHES_REGEX,
            message=f"Content matches pattern '{test_case.pattern}'",
            expected=test_case.pattern,
            actual=match.group(0),
        )
    return AssertionResult(
        test_name=test_case.name,
        status=TestStatus.FAILED,
        assert_type=AssertionType.MATCHES_REGEX,
        message=f"Content does not match pattern '{test_case.pattern}'",
        expected=test_case.pattern,
    )


@_register(AssertionType.NOT_MATCHES_REGEX)
def _assert_not_matches_regex(
    prompt_file: PromptFile,
    test_case: TestCase,
    model: Optional[str],
) -> AssertionResult:
    """Assert that the prompt content does NOT match a regex pattern."""
    if test_case.pattern is None:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.ERROR,
            assert_type=AssertionType.NOT_MATCHES_REGEX,
            message="'pattern' parameter is required for 'not_matches_regex' assertion",
        )

    content = _full_content(prompt_file)
    flags = 0 if test_case.case_sensitive else re.IGNORECASE

    try:
        match = re.search(test_case.pattern, content, flags)
    except re.error as exc:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.ERROR,
            assert_type=AssertionType.NOT_MATCHES_REGEX,
            message=f"Invalid regex pattern: {exc}",
        )

    if not match:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.PASSED,
            assert_type=AssertionType.NOT_MATCHES_REGEX,
            message=f"Content does not match pattern '{test_case.pattern}'",
            expected=f"not '{test_case.pattern}'",
        )
    return AssertionResult(
        test_name=test_case.name,
        status=TestStatus.FAILED,
        assert_type=AssertionType.NOT_MATCHES_REGEX,
        message=f"Content unexpectedly matches pattern '{test_case.pattern}'",
        expected=f"not '{test_case.pattern}'",
        actual=match.group(0),
    )


@_register(AssertionType.TOKEN_RATIO)
def _assert_token_ratio(
    prompt_file: PromptFile,
    test_case: TestCase,
    model: Optional[str],
) -> AssertionResult:
    """Assert that system/user token ratio is within bounds.

    The ratio is computed as system_tokens / user_tokens. If there are no
    user tokens, the ratio is treated as infinite.
    """
    if test_case.ratio_max is None:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.ERROR,
            assert_type=AssertionType.TOKEN_RATIO,
            message="'ratio_max' parameter is required for 'token_ratio' assertion",
        )

    tokenizer = _get_tokenizer(model)

    system_tokens = 0
    user_tokens = 0
    for msg in prompt_file.messages:
        count = tokenizer.count(msg.content)
        if msg.role == "system":
            system_tokens += count
        elif msg.role == "user":
            user_tokens += count

    if user_tokens == 0:
        if system_tokens == 0:
            ratio = 0.0
        else:
            return AssertionResult(
                test_name=test_case.name,
                status=TestStatus.FAILED,
                assert_type=AssertionType.TOKEN_RATIO,
                message="No user messages found; cannot compute system/user ratio",
                expected=test_case.ratio_max,
                actual="infinity (no user tokens)",
            )
    else:
        ratio = system_tokens / user_tokens

    if ratio <= test_case.ratio_max:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.PASSED,
            assert_type=AssertionType.TOKEN_RATIO,
            message=f"System/user token ratio {ratio:.2f} is within limit of "
            f"{test_case.ratio_max:.2f}",
            expected=test_case.ratio_max,
            actual=ratio,
        )
    return AssertionResult(
        test_name=test_case.name,
        status=TestStatus.FAILED,
        assert_type=AssertionType.TOKEN_RATIO,
        message=f"System/user token ratio {ratio:.2f} exceeds limit of "
        f"{test_case.ratio_max:.2f}",
        expected=test_case.ratio_max,
        actual=ratio,
    )


@_register(AssertionType.HAS_METADATA)
def _assert_has_metadata(
    prompt_file: PromptFile,
    test_case: TestCase,
    model: Optional[str],
) -> AssertionResult:
    """Assert that the prompt has specific metadata keys."""
    if not test_case.keys:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.ERROR,
            assert_type=AssertionType.HAS_METADATA,
            message="'keys' parameter is required for 'has_metadata' assertion",
        )

    existing_keys = set(prompt_file.metadata.keys())
    required_keys = set(test_case.keys)
    missing = required_keys - existing_keys

    if not missing:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.PASSED,
            assert_type=AssertionType.HAS_METADATA,
            message=f"All required metadata keys present: {sorted(required_keys)}",
            expected=sorted(required_keys),
            actual=sorted(existing_keys),
        )
    return AssertionResult(
        test_name=test_case.name,
        status=TestStatus.FAILED,
        assert_type=AssertionType.HAS_METADATA,
        message=f"Missing metadata keys: {sorted(missing)} "
        f"(found: {sorted(existing_keys)})",
        expected=sorted(required_keys),
        actual=sorted(existing_keys),
    )


@_register(AssertionType.CONTENT_HASH)
def _assert_content_hash(
    prompt_file: PromptFile,
    test_case: TestCase,
    model: Optional[str],
) -> AssertionResult:
    """Assert that the prompt content hash matches an expected value.

    This is a regression guard: if the prompt changes unexpectedly, the
    hash will differ.
    """
    if test_case.hash is None:
        # No expected hash provided: report the current hash for recording
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.PASSED,
            assert_type=AssertionType.CONTENT_HASH,
            message=f"Current content hash: {prompt_file.content_hash} "
            f"(no expected hash specified; recording)",
            actual=prompt_file.content_hash,
        )

    if prompt_file.content_hash == test_case.hash:
        return AssertionResult(
            test_name=test_case.name,
            status=TestStatus.PASSED,
            assert_type=AssertionType.CONTENT_HASH,
            message="Content hash matches expected value",
            expected=test_case.hash,
            actual=prompt_file.content_hash,
        )
    return AssertionResult(
        test_name=test_case.name,
        status=TestStatus.FAILED,
        assert_type=AssertionType.CONTENT_HASH,
        message="Content hash mismatch (prompt has changed)",
        expected=test_case.hash,
        actual=prompt_file.content_hash,
    )
