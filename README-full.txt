===============================================================================
prompttools -- Comprehensive Documentation
===============================================================================

Developer Tools for LLM Prompts: Lint, format, test, and estimate costs for
your LLM prompt files.

Version: 1.0.0
Author:  Scott Converse
License: MIT
Python:  3.9+

===============================================================================
TABLE OF CONTENTS
===============================================================================

 1. Overview
 2. Installation
 3. Getting Started
 4. prompttools-core Reference
 5. promptfmt Reference
 6. promptcost Reference
 7. prompttest Reference
 8. promptdiff Reference
 9. promptvault Reference
10. Configuration Reference
11. CI/CD Integration Guide
12. Plugin Development Guide
13. Troubleshooting
14. FAQ


===============================================================================
1. OVERVIEW
===============================================================================

prompttools is a monorepo containing seven developer tools that treat LLM
prompts as first-class code artifacts. Think eslint/prettier/jest, but for
prompts.

  Package             Version  Description
  ---                 ---      ---
  prompttools-core    1.0.0    Shared foundation: parsing, tokenization,
                               model profiles, config, cache, plugins
  promptlint          0.3.0    Static analysis and linting for prompt files
                               with fixable rules
  promptfmt           1.0.0    Auto-formatter (whitespace, delimiters,
                               variables, wrapping, structure)
  promptcost          1.0.0    Cost estimation, model comparison, volume
                               projections, budget enforcement
  prompttest          1.0.0    Test framework with 15 assertion types and
                               CI-ready output formats
  promptdiff          1.0.0    Semantic diff for prompt changes -- message-level
                               diffs, variable impact, token deltas, breaking
                               change detection
  promptvault         1.0.0    Version control and registry for prompt assets --
                               semantic versioning, dependency resolution,
                               lockfiles, searchable catalog

All tools support four prompt file formats:
  * YAML (.yaml / .yml)
  * JSON (.json)
  * Markdown (.md)
  * Plain text (.txt)

Template variables are detected in three syntaxes:
  * {{var}} (Jinja)
  * {var}   (f-string)
  * <var>   (XML/angle bracket)


===============================================================================
2. INSTALLATION
===============================================================================

Install Individual Packages
----------------------------

    pip install prompttools-core-ai
    pip install promptfmt-ai
    pip install promptcost-ai
    pip install prompttest-ai
    pip install promptlint-ai
    pip install promptdiff-ai
    pip install promptvault-ai

Each tool package depends on prompttools-core-ai and will install it
automatically.

Development Installation (Monorepo)
------------------------------------

    git clone <repository-url>
    cd prompttools

    pip install -e packages/prompttools-core[dev]
    pip install -e packages/promptfmt[dev]
    pip install -e packages/promptcost[dev]
    pip install -e packages/prompttest[dev]
    pip install -e packages/promptlint[dev]
    pip install -e packages/promptdiff[dev]
    pip install -e packages/promptvault[dev]

Running Tests
--------------

    # All tests
    pytest

    # Single package
    pytest packages/prompttools-core/tests/
    pytest packages/promptfmt/tests/
    pytest packages/promptcost/tests/
    pytest packages/prompttest/tests/
    pytest packages/promptdiff/tests/
    pytest packages/promptvault/tests/

    # Lint and type check
    ruff check .
    mypy packages/

System Requirements
--------------------

  * Python 3.9, 3.10, 3.11, or 3.12
  * Key dependencies: pydantic >= 2.0, pyyaml >= 6.0, tiktoken >= 0.7,
    typer >= 0.12, rich >= 13.0


===============================================================================
3. GETTING STARTED
===============================================================================

Step 1: Create a prompt file
-----------------------------

Create prompts/greeting.yaml:

    model: gpt-4o
    description: A friendly greeting prompt
    messages:
      - role: system
        content: You are a helpful assistant that greets users warmly.
      - role: user
        content: Hello! My name is {{user_name}}.

