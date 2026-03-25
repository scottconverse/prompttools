# prompttest

Test framework for LLM prompt files.

[![PyPI](https://img.shields.io/badge/PyPI-v1.0.0-blue)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]()
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)]()

## What It Does

`prompttest` is a test framework for LLM prompt files, similar to what Jest or pytest does for application code. You write test suites in YAML that assert properties of your prompt files -- content, structure, token counts, cost limits, and more. Tests run in CI to catch prompt regressions.

## Installation

```bash
pip install prompttest
```

**Dependencies:** prompttools-core >= 1.0, promptcost >= 1.0, typer >= 0.12, pyyaml >= 6.0, rich >= 13.0

## CLI Commands

### `prompttest run`

Run prompt tests from a file or directory.

```bash
# Run a single test file
prompttest run tests/test_greeting.yaml

# Run all test files in a directory
prompttest run tests/

# Run with custom glob pattern
prompttest run tests/ --pattern "check_*.yaml"

# Stop on first failure
prompttest run tests/ --fail-fast

# JSON output
prompttest run tests/ --format json

# JUnit XML output (for CI)
prompttest run tests/ --format junit

# Verbose output
prompttest run tests/ -v
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--format`, `-f` | `text` | Output format: `text`, `json`, `junit` |
| `--model`, `-m` | none | Override model for cost/token assertions |
| `--fail-fast` | `false` | Stop after first failure |
| `--verbose`, `-v` | `false` | Show detailed output for all tests |
| `--pattern`, `-p` | `test_*.yaml` | Glob pattern for test file discovery |

### `prompttest init`

Create an example test file in the current directory.

```bash
prompttest init
```

This creates `test_example.yaml` with sample test cases you can adapt to your project.

## Test File Format

Test files are YAML with this structure:

```yaml
suite: my-test-suite          # Suite name (optional, defaults to filename)
prompt: prompts/greeting.yaml  # Path to the prompt file (relative to test file)
model: gpt-4o                 # Default model for cost/token assertions (optional)

tests:
  - name: test-name           # Unique test name
    assert: assertion_type    # One of the 15 assertion types below
    # ... assertion-specific parameters
```

The `prompt` path is resolved relative to the test file's directory.

## Assertion Types

prompttest supports 15 assertion types:

### Content Assertions

#### `contains`

Assert that prompt content contains specific text.

```yaml
- name: has-greeting-instruction
  assert: contains
  text: "greet the user"
  case_sensitive: false    # optional, default: false
```

#### `not_contains`

Assert that prompt content does NOT contain specific text.

```yaml
- name: no-injection-risk
  assert: not_contains
  text: "ignore previous instructions"
```

#### `matches_regex`

Assert that prompt content matches a regular expression.

```yaml
- name: has-version-tag
  assert: matches_regex
  pattern: "v\\d+\\.\\d+"
  case_sensitive: false
```

#### `not_matches_regex`

Assert that prompt content does NOT match a regular expression.

```yaml
- name: no-hardcoded-urls
  assert: not_matches_regex
  pattern: "https?://api\\.example\\.com"
```

### Structure Assertions

#### `has_role`

Assert that the prompt has a message with a given role.

```yaml
- name: has-system-message
  assert: has_role
  role: system
```

#### `has_variables`

Assert that the prompt uses specific template variables.

```yaml
- name: required-variables
  assert: has_variables
  variables:
    - user_name
    - context
```

#### `has_metadata`

Assert that the prompt has specific metadata keys.

```yaml
- name: has-required-metadata
  assert: has_metadata
  keys:
    - model
    - description
```

#### `valid_format`

Assert that the prompt file parsed without errors and contains at least one message.

```yaml
- name: parseable-prompt
  assert: valid_format
```

### Token/Size Assertions

#### `max_tokens`

Assert that total token count is under a maximum.

```yaml
- name: within-context-window
  assert: max_tokens
  max: 4096
```

