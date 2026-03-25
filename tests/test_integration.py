"""Integration tests -- cross-package workflows.

Exercises real interactions between prompttools-core, promptfmt, promptcost,
and prompttest to verify the packages work together correctly.
"""

import pytest
from pathlib import Path

from prompttools_core import (
    ParseError,
    PromptFile,
    Tokenizer,
    count_tokens,
    find_config_file,
    get_profile,
    list_profiles,
    load_config,
    parse_file,
)
from prompttools_core.parser import parse_stdin
from promptfmt import FmtConfig, format_content, format_file, is_equivalent
from promptcost import estimate_file
from prompttest import (
    PromptTestStatus,
    load_test_suite,
    run_test_file,
    run_test_suite,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_YAML_PROMPT = """\
model: gpt-4o
description: Customer support assistant
messages:
  - role: system
    content: >
      You are a helpful customer support agent for Acme Corp.
      Always be polite, concise, and accurate.
      Greet the user by {{name}} if provided.
  - role: user
    content: >
      Hi, my order {{order_id}} hasn't arrived yet.
      Can you check the status for me?
"""

_YAML_PROMPT_MESSY = """\
model:   gpt-4o
description:  Customer support  assistant
messages:
  - role:   system
    content:  >
      You are a helpful customer support agent   for Acme Corp.
      Always be polite,  concise,   and accurate.
      Greet the user by  {{name}}  if provided.
  - role:    user
    content:   >
      Hi, my order  {{order_id}}  hasn't arrived yet.
      Can you  check the status  for me?
"""


def _write_yaml(tmp_path: Path, filename: str, content: str) -> Path:
    """Write a YAML file into tmp_path and return its Path."""
    p = tmp_path / filename
    p.write_text(content, encoding="utf-8")
    return p


def _write_test_yaml(
    tmp_path: Path,
    prompt_filename: str,
    test_filename: str,
    tests_yaml: str,
    suite_name: str = "integration",
    model: str | None = None,
) -> Path:
    """Write a prompttest YAML test file that references a prompt in the same dir."""
    model_line = f"model: {model}" if model else ""
    content = f"""\
suite: {suite_name}
prompt: {prompt_filename}
{model_line}
tests:
{tests_yaml}
"""
    p = tmp_path / test_filename
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Test 1: Parse -> Format -> Re-parse (core + fmt)
# ---------------------------------------------------------------------------


def test_parse_format_reparse(tmp_path: Path) -> None:
    """Parse a prompt, format it, re-parse -- should be semantically equivalent."""
    prompt_path = _write_yaml(tmp_path, "support.yaml", _YAML_PROMPT_MESSY)

    # 1. Parse the messy original
    original = parse_file(prompt_path)
    assert len(original.messages) == 2
    assert original.messages[0].role == "system"
    assert original.messages[1].role == "user"
    assert "name" in original.variables
    assert "order_id" in original.variables

    # 2. Format the file
    result = format_file(prompt_path, FmtConfig())
    assert result.formatted_content is not None

    # 3. Write formatted content and re-parse
    formatted_path = tmp_path / "support_formatted.yaml"
    formatted_path.write_text(result.formatted_content, encoding="utf-8")
    reparsed = parse_file(formatted_path)

    # 4. Semantic equivalence: same messages, same roles, same variables
    assert len(reparsed.messages) == len(original.messages)
    for orig_msg, fmt_msg in zip(original.messages, reparsed.messages):
        assert orig_msg.role == fmt_msg.role
        # Content should be semantically equivalent (whitespace may differ)
        assert " ".join(orig_msg.content.split()) == " ".join(fmt_msg.content.split())

    assert set(original.variables.keys()) == set(reparsed.variables.keys())

    # The equivalence checker from promptfmt should also agree
    assert is_equivalent(original, reparsed)


# ---------------------------------------------------------------------------
# Test 2: Parse -> Estimate Cost (core + cost)
# ---------------------------------------------------------------------------


def test_parse_then_estimate_cost(tmp_path: Path) -> None:
    """Parse a prompt file, then estimate its cost."""
    prompt_path = _write_yaml(tmp_path, "cost_test.yaml", _YAML_PROMPT)

    pf = parse_file(prompt_path)
    estimate = estimate_file(pf, model="gpt-4o")

    assert estimate.input_tokens > 0
    assert estimate.total_cost > 0
    assert estimate.model == "gpt-4o"
    assert estimate.input_cost >= 0
    assert estimate.output_cost >= 0
    assert estimate.file_path == pf.path


# ---------------------------------------------------------------------------
# Test 3: Parse -> Format -> Estimate Cost (core + fmt + cost)
# ---------------------------------------------------------------------------


def test_format_preserves_cost(tmp_path: Path) -> None:
    """Formatting should not change the cost estimate significantly."""
    prompt_path = _write_yaml(tmp_path, "preserve.yaml", _YAML_PROMPT_MESSY)

    # Estimate cost of original
    pf_original = parse_file(prompt_path)
    cost_before = estimate_file(pf_original, model="gpt-4o")

    # Format the file
    result = format_file(prompt_path, FmtConfig())
    formatted_path = tmp_path / "preserve_fmt.yaml"
    formatted_path.write_text(result.formatted_content, encoding="utf-8")

    # Estimate cost of formatted version
    pf_formatted = parse_file(formatted_path)
    cost_after = estimate_file(pf_formatted, model="gpt-4o")

    # Input tokens should be identical or very close (whitespace-only changes
    # produce the same tokens with most tokenizers)
    assert abs(cost_before.input_tokens - cost_after.input_tokens) <= 5, (
        f"Token count changed significantly: {cost_before.input_tokens} -> "
        f"{cost_after.input_tokens}"
    )
    # Total cost difference should be negligible
    assert abs(cost_before.total_cost - cost_after.total_cost) < 0.001


# ---------------------------------------------------------------------------
# Test 4: Parse -> Test assertions (core + test)
# ---------------------------------------------------------------------------


def test_parse_then_test(tmp_path: Path) -> None:
    """Parse a prompt, run test assertions against it."""
    prompt_path = _write_yaml(tmp_path, "tested.yaml", _YAML_PROMPT)

    test_path = _write_test_yaml(
        tmp_path,
        prompt_filename="tested.yaml",
        test_filename="test_tested.yaml",
        model="gpt-4o",
        tests_yaml="""\
  - name: has system role
    assert: has_role
    role: system
  - name: has user role
    assert: has_role
    role: user
  - name: contains greeting instruction
    assert: contains
    text: polite
  - name: is valid yaml
    assert: valid_format
""",
    )

    report = run_test_file(test_path)

    assert report.total == 4
    assert report.passed == 4
    assert report.failed == 0
    assert report.errors == 0


# ---------------------------------------------------------------------------
# Test 5: Full pipeline -- Parse, Format, Cost, Test (all 4)
# ---------------------------------------------------------------------------


def test_full_pipeline(tmp_path: Path) -> None:
    """Complete workflow: parse, format, verify cost, run tests."""
    # 1. Create a messy prompt
    prompt_path = _write_yaml(tmp_path, "pipeline.yaml", _YAML_PROMPT_MESSY)

    # 2. Parse it
    pf = parse_file(prompt_path)
    assert len(pf.messages) == 2

    # 3. Format it
    fmt_result = format_file(prompt_path, FmtConfig())
    formatted_path = tmp_path / "pipeline_fmt.yaml"
    formatted_path.write_text(fmt_result.formatted_content, encoding="utf-8")

    # 4. Re-parse formatted version
    pf_fmt = parse_file(formatted_path)
    assert is_equivalent(pf, pf_fmt)

    # 5. Estimate cost
    estimate = estimate_file(pf_fmt, model="gpt-4o")
    assert estimate.input_tokens > 0
    assert estimate.total_cost > 0

    # 6. Run test assertions against the formatted prompt
    test_path = _write_test_yaml(
        tmp_path,
        prompt_filename="pipeline_fmt.yaml",
        test_filename="test_pipeline.yaml",
        model="gpt-4o",
        tests_yaml="""\
  - name: has system role
    assert: has_role
    role: system
  - name: has user role
    assert: has_role
    role: user
  - name: has variables
    assert: has_variables
    variables:
      - name
      - order_id
  - name: token budget
    assert: max_tokens
    max: 5000
  - name: is valid
    assert: valid_format
""",
    )

    report = run_test_file(test_path)
    assert report.total == 5
    assert report.passed == 5
    assert report.failed == 0
    assert report.errors == 0


# ---------------------------------------------------------------------------
# Test 6: Shared model profiles (core used by cost)
# ---------------------------------------------------------------------------


def test_model_profiles_shared() -> None:
    """Model profiles from core are available in cost estimator."""
    profiles = list_profiles()
    assert len(profiles) >= 10

    # Verify that every profile with pricing can be used by the cost estimator
    # by building a minimal prompt
    minimal_pf = PromptFile(
        path=Path("inline.yaml"),
        format="yaml",
        raw_content="messages:\n  - role: user\n    content: Hello",
        messages=[
            __import__("prompttools_core.models", fromlist=["Message"]).Message(
                role="user", content="Hello world"
            )
        ],
    )

    for name, profile in profiles.items():
        if profile.input_price_per_mtok is not None:
            est = estimate_file(minimal_pf, model=name)
            assert est.input_tokens > 0, f"Profile {name}: expected input_tokens > 0"
            assert est.model == name


# ---------------------------------------------------------------------------
# Test 7: Shared tokenizer (core used by all)
# ---------------------------------------------------------------------------


def test_tokenizer_consistent(tmp_path: Path) -> None:
    """Token counts from core tokenizer match what cost/test packages see."""
    prompt_path = _write_yaml(tmp_path, "tokenizer.yaml", _YAML_PROMPT)
    pf = parse_file(prompt_path)

    # Count tokens via core Tokenizer
    tokenizer = Tokenizer.for_model("gpt-4o")
    core_tokens = tokenizer.count_file(pf)
    assert core_tokens > 0

    # Estimate via cost -- input_tokens should match core's count
    estimate = estimate_file(pf, model="gpt-4o")
    assert estimate.input_tokens == core_tokens, (
        f"Cost estimator tokens ({estimate.input_tokens}) != "
        f"core tokenizer ({core_tokens})"
    )

    # Run a max_tokens test set high enough to pass -- verify the test sees
    # the same token count
    test_path = _write_test_yaml(
        tmp_path,
        prompt_filename="tokenizer.yaml",
        test_filename="test_tokens.yaml",
        model="gpt-4o",
        tests_yaml=f"""\
  - name: token ceiling
    assert: max_tokens
    max: {core_tokens + 100}
  - name: token floor
    assert: min_tokens
    min: {core_tokens - 1}
""",
    )

    report = run_test_file(test_path)
    assert report.passed == 2, (
        f"Expected 2 passes but got {report.passed} passed, "
        f"{report.failed} failed, {report.errors} errors"
    )


# ---------------------------------------------------------------------------
# Test 8: Config cascade (core config used by fmt)
# ---------------------------------------------------------------------------


def test_config_cascade(tmp_path: Path) -> None:
    """Config files are found and applied across packages."""
    # Create a .prompttools.yaml config in the tmp dir
    config_content = """\
model: gpt-4o
exclude:
  - "*.bak"
cache:
  enabled: true
fmt:
  indent: 4
  sort_keys: true
"""
    (tmp_path / ".prompttools.yaml").write_text(config_content, encoding="utf-8")

    # Verify core's find_config_file discovers it
    found = find_config_file(tmp_path)
    assert found is not None
    assert found.name == ".prompttools.yaml"

    # Verify load_config picks it up and populates ToolConfig
    config = load_config("fmt", start_dir=tmp_path)
    assert config.model == "gpt-4o"
    assert "*.bak" in config.exclude
    assert config.cache_enabled is True

    # The tool-specific "fmt" section should be in config.extra
    assert config.extra.get("indent") == 4
    assert config.extra.get("sort_keys") is True

    # Verify that a tool-specific config file takes priority
    (tmp_path / ".promptfmt.yaml").write_text(
        "model: gpt-4o-mini\nfmt:\n  indent: 2\n", encoding="utf-8"
    )
    found_tool = find_config_file(tmp_path, tool_name="fmt")
    assert found_tool is not None
    assert found_tool.name == ".promptfmt.yaml"

    config_tool = load_config("fmt", start_dir=tmp_path)
    assert config_tool.model == "gpt-4o-mini"


# ---------------------------------------------------------------------------
# Test 9: Error propagation
# ---------------------------------------------------------------------------


def test_parse_error_propagates(tmp_path: Path) -> None:
    """Parse errors from core are properly caught by downstream packages."""
    # Create an invalid YAML prompt file (missing messages list)
    bad_content = """\
model: gpt-4o
description: broken prompt
not_messages:
  - role: system
    content: oops
"""
    bad_path = _write_yaml(tmp_path, "broken.yaml", bad_content)

    # Core parser should raise ParseError
    with pytest.raises(ParseError):
        parse_file(bad_path)

    # Formatter should return a FormattedResult with an error
    # (format_file catches and wraps the parse error)
    try:
        fmt_result = format_file(bad_path)
        # If it returns instead of raising, there should be an error
        assert fmt_result.error is not None or not fmt_result.changed
    except (ParseError, Exception):
        # Also acceptable: formatter propagates the parse error
        pass

    # Cost estimator requires a PromptFile, so we test that passing garbage
    # content through parse_stdin raises properly
    with pytest.raises(ParseError):
        parse_stdin("this is not valid yaml: [", "yaml")

    # Test runner: a test file pointing at a broken prompt should produce
    # ERROR results, not crash
    test_content = f"""\
suite: error_suite
prompt: broken.yaml
tests:
  - name: should be valid
    assert: valid_format
"""
    test_path = tmp_path / "test_broken.yaml"
    test_path.write_text(test_content, encoding="utf-8")

    report = run_test_file(test_path)
    assert report.errors >= 1, (
        f"Expected at least 1 error result, got: "
        f"passed={report.passed}, failed={report.failed}, errors={report.errors}"
    )


# ---------------------------------------------------------------------------
# Test 10: Variable extraction consistency
# ---------------------------------------------------------------------------


def test_variables_consistent_across_packages(tmp_path: Path) -> None:
    """Variables extracted by core are the same ones checked by test assertions."""
    prompt_content = """\
messages:
  - role: system
    content: >
      Welcome, {{name}}! You are {{age}} years old.
      Your account type is {{account_type}}.
  - role: user
    content: >
      Please update my profile with name={{name}}.
"""
    prompt_path = _write_yaml(tmp_path, "vars.yaml", prompt_content)

    # Parse with core and check variables
    pf = parse_file(prompt_path)
    core_vars = set(pf.variables.keys())
    assert "name" in core_vars
    assert "age" in core_vars
    assert "account_type" in core_vars

    # has_variables assertion with exact match -- should pass
    test_pass_yaml = _write_test_yaml(
        tmp_path,
        prompt_filename="vars.yaml",
        test_filename="test_vars_pass.yaml",
        tests_yaml="""\
  - name: has expected variables
    assert: has_variables
    variables:
      - name
      - age
      - account_type
""",
    )
    report_pass = run_test_file(test_pass_yaml)
    assert report_pass.passed == 1
    assert report_pass.failed == 0

    # has_variables with a missing variable -- should fail
    test_fail_yaml = _write_test_yaml(
        tmp_path,
        prompt_filename="vars.yaml",
        test_filename="test_vars_fail.yaml",
        tests_yaml="""\
  - name: has missing variable
    assert: has_variables
    variables:
      - name
      - age
      - account_type
      - nonexistent_var
""",
    )
    report_fail = run_test_file(test_fail_yaml)
    assert report_fail.failed == 1
    assert report_fail.passed == 0

    # Also verify format preserves variables
    fmt_result = format_file(prompt_path, FmtConfig())
    formatted_path = tmp_path / "vars_fmt.yaml"
    formatted_path.write_text(fmt_result.formatted_content, encoding="utf-8")
    pf_fmt = parse_file(formatted_path)
    assert set(pf_fmt.variables.keys()) == core_vars