Step 2: Parse and inspect it
------------------------------

    from prompttools_core import parse_file, Tokenizer

    prompt = parse_file("prompts/greeting.yaml")
    print(f"Format: {prompt.format.value}")
    print(f"Messages: {len(prompt.messages)}")
    print(f"Variables: {list(prompt.variables.keys())}")

    tokenizer = Tokenizer.for_model("gpt-4o")
    total = tokenizer.count_file(prompt)
    print(f"Total tokens: {total}")

Step 3: Format the prompt file
-------------------------------

    promptfmt format prompts/greeting.yaml

Step 4: Estimate cost
----------------------

    promptcost estimate prompts/greeting.yaml --model gpt-4o --project 1000/day

Step 5: Write tests
--------------------

Create tests/test_greeting.yaml:

    suite: greeting-tests
    prompt: ../prompts/greeting.yaml
    model: gpt-4o

    tests:
      - name: has-system-message
        assert: has_role
        role: system

      - name: uses-user-name-variable
        assert: has_variables
        variables:
          - user_name

      - name: token-count-reasonable
        assert: max_tokens
        max: 2048

      - name: no-injection-risk
        assert: not_contains
        text: "ignore previous instructions"

      - name: cost-under-budget
        assert: max_cost
        max: 0.05

Run the tests:

    prompttest run tests/test_greeting.yaml


===============================================================================
4. PROMPTTOOLS-CORE REFERENCE
===============================================================================

Parsing
--------

  parse_file(path, config=None) -> PromptFile
    Parse a prompt file, auto-detecting format by extension.
    Raises ParseError for unsupported formats.

  parse_directory(path, config=None, patterns=None) -> list[PromptFile]
    Recursively parse all prompt files in a directory.
    Skips files that fail to parse. Respects config.exclude patterns.

  parse_stdin(content, format) -> PromptFile
    Parse prompt content from stdin.
    format: "text", "md", "yaml", or "json"

  parse_pipeline(manifest_path, config=None) -> PromptPipeline
    Parse a pipeline manifest YAML and all referenced prompt files.

Example:

    from prompttools_core import parse_file
    prompt = parse_file("prompts/greeting.yaml")

Tokenization
--------------

  Tokenizer(encoding="cl100k_base", provider="default")
    Create a tokenizer with a specific encoding.
    Provider controls per-message role overhead:
      openai: 4 tokens, anthropic: 3, google: 3

  Tokenizer.for_model(model_name) -> Tokenizer
    Factory that looks up the model profile and creates a tokenizer
    with the correct encoding and provider.

  Tokenizer.count(text) -> int
    Count tokens in a string.

  Tokenizer.count_file(prompt_file) -> int
    Count tokens for a prompt file. Populates token_count on each
    message and total_tokens on the file.

  Tokenizer.count_messages(messages) -> int
    Count tokens across messages including role overhead.

  count_tokens(text, encoding="cl100k_base") -> int
    Standalone convenience function.

  get_encoding(name="cl100k_base")
    Returns a cached tiktoken encoding (LRU cached, up to 8).

Built-in Model Profiles
-------------------------

  Model             Provider   Context      Encoding      In $/Mtok  Out $/Mtok
  ---               ---        ---          ---           ---        ---
  gpt-4             openai     8,192        cl100k_base   $30.00     $60.00
  gpt-4-turbo       openai     128,000      cl100k_base   $10.00     $30.00
  gpt-4o            openai     128,000      o200k_base    $2.50      $10.00
  gpt-4o-mini       openai     128,000      o200k_base    $0.15      $0.60
  claude-3-haiku    anthropic  200,000      cl100k_base*  $0.25      $1.25
  claude-3-sonnet   anthropic  200,000      cl100k_base*  $3.00      $15.00
  claude-3-opus     anthropic  200,000      cl100k_base*  $15.00     $75.00
  claude-4-sonnet   anthropic  200,000      cl100k_base*  $3.00      $15.00
  gemini-1.5-pro    google     1,000,000    cl100k_base*  $1.25      $5.00
  gemini-2.0-flash  google     1,048,576    cl100k_base*  $0.10      $0.40

  * Approximate tokenizer

