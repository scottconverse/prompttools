# promptdiff

Semantic diff for LLM prompt changes. Part of the [prompttools](https://github.com/scottconverse/prompttools) suite.

Unlike generic text diffing, promptdiff understands prompt structure: messages, variables, metadata, and token counts. It classifies changes as breaking or non-breaking and outputs structured reports suitable for CI/CD pipelines and GitHub PR comments.

## Installation

```bash
pip install promptdiff-ai
```

## Quick Start

```bash
# Compare two prompt files
promptdiff old_prompt.yaml new_prompt.yaml

# JSON output for CI pipelines
promptdiff old.yaml new.yaml --format json

# Markdown output for GitHub PR comments
promptdiff old.yaml new.yaml --format markdown

# Exit with code 1 if breaking changes are found (CI gate)
promptdiff old.yaml new.yaml --exit-on-breaking

# Show per-message token breakdowns
promptdiff old.yaml new.yaml --token-detail
```

## What It Detects

### Message-Level Changes
- Added, removed, or modified messages
- Per-message token deltas
- Unified content diffs within modified messages

### Variable Changes
- New variables (with or without defaults)
- Removed variables
- Modified default values

### Metadata Changes
- Model changes
- Added/removed/modified metadata keys

### Token Deltas
- Total token count comparison
- Percentage change
- Per-message breakdowns (with `--token-detail`)

## Breaking Change Classification

### Breaking (High Severity)
- **New required variable** -- a variable added without a default value; existing callers will fail
- **Removed variable** -- callers referencing this variable will break
- **Removed message** -- changes the prompt structure

### Breaking (Medium Severity)
- **Model change** -- may affect behavior, pricing, and capabilities
- **Role ordering change** -- may affect model behavior

### Non-Breaking
- Added variable with a default value
- Added messages (extends the prompt)
- Content modifications within existing messages
- Metadata changes (except model)

## Output Formats

### Text (default)
Rich terminal output with color-coded diffs:

```
Prompt Diff: new_prompt.yaml
  old: a1b2c3d4e5f6  new: f6e5d4c3b2a1

BREAKING CHANGES (2):
  HIGH [variable] Variable 'tone' was removed
  MEDIUM [model] Model changed from 'gpt-4' to 'gpt-4o'

Token Delta:
  150 -> 165 (+15, +10.0%)

Messages (1 changed):
  ~ system
      System message content modified
```

### JSON
Structured JSON for programmatic consumption:

```bash
promptdiff old.yaml new.yaml --format json
```

### Markdown
GitHub-flavored Markdown for PR comments:

```bash
promptdiff old.yaml new.yaml --format markdown
```

## Python API

```python
from promptdiff import diff_files, format_text, format_json

# Compare two files
result = diff_files("prompts/v1.yaml", "prompts/v2.yaml")

# Check for breaking changes
if result.is_breaking:
    for bc in result.breaking_changes:
        print(f"[{bc.severity}] {bc.description}")

# Get token delta
print(f"Tokens: {result.token_delta.old_total} -> {result.token_delta.new_total}")

# Format output
print(format_text(result))
```

## CLI Reference

```
Usage: promptdiff [OPTIONS] FILE_A FILE_B

Arguments:
  FILE_A  Path to the old prompt file
  FILE_B  Path to the new prompt file

Options:
  -f, --format [text|json|markdown]  Output format (default: text)
  --exit-on-breaking                 Exit with code 1 if breaking changes found
  --token-detail                     Show per-message token breakdowns
  -e, --encoding TEXT                tiktoken encoding (default: cl100k_base)
  -V, --version                      Show version and exit
  --help                             Show this message and exit
```

## Supported File Formats

All formats supported by prompttools-core:
- YAML (`.yaml`, `.yml`)
- JSON (`.json`)
- Markdown (`.md`)
- Text (`.txt`)

## License

MIT
