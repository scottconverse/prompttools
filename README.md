# prompttools — Developer Tools for LLM Prompts

Lint, format, test, and estimate costs for your LLM prompt files.

<!-- Badges -->
[![CI](https://img.shields.io/badge/CI-passing-brightgreen)]()
[![PyPI](https://img.shields.io/badge/PyPI-v1.0.0-blue)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]()

---

## Overview

**prompttools** is a monorepo containing seven developer tools that treat LLM prompts as first-class code artifacts. Each tool can be installed and used independently, but they share a common foundation through `prompttools-core`.

| Package | Version | Description |
|---------|---------|-------------|
| [prompttools-core](packages/prompttools-core/) | 1.0.0 | Shared foundation: parsing, tokenization, model profiles, config, cache, and plugin system |
| [promptlint](packages/promptlint/) | 0.3.0 | Static analysis and linting for prompt files with fixable rules |
| [promptfmt](packages/promptfmt/) | 1.0.0 | Auto-formatter for prompt files (whitespace, delimiters, variables, wrapping, structure) |
| [promptcost](packages/promptcost/) | 1.0.0 | Token cost estimation, model comparison, volume projections, and budget enforcement |
| [prompttest](packages/prompttest/) | 1.0.0 | Test framework for prompts with 15 assertion types and CI-ready output formats |
| [promptdiff](packages/promptdiff/) | 1.0.0 | Semantic diff for prompt changes — message-level diffs, variable impact, token deltas, breaking change detection |
| [promptvault](packages/promptvault/) | 1.0.0 | Version control and registry for prompt assets — semantic versioning, dependency resolution, lockfiles, searchable catalog |

## Installation

Install individual packages as needed:

```bash
pip install prompttools-core-ai
pip install promptfmt-ai
pip install promptcost-ai
pip install prompttest-ai
pip install promptlint-ai
pip install promptdiff-ai
pip install promptvault-ai
```

For development on the monorepo:

```bash
pip install -e packages/prompttools-core[dev]
pip install -e packages/promptfmt[dev]
pip install -e packages/promptcost[dev]
pip install -e packages/prompttest[dev]
pip install -e packages/promptlint[dev]
pip install -e packages/promptdiff[dev]
pip install -e packages/promptvault[dev]
```

**Requirements:** Python 3.9+

## Quick Start

### Parse a prompt file

```python
from prompttools_core import parse_file, Tokenizer

prompt = parse_file("prompts/greeting.yaml")
print(f"Messages: {len(prompt.messages)}")
print(f"Variables: {list(prompt.variables.keys())}")

tokenizer = Tokenizer.for_model("gpt-4o")
tokens = tokenizer.count_file(prompt)
print(f"Tokens: {tokens}")
```

### Format prompt files

```bash
# Format all prompt files in a directory
promptfmt format prompts/

# Check formatting without writing (CI mode)
promptfmt format prompts/ --check

# Show diff of what would change
promptfmt format prompts/ --diff
```

### Estimate costs

```bash
# Estimate cost for a single file
promptcost estimate prompts/greeting.yaml --model gpt-4o

# Compare costs across models
promptcost estimate prompts/greeting.yaml --compare

# Project costs at volume
promptcost estimate prompts/greeting.yaml --model gpt-4o --project 1000/day

# Enforce a budget ceiling
promptcost budget prompts/ --limit 0.05 --model gpt-4o
```

### Test your prompts

```bash
# Run tests from a YAML test file
prompttest run tests/test_greeting.yaml

# Run all tests in a directory
prompttest run tests/

# Output JUnit XML for CI
prompttest run tests/ --format junit
```

### Diff prompt changes

```bash
# Compare two prompt files
promptdiff old_prompt.yaml new_prompt.yaml

# JSON output for CI pipelines
promptdiff old.yaml new.yaml --format json

# Exit with code 1 if breaking changes are found (CI gate)
promptdiff old.yaml new.yaml --exit-on-breaking
```

### Manage prompt packages

```bash
# Initialize a prompt package
promptvault init --name @my-org/my-prompts --author "Your Name"

# Publish to local registry
promptvault publish

# Install dependencies and generate lockfile
promptvault install

# Search the registry
promptvault search greeting
```

Example test file (`test_greeting.yaml`):

```yaml
suite: greeting-tests
prompt: prompts/greeting.yaml
model: gpt-4o

tests:
  - name: has-system-message
    assert: has_role
    role: system

  - name: token-count-reasonable
    assert: max_tokens
    max: 2048

  - name: no-injection-risk
    assert: not_contains
    text: "ignore previous instructions"

  - name: cost-under-budget
    assert: max_cost
    max: 0.05
```

## Supported Prompt Formats

All tools support these file formats:

| Extension | Format |
|-----------|--------|
| `.yaml`, `.yml` | YAML (structured messages with metadata) |
| `.json` | JSON (structured messages with metadata) |
| `.md` | Markdown (heading-delimited sections) |
| `.txt` | Plain text (single message or `---` delimited) |

Template variables are detected in three syntaxes: `{{var}}` (Jinja), `{var}` (f-string), and `<var>` (XML/angle bracket).

## Built-in Model Profiles

prompttools ships with profiles for popular models including pricing and tokenizer configuration:

| Model | Provider | Context Window | Input $/Mtok | Output $/Mtok |
|-------|----------|---------------|-------------|--------------|
| gpt-4 | OpenAI | 8,192 | $30.00 | $60.00 |
| gpt-4-turbo | OpenAI | 128,000 | $10.00 | $30.00 |
| gpt-4o | OpenAI | 128,000 | $2.50 | $10.00 |
| gpt-4o-mini | OpenAI | 128,000 | $0.15 | $0.60 |
| claude-3-haiku | Anthropic | 200,000 | $0.25 | $1.25 |
| claude-3-sonnet | Anthropic | 200,000 | $3.00 | $15.00 |
| claude-3-opus | Anthropic | 200,000 | $15.00 | $75.00 |
| claude-4-sonnet | Anthropic | 200,000 | $3.00 | $15.00 |
| gemini-1.5-pro | Google | 1,000,000 | $1.25 | $5.00 |
| gemini-2.0-flash | Google | 1,048,576 | $0.10 | $0.40 |

Custom profiles can be registered programmatically via `register_profile()`.

## Configuration

All tools share a common configuration file format. Place a `.prompttools.yaml` in your project root:

```yaml
model: gpt-4o
exclude:
  - "vendor/**"
  - "*.generated.*"
plugins: []
cache:
  enabled: true
  dir: .prompttools-cache
```

Tool-specific config files are also supported: `.promptfmt.yaml`, `.promptcost.yaml`, etc. Config files are discovered by walking up the directory tree from the target file.

## Per-Package Documentation

Each package has its own detailed README:

- [prompttools-core README](packages/prompttools-core/README.md) -- Parsing, tokenization, model profiles, config, cache, plugins
- [promptfmt README](packages/promptfmt/README.md) -- Auto-formatter CLI and rules
- [promptcost README](packages/promptcost/README.md) -- Cost estimation, comparison, budgets
- [prompttest README](packages/prompttest/README.md) -- Test framework, assertion types, reporters
- [promptdiff README](packages/promptdiff/README.md) -- Semantic diff, breaking change detection, CI integration
- [promptvault README](packages/promptvault/README.md) -- Package registry, versioning, dependency resolution

See [README-full.md](README-full.md) for comprehensive documentation combining all packages.

## License

MIT License. See [LICENSE](LICENSE) for details.

See [Terms of Service & Legal Disclaimer](docs/terms.html) for warranty limitations and tool-specific risk disclosures.

## Author

Scott Converse