Profile API:

  get_profile(name) -> ModelProfile or None
    Look up a profile. Checks custom profiles first, then built-in.

  list_profiles() -> dict[str, ModelProfile]
    All registered profiles (built-in + custom).

  register_profile(profile)
    Register a custom model profile.

Caching
--------

  PromptCache(cache_dir=Path(".prompttools-cache"))

  Methods:
    cache.get(key) -> value or None (None if expired)
    cache.set(key, value, ttl=None)  (ttl in seconds)
    cache.invalidate(key)
    cache.clear()

  Static method:
    PromptCache.content_key(content, encoding) -> str (SHA256 hash)

Plugin System
--------------

  load_plugin(path, base_class) -> list[type]
    Load plugin classes from a single Python file.

  discover_plugins(plugin_dirs, base_class) -> list[type]
    Find all classes subclassing base_class in plugin directories.
    Skips files starting with underscore. Skips duplicate class names.

Data Models
------------

  PromptFile:
    * path: Path
    * format: PromptFormat (TEXT, MARKDOWN, YAML, JSON)
    * raw_content: str
    * messages: list[Message]
    * variables: dict[str, str]
    * variable_defaults: dict[str, str]
    * metadata: dict[str, Any]
    * total_tokens: Optional[int]
    * content_hash: str (SHA256)
    * Helper methods: system_message(), user_messages(), has_role(role)

  Message:
    * role: "system" | "user" | "assistant" | "tool"
    * content: str
    * line_start, line_end: Optional[int]
    * token_count: Optional[int]
    * metadata: dict[str, Any]

  ModelProfile:
    * name, context_window, encoding, provider
    * input_price_per_mtok, output_price_per_mtok
    * max_output_tokens, supports_system_message, supports_tools
    * approximate_tokenizer: bool

  ToolConfig:
    * model, tokenizer_encoding, exclude, plugins
    * cache_enabled, cache_dir, extra

Error Hierarchy
----------------

  PromptToolsError (base)
    * ParseError       -- file cannot be parsed
    * ConfigError      -- configuration is invalid
    * TokenizerError   -- tokenization fails
    * ProfileNotFoundError -- unknown model profile
    * PluginError      -- plugin loading/execution fails
    * CacheError       -- cache read/write fails


===============================================================================
5. PROMPTFMT REFERENCE
===============================================================================

CLI Commands
-------------

  promptfmt format <path>
    Format prompt files in-place or check formatting.

    Options:
      --check              Dry run; exit 1 if changes needed
      --diff               Show unified diff
      --delimiter-style    Target: ###, ---, ===, ***, ~~~ (default: ###)
      --variable-style     Target: double_brace, single_brace,
                           angle_bracket (default: double_brace)
      --max-line-length    Max line length, 0 to disable (default: 120)
      --quiet, -q          Suppress non-error output

  promptfmt init
    Generate a default .promptfmt.yaml in the current directory.

Formatting Pipeline
--------------------