#### `min_tokens`

Assert that total token count is above a minimum.

```yaml
- name: not-too-short
  assert: min_tokens
  min: 50
```

#### `max_messages`

Assert that message count is under a maximum.

```yaml
- name: reasonable-conversation
  assert: max_messages
  max: 10
```

#### `min_messages`

Assert that message count is above a minimum.

```yaml
- name: has-enough-context
  assert: min_messages
  min: 2
```

#### `token_ratio`

Assert that the system/user token ratio is within bounds.

```yaml
- name: balanced-prompt
  assert: token_ratio
  ratio_max: 5.0
```

The ratio is computed as system_tokens / user_tokens.

### Cost Assertions

#### `max_cost`

Assert that the estimated cost per invocation is under a budget ceiling. Requires a model (set on the test or the suite).

```yaml
- name: cost-under-budget
  assert: max_cost
  max: 0.05
  model: gpt-4o      # optional if set on suite
```

### Regression Assertions

#### `content_hash`

Assert that the prompt content SHA256 hash matches an expected value. Detects unexpected prompt changes.

```yaml
- name: prompt-unchanged
  assert: content_hash
  hash: "a1b2c3d4..."   # omit to record current hash (always passes)
```

If `hash` is omitted, the test passes and reports the current hash so you can record it.

## Test Options

Each test case supports these common options:

```yaml
- name: example-test
  assert: contains
  text: "hello"
  skip: true               # Skip this test
  skip_reason: "not ready" # Reason for skipping
  case_sensitive: false     # For text/regex assertions (default: false)
  model: gpt-4o            # Override suite model for this test
```

## Output Formats

### Text (default)

Rich-formatted terminal output with colored pass/fail indicators.

```
Suite: greeting-tests
Prompt: prompts/greeting.yaml

  PASS  has-system-message
  PASS  token-count-reasonable
  FAIL  no-injection-risk
         Content unexpectedly contains 'ignore previous instructions'
  PASS  cost-under-budget

Results:
  3 passed, 1 failed (4 total)
  Duration: 12ms
```

### JSON

```bash
prompttest run tests/ --format json
```

Returns a JSON object with `total`, `passed`, `failed`, `errors`, `skipped`, `duration_ms`, and detailed `suites` array.

### JUnit XML

```bash
prompttest run tests/ --format junit
```

Standard JUnit XML format compatible with CI systems (GitHub Actions, Jenkins, GitLab CI, CircleCI).

## Programmatic Usage

```python
from prompttest import (
    load_test_suite,
    run_test_suite,
    run_test_file,
    run_test_directory,
    discover_test_files,
    format_text,
    format_json,
    format_junit,
)

# Run a single test file
report = run_test_file("tests/test_greeting.yaml")
print(f"Passed: {report.passed}/{report.total}")

# Run all tests in a directory
report = run_test_directory("tests/", fail_fast=True, pattern="test_*.yaml")

# Format output
print(format_text(report))
print(format_json(report))
print(format_junit(report))

# Load and run a suite manually
suite = load_test_suite("tests/test_greeting.yaml")
results = run_test_suite(suite, fail_fast=False)
for r in results:
    print(f"{r.test_name}: {r.status.value} - {r.message}")
```

## CI Integration

### GitHub Actions

```yaml
- name: Run prompt tests
  run: prompttest run tests/ --format junit > test-results.xml

- name: Upload test results
  uses: actions/upload-artifact@v4
  with:
    name: prompt-test-results
    path: test-results.xml
```

### GitLab CI

```yaml
prompt-tests:
  script:
    - pip install prompttest
    - prompttest run tests/ --format junit > report.xml
  artifacts:
    reports:
      junit: report.xml
```

Exit codes:

| Code | Meaning |
|------|---------|
| 0 | All tests passed (or no tests found) |
| 1 | One or more tests failed or errored |
| 2 | Path not found |

## License

MIT License. Author: Scott Converse.
