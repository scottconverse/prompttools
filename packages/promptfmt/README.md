# promptfmt

Auto-formatter for LLM prompt files.

[![PyPI](https://img.shields.io/badge/PyPI-v1.0.0-blue)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]()
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)]()

## What It Does

`promptfmt` is an opinionated auto-formatter for LLM prompt files, similar to what Prettier does for JavaScript or Black does for Python. It normalizes whitespace, section delimiters, template variable syntax, line wrapping, and structural formatting for YAML/JSON prompt files.

After formatting, promptfmt verifies **semantic equivalence** -- it re-parses the formatted output and confirms that the meaning of the prompt has not changed (same messages, roles, variables, and metadata).

## Installation

```bash
pip install promptfmt-ai
```

**Dependencies:** prompttools-core-ai >= 1.0, typer >= 0.12, rich >= 13.0, watchfiles >= 0.21

## CLI Commands

### `promptfmt format`

Format prompt files in-place or check formatting.

```bash
# Format a single file
promptfmt format prompts/greeting.yaml

# Format all prompt files in a directory (recursive)
promptfmt format prompts/

# Check only -- exit 1 if any file would change (for CI)
promptfmt format prompts/ --check

# Show a unified diff of changes
promptfmt format prompts/ --diff

# Quiet mode (no output except errors)
promptfmt format prompts/ -q
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--check` | `false` | Check only, do not write files. Exit code 1 if changes needed. |
| `--diff` | `false` | Show unified diff of changes. |
| `--delimiter-style` | `###` | Target delimiter style: `###`, `---`, `===`, `***`, `~~~` |
| `--variable-style` | `double_brace` | Target variable syntax: `double_brace`, `single_brace`, `angle_bracket` |
| `--max-line-length` | `120` | Maximum line length for wrapping. 0 to disable. |
| `--quiet`, `-q` | `false` | Suppress non-error output. |

### `promptfmt init`

Generate a default `.promptfmt.yaml` configuration file in the current directory.

```bash
promptfmt init
```

This creates a `.promptfmt.yaml` with default settings:

```yaml
# promptfmt configuration
delimiter_style: '###'
variable_style: double_brace
max_line_length: 120
wrap_style: soft
sort_metadata_keys: true
indent: 2
exclude:
  - 'vendor/**'
  - '*.generated.*'
```

## Formatting Rules

promptfmt applies five rule categories in order:

### 1. Whitespace Normalization

- Normalize line endings to LF
- Strip trailing whitespace from every line
- Remove leading blank lines at file start
- Collapse 3+ consecutive blank lines to 2
- Ensure file ends with exactly one newline

### 2. Delimiter Normalization

Normalizes section delimiters (`---`, `===`, `***`, `~~~`) to a single consistent style. Code blocks (` ``` `) are preserved and not modified.

**Supported styles:** `###`, `---`, `===`, `***`, `~~~`

### 3. Variable Syntax Normalization

Converts all template variable references to a single syntax style. Inline code spans (`` `code` ``) are preserved and not modified.

| Style | Syntax | Example |
|-------|--------|---------|
| `double_brace` | `{{var}}` | `Hello {{name}}` |
| `single_brace` | `{var}` | `Hello {name}` |
| `angle_bracket` | `<var>` | `Hello <name>` |

Common HTML tags (`div`, `span`, `p`, `br`, etc.) are excluded from variable detection when using angle bracket style.

### 4. Line Wrapping

Wraps lines exceeding the configured maximum length at word boundaries. The following are never wrapped:

- Lines inside code blocks
- URL lines
- Table rows (starting with `|`)
- Heading lines (starting with `#`)

Leading indentation is preserved on continuation lines.

### 5. Structure Normalization (YAML/JSON only)

For YAML and JSON files:

- Re-serializes with consistent indentation (default: 2 spaces)
- Sorts metadata keys with priority ordering: `model`, `name`, `description`, `defaults` appear first, then remaining keys alphabetically
- Within message objects, sorts keys with `role` before `content`
- Re-applies whitespace normalization after structural changes

## Configuration (.promptfmt.yaml)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `delimiter_style` | string | `"###"` | Target delimiter style |
| `variable_style` | string | `"double_brace"` | Target variable syntax |
| `max_line_length` | int | `120` | Max line length (0 to disable) |
| `wrap_style` | string | `"soft"` | Wrapping approach |
| `sort_metadata_keys` | bool | `true` | Sort keys in YAML/JSON |
| `indent` | int | `2` | Indentation width for YAML/JSON |
| `exclude` | list | `[]` | Glob patterns to exclude |

## Programmatic Usage

```python
from promptfmt import format_file, format_content, FmtConfig, is_equivalent

# Format a file
config = FmtConfig(delimiter_style="---", variable_style="double_brace")
result = format_file("prompts/greeting.yaml", config)

print(result.changed)      # True if content changed
print(result.equivalent)   # True if semantically equivalent
print(result.formatted_content)

# Format raw content
from prompttools_core import PromptFormat
formatted = format_content(content, PromptFormat.YAML, config)

# Check semantic equivalence between two parsed prompts
from prompttools_core import parse_file
original = parse_file("original.yaml")
modified = parse_file("modified.yaml")
print(is_equivalent(original, modified))
```

## CI Integration

### GitHub Actions

```yaml
- name: Check prompt formatting
  run: promptfmt format prompts/ --check
```

### Pre-commit Hook

```bash
#!/bin/sh
promptfmt format prompts/ --check || exit 1
```

### GitLab CI

```yaml
check-prompt-format:
  script:
    - pip install promptfmt-ai
    - promptfmt format prompts/ --check
```

Exit codes:

| Code | Meaning |
|------|---------|
| 0 | All files formatted (or no changes needed) |
| 1 | Files need formatting (with `--check`) |
| 2 | Errors occurred during formatting |

## License

MIT License. Author: Scott Converse.