Rules are applied in this order:

  1. Whitespace normalization
     - LF line endings
     - Strip trailing whitespace
     - Remove leading blank lines
     - Collapse 3+ consecutive blank lines to 2
     - Ensure single trailing newline

  2. Delimiter normalization
     - Normalize ---, ===, ***, ~~~ to target style
     - Code blocks (```) are preserved

  3. Variable syntax normalization
     - Convert {{var}}, {var}, <var> to target style
     - Inline code spans preserved
     - HTML tags excluded from angle bracket detection

  4. Line wrapping
     - Wrap at word boundaries at max_line_length
     - Skip: URLs, table rows, headings, code blocks
     - Preserve leading indentation

  5. Structure normalization (YAML/JSON only)
     - Sort keys with priority: model, name, description, defaults
     - Within messages: role before content
     - Consistent indentation
     - Re-apply whitespace after re-serialization

Semantic Equivalence
---------------------

After formatting, promptfmt re-parses the output and verifies that:
  * Same number of messages
  * Each message has the same role
  * Content is identical after whitespace normalization
  * Same variable names (syntax style may differ)
  * Same metadata keys and values

If formatting changes the meaning, the change is rejected with an error.

Programmatic API
-----------------

    from promptfmt import format_file, format_content, FmtConfig, is_equivalent

    config = FmtConfig(
        delimiter_style="###",
        variable_style="double_brace",
        max_line_length=120,
        wrap_style="soft",
        sort_metadata_keys=True,
        indent=2,
    )

    result = format_file("prompts/greeting.yaml", config)
    # result.changed, result.equivalent, result.formatted_content


===============================================================================
6. PROMPTCOST REFERENCE
===============================================================================

CLI Commands
-------------

  promptcost estimate <path>
    Estimate costs for a prompt file or directory.

    Options:
      --model, -m          Model profile (default: claude-4-sonnet)
      --output-tokens      Override output token estimate
      --project            Volume projection (e.g., 1000/day)
      --compare            Compare across default model set
      --models             Comma-separated model list for comparison
      --format, -f         Output: text or json (default: text)

  promptcost budget <path>
    Check prompt costs against a budget ceiling.

    Options:
      --limit, -l          Max cost per invocation in USD (required)
      --model, -m          Model profile (default: claude-4-sonnet)
      --output-tokens      Override output token estimate

  promptcost delta <old_path> <new_path>
    Show cost impact of a prompt change.

    Options:
      --model, -m          Model profile
      --volume             Volume for monthly impact
      --output-tokens      Override output tokens

  promptcost models
    List all available model profiles with pricing.

Output Token Estimation Heuristics
------------------------------------

  Priority  Source                                        Tokens  Method
  ---       ---                                           ---     ---
  1         --output-tokens CLI flag                      as set  explicit
  2         expected_output_tokens in prompt metadata     as set  explicit
  3         Keywords: json, structured, schema, format    500     heuristic
  4         Keywords: brief, short, concise, summary      300     heuristic
  5         Keywords: detailed, comprehensive, thorough   2000    heuristic
  6         Default                                       1000    heuristic

  Estimates are capped at the model's max_output_tokens.

Volume Projection Formats
---------------------------

  N/hour   -> N * 24 calls/day
  N/day    -> N calls/day
  N/week   -> N / 7 calls/day
  N/month  -> N / 30 calls/day

  Projections: daily, monthly (daily * 30), annual (daily * 365)

Programmatic API
-----------------

    from prompttools_core import parse_file
    from promptcost import estimate_file, compare_models, project_cost, check_budget

    prompt = parse_file("prompts/greeting.yaml")
    est = estimate_file(prompt, model="gpt-4o")

    comp = compare_models(prompt, ["gpt-4o", "gpt-4o-mini", "claude-4-sonnet"])

    proj = project_cost(est, "1000/day")

    results = check_budget([est], budget=0.05)


===============================================================================
7. PROMPTTEST REFERENCE
===============================================================================

CLI Commands
-------------

  prompttest run <path>
    Run prompt tests from a file or directory.

    Options:
      --format, -f         Output: text, json, junit (default: text)
      --model, -m          Override model for cost/token assertions
      --fail-fast          Stop after first failure
      --verbose, -v        Detailed output for all tests
      --pattern, -p        Glob pattern for test files (default: test_*.yaml)

  prompttest init
    Create an example test_example.yaml in the current directory.

Test File Format
-----------------

    suite: suite-name              # optional, defaults to filename
    prompt: path/to/prompt.yaml    # required, relative to test file
    model: gpt-4o                  # optional default model

    tests:
      - name: test-name
        assert: assertion_type
        # assertion-specific parameters...
        skip: false
        skip_reason: "reason"
        case_sensitive: false
        model: gpt-4o

All 15 Assertion Types
-----------------------

  Content assertions:

    contains
      Required: text
      Checks that prompt content contains specific text.

    not_contains
      Required: text
      Checks that prompt content does NOT contain specific text.

    matches_regex
      Required: pattern
      Checks that prompt content matches a regex.

    not_matches_regex
      Required: pattern
      Checks that prompt content does NOT match a regex.

  Structure assertions:

    has_role
      Required: role
      Checks that the prompt has a message with the given role.

    has_variables
      Required: variables (list)
      Checks that the prompt uses specific template variables.

    has_metadata
      Required: keys (list)
      Checks that the prompt has specific metadata keys.

    valid_format
      Required: (none)
      Checks that the file parsed with at least one message.

  Token/size assertions:

    max_tokens
      Required: max
      Checks that total token count is under a maximum.

    min_tokens
      Required: min
      Checks that total token count is above a minimum.

    max_messages
      Required: max
      Checks that message count is under a maximum.

    min_messages
      Required: min
      Checks that message count is above a minimum.

    token_ratio
      Required: ratio_max
      Checks that system/user token ratio is within limit.

  Cost assertions:

    max_cost
      Required: max, model (on test or suite)
      Checks that estimated cost is under a budget ceiling.

  Regression assertions:

    content_hash
      Required: hash (optional -- omit to record current hash)
      Checks that the SHA256 content hash matches expected value.

Output Formats
---------------

  text    Rich-formatted terminal output with PASS/FAIL/ERR/SKIP indicators.

  json    Structured JSON with total, passed, failed, errors, skipped,
          duration_ms, and detailed suites array.

  junit   Standard JUnit XML compatible with CI systems (GitHub Actions,
          Jenkins, GitLab CI, CircleCI).

Programmatic API
-----------------

    from prompttest import (
        run_test_file, run_test_directory, load_test_suite,
        run_test_suite, discover_test_files,
        format_text, format_json, format_junit,
    )

    report = run_test_file("tests/test_greeting.yaml")
    report = run_test_directory("tests/", fail_fast=True)

    suite = load_test_suite("tests/test_greeting.yaml")
    results = run_test_suite(suite)

    print(format_text(report))
    print(format_junit(report))


===============================================================================
8. PROMPTDIFF REFERENCE
===============================================================================

CLI Commands
-------------

  promptdiff <file_a> <file_b>
    Compare two prompt files and show semantic differences.

    Options:
      -f, --format         Output: text, json, markdown (default: text)
      --exit-on-breaking   Exit with code 1 if breaking changes found
      --token-detail       Show per-message token breakdowns
      -e, --encoding       tiktoken encoding (default: cl100k_base)
      -V, --version        Show version and exit

What It Detects
----------------

  * Message-level changes -- Added, removed, or modified messages with
    per-message token deltas and unified content diffs
  * Variable changes -- New variables (with or without defaults), removed
    variables, modified default values
  * Metadata changes -- Model changes, added/removed/modified metadata keys
  * Token deltas -- Total token count comparison, percentage change,
    per-message breakdowns

Breaking Change Classification
--------------------------------

  Severity  Change                  Reason
  ---       ---                     ---
  HIGH      New required variable   Added without default; callers will fail
  HIGH      Removed variable        Callers referencing it will break
  HIGH      Removed message         Changes the prompt structure
  MEDIUM    Model change            May affect behavior, pricing, capabilities
  MEDIUM    Role ordering change    May affect model behavior

  Non-breaking: added variables with defaults, added messages, content
  modifications, metadata changes (except model).

Output Formats
---------------

  text      Rich terminal output with color-coded diffs (default)
  json      Structured JSON for programmatic consumption
  markdown  GitHub-flavored Markdown for PR comments

Programmatic API
-----------------

    from promptdiff import diff_files, format_text, format_json

    result = diff_files("prompts/v1.yaml", "prompts/v2.yaml")

    if result.is_breaking:
        for bc in result.breaking_changes:
            print(f"[{bc.severity}] {bc.description}")

    print(f"Tokens: {result.token_delta.old_total} -> {result.token_delta.new_total}")
    print(format_text(result))


===============================================================================
9. PROMPTVAULT REFERENCE
===============================================================================

CLI Commands
-------------

  promptvault init               Scaffold a new promptvault.yaml manifest
  promptvault publish             Publish the current package to the local registry
  promptvault install             Resolve dependencies and generate a lockfile
  promptvault search <query>      Search the registry catalog
  promptvault info <package>      Show package details
  promptvault list                List all packages in the registry
  promptvault verify              Verify lockfile integrity

  Global Options:
    --registry <path>    Override default registry (~/.promptvault/registry/)
    --format text|json   Output format (default: text)

Package Manifest
-----------------

Create a promptvault.yaml to define a prompt package:

    name: '@my-org/my-prompts'
    version: 0.1.0
    description: A prompt package
    author: Your Name
    license: MIT
    prompts:
      - file: prompts/greeting.yaml
        name: greeting
        description: A friendly greeting prompt
        variables: [user_name]
        model: claude-4-sonnet
    dependencies: {}
    quality:
      lint: optional
      test: optional
      format: optional

Version Ranges
---------------

  Syntax       Meaning                   Example
  ---          ---                       ---
  ^1.2.3       Compatible with 1.x.x     >=1.2.3, <2.0.0
  ~1.2.3       Patch-level changes        >=1.2.3, <1.3.0
  >=1.0,<2.0   PEP 440 range             Explicit range
  1.2.3        Exact version              ==1.2.3

Programmatic API
-----------------

    from promptvault import LocalRegistry, PackageManifest, resolve_dependencies

    registry = LocalRegistry()

    entry = registry.publish(Path("./my-package"))

    results = registry.search("greeting")

    manifest = PackageManifest(...)
    resolved = resolve_dependencies(manifest, registry)


===============================================================================
10. CONFIGURATION REFERENCE
===============================================================================

Config File Locations
----------------------

Config files are discovered by walking up the directory tree. At each level,
these filenames are checked in order:

  1. .prompt{tool_name}.yaml  (e.g., .promptfmt.yaml)
  2. .prompttools.yaml        (suite-wide)
  3. .promptlint.yaml         (backward compatibility)

Merge Priority
---------------

  1. CLI flags (highest)
  2. Config file
  3. Model profile defaults
  4. Built-in defaults (lowest)

Full Config File Reference
---------------------------

    # .prompttools.yaml

    model: gpt-4o

    exclude:
      - "vendor/**"
      - "*.generated.*"
      - "node_modules/**"

    plugins:
      - "./my-plugins"

    cache:
      enabled: true
      dir: .prompttools-cache

    tokenizer:
      encoding: cl100k_base

    # Tool-specific sections
    fmt:
      delimiter_style: "###"
      variable_style: double_brace
      max_line_length: 120
      wrap_style: soft
      sort_metadata_keys: true
      indent: 2


===============================================================================
11. CI/CD INTEGRATION GUIDE
===============================================================================

GitHub Actions
---------------

    name: Prompt Quality
    on: [push, pull_request]

    jobs:
      prompt-checks:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - uses: actions/setup-python@v5
            with:
              python-version: '3.12'

          - name: Install tools
            run: pip install promptfmt-ai promptcost-ai prompttest-ai

          - name: Check formatting
            run: promptfmt format prompts/ --check

          - name: Check budget
            run: promptcost budget prompts/ --limit 0.10 --model gpt-4o

          - name: Run tests
            run: prompttest run tests/ --format junit > results.xml

          - name: Upload test results
            if: always()
            uses: actions/upload-artifact@v4
            with:
              name: prompt-test-results
              path: results.xml

GitLab CI
----------

    prompt-quality:
      image: python:3.12
      before_script:
        - pip install promptfmt-ai promptcost-ai prompttest-ai
      script:
        - promptfmt format prompts/ --check
        - promptcost budget prompts/ --limit 0.10 --model gpt-4o
        - prompttest run tests/ --format junit > report.xml
      artifacts:
        reports:
          junit: report.xml

Pre-commit Hooks
-----------------

    #!/bin/sh
    promptfmt format prompts/ --check || exit 1
    promptcost budget prompts/ --limit 0.10 --model gpt-4o || exit 1
    prompttest run tests/ || exit 1

Exit Codes
-----------

  Tool         Code 0               Code 1                    Code 2
  ---          ---                  ---                       ---
  promptfmt    All formatted        Files need formatting     Errors
  promptcost   Within budget        Over budget               Path not found
  prompttest   All passed           Tests failed/errored      Path not found


===============================================================================
12. PLUGIN DEVELOPMENT GUIDE
===============================================================================

The plugin system allows extending prompttools with custom logic. Plugins are
Python files containing classes that subclass a tool-specific base class.

Creating a Plugin
------------------

1. Create a Python file in a plugin directory:

    # my_plugins/custom_rule.py
    from promptlint.rules.base import BaseRule
    from promptlint.models import LintConfig, LintViolation, PromptFile, Severity

    class NoTodoComments(BaseRule):
        rule_id = "custom/no-todo"
        name = "No TODO comments in prompts"
        default_severity = Severity.WARNING
        fixable = False

        def check(self, prompt_file, config):
            violations = []
            for msg in prompt_file.messages:
                if "TODO" in msg.content:
                    violations.append(LintViolation(
                        rule_id=self.rule_id,
                        message="Found TODO comment in prompt",
                        severity=self.default_severity,
                        line=msg.line_start,
                    ))
            return violations

2. Register the plugin directory in your config:

    # .prompttools.yaml
    plugins:
      - "./my_plugins"

Plugin Discovery Rules
-----------------------

  * Only .py files are scanned (files starting with _ are skipped)
  * Classes must be concrete subclasses of the specified base class
  * Duplicate class names across files are skipped with a warning
  * Plugins are loaded in sorted filename order
  * Import errors are logged; the plugin is skipped (does not halt)


===============================================================================
13. TROUBLESHOOTING
===============================================================================

"Unsupported file extension" error
  Ensure your prompt files use a supported extension:
  .yaml, .yml, .json, .md, or .txt

"tiktoken is not installed" error
  Install tiktoken: pip install tiktoken
  This is a required dependency and should be installed automatically.

"Unknown model profile" error
  The model name does not match any built-in or custom profile.
  Run "promptcost models" to see available profiles.
  Register custom profiles with register_profile().

Token counts differ from the LLM provider's count
  Non-OpenAI models use cl100k_base as an approximation. Token counts
  may differ from the provider's actual tokenizer. The
  approximate_tokenizer flag on the profile indicates this.

promptfmt reports "Formatting altered semantic content"
  The formatting rules changed the meaning of the prompt. This is a
  safety check to prevent unintended changes.

Config file not being found
  Config files are discovered by walking up the directory tree. Ensure
  the file is in the target directory or a parent. Check the filename
  starts with a dot: .prompttools.yaml

JUnit XML not recognized by CI
  Ensure you redirect output to a file:
  prompttest run tests/ --format junit > results.xml


===============================================================================
14. FAQ
===============================================================================

Q: Can I use prompttools without any LLM API calls?
A: Yes. All tools work entirely offline. They parse, analyze, and test
   prompt files without making any API calls.

Q: Which tokenizer is used for non-OpenAI models?
A: Non-OpenAI models use cl100k_base as an approximation, noted by the
   approximate_tokenizer flag on the profile. Token counts may differ
   slightly from the provider's actual tokenizer.

Q: Can I add support for a new model?
A: Yes. Use register_profile() to add a custom ModelProfile with the
   model's context window, pricing, and encoding.

Q: How does promptcost estimate output tokens?
A: It uses keyword-based heuristics. You can override with
   --output-tokens or by setting expected_output_tokens in your prompt
   file's metadata.

Q: Can I use prompttest with pytest?
A: prompttest is a standalone framework with its own YAML test files.
   It does not integrate into pytest discovery, but you can call its
   Python API from within a pytest test.

Q: What happens if promptfmt changes the meaning of my prompt?
A: promptfmt verifies semantic equivalence after formatting. If the
   formatted output is not semantically equivalent, the change is
   rejected with an error.

Q: How do I exclude files from processing?
A: Add glob patterns to the exclude list in your config file:
   exclude: ["vendor/**", "*.generated.*"]

Q: Can I use these tools in a monorepo with non-prompt files?
A: Yes. Tools only process files with supported extensions. Use the
   exclude config to skip directories like node_modules or vendor.


===============================================================================

prompttools v1.0.0
Author: Scott Converse
License: MIT
