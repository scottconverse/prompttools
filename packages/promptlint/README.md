# promptlint

Static analysis tool for LLM prompts — treats prompts as code.

---

> **Disclaimer:** This software is provided as-is, without warranty of any kind. `promptlint` is a static analysis tool — it identifies potential issues in prompt files but does not guarantee that analyzed prompts are secure, correct, or free of vulnerabilities. Lint results are advisory, not authoritative. Always apply your own judgment before relying on any automated analysis. See the [Terms of Service](docs/terms.html) for complete legal terms.

---

## What It Does

`promptlint` analyzes LLM prompts for:

- **Token bloat** — warns when prompts approach model context limits
- **Security vulnerabilities** — detects prompt injection patterns, PII, hardcoded API keys
- **Hallucination risk** — flags prompts that ask for specific numbers, URLs, or citations without data sources
- **Structural issues** — missing system prompts, inconsistent delimiters, no output format specified
- **Variable problems** — undefined variables, unused declarations, mixed placeholder formats
- **Prompt smells** — buried instructions, ambiguous quantifiers, wall-of-text prompts with no structure
- **Gate integrity** — conditional logic without enforcement, missing fallbacks for required tools
- **Pipeline analysis** — cross-prompt handoff drift, context window overflow, persona inconsistency

## Installation

```bash
pip install promptlint-ai
```

## Quick Start

```bash
# Lint a single file
promptlint check my-prompt.yaml

# Lint a directory
promptlint check prompts/

# Lint with model-aware thresholds
promptlint check prompts/ --model claude-3-sonnet

# Lint a multi-prompt pipeline
promptlint check prompts/ --pipeline

# Auto-fix fixable issues
promptlint check prompts/ --fix

# List all rules
promptlint rules

# Create a config file
promptlint init
```

## Supported Formats

| Format | Extensions | Structure |
|--------|-----------|-----------|
| Text | `.txt` | Entire file as single user message |
| Markdown | `.md` | Optional YAML frontmatter + body |
| YAML | `.yaml`, `.yml` | `messages` list with `role`/`content` |
| JSON | `.json` | OpenAI chat format or `prompt` string |

## Rules (34 built-in)

| Category | IDs | What It Checks |
|----------|-----|---------------|
| Token Budget | PL001-003 | Token count thresholds, filler content density |
| System Prompt | PL010-014 | Missing/misplaced system prompt, injection vectors, conflicting instructions |
| Formatting | PL020-024 | Trailing whitespace, inconsistent delimiters, missing output format, repetition |
| Variables | PL030-033 | Undefined/unused variables, missing defaults, mixed formats |
| Pipeline | PL040-043 | Handoff gaps, context overflow, orphan references, persona drift |
| Hallucination | PL050-054 | Requests for numbers/URLs/citations without data, no uncertainty instructions |
| Security | PL060-063 | PII in prompts, API keys, no output constraints, unbounded tool use |
| Smells | PL070-074 | Ambiguous quantifiers, buried instructions, no examples, wall of text |
| Gates | PL080-083 | Conditional logic without enforcement, missing fallbacks, no evidence gates |
| Tokenizer | PL090 | Warns when model profile uses an approximate tokenizer (Claude, Gemini) |

## Configuration

Create `.promptlint.yaml` in your project:

```yaml
model: "claude-3-sonnet"

token_budget:
  warn_threshold: 2048
  error_threshold: 4096

rules:
  PL003: "error"
  PL022: "ignore"

ignore:
  - PL020
  - PL024

exclude:
  - "tests/**"
```

Or run `promptlint init` to scaffold one with defaults.

## Pipeline Linting

For multi-prompt systems, create `.promptlint-pipeline.yaml`:

```yaml
name: "my-pipeline"
model: "claude-3-sonnet"

stages:
  - name: "research"
    file: "stage-1-research.yaml"
    persona: "Research analyst"
    expected_output_tokens: 3000

  - name: "analysis"
    file: "stage-2-analysis.yaml"
    depends_on: ["research"]
    persona: "Senior analyst"
    expected_output_tokens: 4000
```

Then run:

```bash
promptlint check . --pipeline
```

## Model Profiles

Set `--model` to auto-configure context windows and tokenizers:

| Profile | Context Window | Tokenizer |
|---------|---------------|-----------|
| `gpt-4` | 8,192 | cl100k_base |
| `gpt-4-turbo` | 128,000 | cl100k_base |
| `gpt-4o` | 128,000 | o200k_base |
| `claude-3-sonnet` | 200,000 | cl100k_base |
| `claude-4-sonnet` | 200,000 | cl100k_base |
| `gemini-1.5-pro` | 1,000,000 | cl100k_base |

## Output Formats

```bash
# Human-readable (default)
promptlint check prompts/

# JSON for scripting
promptlint check prompts/ --format json

# GitHub Actions annotations
promptlint check prompts/ --format github
```

## CI Integration

```yaml
# .github/workflows/lint-prompts.yml
- name: Lint prompts
  run: promptlint check prompts/ --format github --min-severity warning
```

Use `--baseline` to only fail on new violations:

```bash
promptlint check prompts/ --baseline previous-report.json --format json > current-report.json
```

## Custom Rules (Plugins)

```python
# custom_rules/my_rule.py
from promptlint.rules.base import BaseRule
from promptlint.models import PromptFile, LintViolation, LintConfig, Severity

class RequireTeamHeader(BaseRule):
    rule_id = "PLX001"
    name = "team-header-missing"
    default_severity = Severity.WARNING

    def check(self, prompt_file, config):
        if "## Team:" not in prompt_file.raw_content:
            return [LintViolation(
                rule_id=self.rule_id, severity=self.default_severity,
                message="Missing '## Team:' header.",
                suggestion="Add '## Team: <name>' to the prompt.",
                path=prompt_file.path, line=1, rule_name=self.name, fixable=False,
            )]
        return []
```

```yaml
# .promptlint.yaml
plugins:
  - "./custom_rules/"
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No violations (or all below `--min-severity`) |
| 1 | Violations found |
| 2 | Tool error (bad config, parse failure) |

## License

MIT
