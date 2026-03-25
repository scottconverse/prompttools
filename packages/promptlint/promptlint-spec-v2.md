# Technical Specification: promptlint v2

## 1. Project Overview

`promptlint` is a static analysis tool (linter) for Large Language Model (LLM) prompts. It treats prompts as code artifacts, analyzing them for token bloat, missing context, security vulnerabilities (prompt injection vectors), hallucination risk, structural inconsistencies, and cross-prompt pipeline integrity.

- **Target Environment:** Python 3.9+
- **Primary Interface:** CLI
- **Core Dependencies:** `typer` (CLI), `pydantic` (Data Models), `pyyaml` (Config/Parsing), `tiktoken` (Token estimation), `rich` (Console output), `watchfiles` (Watch mode)

---

## 2. Architecture & Directory Structure

```text
promptlint/
├── pyproject.toml
├── promptlint/
│   ├── __init__.py
│   ├── cli.py                 # Typer application entry point
│   ├── config.py              # Configuration loading and merging
│   ├── models.py              # Pydantic core data models
│   ├── core/
│   │   ├── __init__.py
│   │   ├── parser.py          # Reads files -> PromptFile objects
│   │   ├── engine.py          # Applies Rules -> LintViolation objects
│   │   ├── reporter.py        # Formats LintViolation objects for output
│   │   ├── fixer.py           # Applies auto-fixes for fixable violations
│   │   └── cache.py           # Token count and parse result caching
│   ├── rules/
│   │   ├── __init__.py
│   │   ├── base.py            # Abstract Base Class for all rules
│   │   ├── token_budget.py    # PL001-PL003
│   │   ├── system_prompt.py   # PL010-PL014
│   │   ├── formatting.py      # PL020-PL024
│   │   ├── variables.py       # PL030-PL033
│   │   ├── pipeline.py        # PL040-PL043
│   │   ├── hallucination.py   # PL050-PL054
│   │   ├── security.py        # PL060-PL063
│   │   ├── smells.py          # PL070-PL074
│   │   └── gates.py           # PL080-PL083
│   ├── plugins/
│   │   ├── __init__.py
│   │   └── loader.py          # Plugin discovery and loading
│   ├── profiles/
│   │   ├── __init__.py
│   │   └── models.py          # Model-specific context windows and tokenizers
│   └── utils/
│       ├── __init__.py
│       └── tokenizers.py      # tiktoken wrapper
└── tests/
    ├── conftest.py
    ├── test_cli.py
    ├── test_parser.py
    ├── test_engine.py
    ├── test_fixer.py
    ├── test_cache.py
    └── rules/
        ├── test_token_budget.py
        ├── test_system_prompt.py
        ├── test_formatting.py
        ├── test_variables.py
        ├── test_pipeline.py
        ├── test_hallucination.py
        ├── test_security.py
        ├── test_smells.py
        └── test_gates.py
```

---

## 3. Core Data Models (`models.py`)

All models are implemented using Pydantic v2.

### `PromptFile`

Represents a single parsed prompt file loaded by the parser.

| Field | Type | Description |
|---|---|---|
| `path` | `Path` | Absolute path to the source file |
| `format` | `PromptFormat` | Detected format enum (`text`, `markdown`, `yaml`, `json`) |
| `raw_content` | `str` | Original unmodified file content |
| `messages` | `list[Message]` | Parsed list of messages (single-item for plain text prompts) |
| `variables` | `dict[str, str]` | Extracted template variables (e.g. `{{variable}}`) |
| `metadata` | `dict[str, Any]` | Optional front-matter or top-level YAML/JSON metadata |
| `total_tokens` | `int \| None` | Total token count across all messages, populated by engine |

### `Message`

Represents a single turn within a prompt.

| Field | Type | Description |
|---|---|---|
| `role` | `str` | One of `system`, `user`, `assistant` |
| `content` | `str` | The text content of the message |
| `line_start` | `int` | Line number where this message begins in the source file |
| `token_count` | `int \| None` | Token count, populated by the engine before rule evaluation |

### `PromptPipeline`

Represents an ordered set of prompt files that form a multi-stage pipeline.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Pipeline name |
| `stages` | `list[PipelineStage]` | Ordered list of stages |
| `manifest_path` | `Path` | Path to the `.promptlint-pipeline.yaml` manifest |
| `total_tokens` | `int \| None` | Sum of all stage token counts |
| `cumulative_tokens` | `list[int] \| None` | Running total at each stage (for context window analysis) |

### `PipelineStage`

Represents one stage in a prompt pipeline.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Stage name (e.g. "prior-art-search") |
| `prompt_file` | `PromptFile` | The parsed prompt file for this stage |
| `depends_on` | `list[str]` | Names of stages whose output this stage consumes |
| `expected_output_tokens` | `int \| None` | Estimated output token count (for context growth analysis) |
| `persona` | `str \| None` | Declared persona/role for this stage |

### `LintViolation`

Represents a single rule violation produced by the engine.

| Field | Type | Description |
|---|---|---|
| `rule_id` | `str` | Rule identifier, e.g. `PL001` |
| `severity` | `Severity` | Enum: `error`, `warning`, `info` |
| `message` | `str` | Human-readable description of the violation |
| `suggestion` | `str \| None` | Optional actionable fix suggestion |
| `path` | `Path` | Source file where the violation was found |
| `line` | `int \| None` | Line number of the violation, if applicable |
| `rule_name` | `str` | Short slug name of the rule, e.g. `token-budget-exceeded` |
| `fixable` | `bool` | Whether this violation can be auto-fixed |

### `LintConfig`

Merged configuration from file + CLI flags + defaults.

| Field | Type | Description |
|---|---|---|
| `model` | `str \| None` | Model profile name (auto-sets context window + tokenizer) |
| `tokenizer_encoding` | `str` | tiktoken encoding name (default: `cl100k_base`) |
| `token_warn_threshold` | `int` | PL001 warning threshold (default: `2048`) |
| `token_error_threshold` | `int` | PL002 error threshold (default: `4096`) |
| `system_prompt_threshold` | `int` | PL014 system prompt threshold (default: `1024`) |
| `stop_word_ratio` | `float` | PL003 stop-word ratio threshold (default: `0.60`) |
| `max_line_length` | `int` | PL024 character limit (default: `500`) |
| `repetition_threshold` | `int` | PL023 occurrence count (default: `3`) |
| `rule_overrides` | `dict[str, str]` | Per-rule severity overrides |
| `ignored_rules` | `list[str]` | Globally ignored rule IDs |
| `exclude_patterns` | `list[str]` | Glob patterns for excluded files |
| `plugin_dirs` | `list[Path]` | Directories containing custom rule plugins |
| `context_window` | `int \| None` | Model context window (auto-set by model profile, or manual) |

### `ModelProfile`

Built-in model configuration for context-aware linting.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Model identifier |
| `context_window` | `int` | Maximum context window in tokens |
| `tokenizer_encoding` | `str` | tiktoken encoding to use |
| `max_output_tokens` | `int` | Typical max output tokens |

### `Severity` (Enum)

```python
class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
```

### `PromptFormat` (Enum)

```python
class PromptFormat(str, Enum):
    TEXT = "text"       # .txt
    MARKDOWN = "md"     # .md
    YAML = "yaml"       # .yaml / .yml
    JSON = "json"       # .json
```

---

## 4. Supported Input Formats (`parser.py`)

The parser detects format by file extension and routes to the appropriate sub-parser. All sub-parsers produce a `PromptFile` object. When reading from stdin (`-`), the `--input-format` flag is required.

| Extension | Format | Parsing Strategy |
|---|---|---|
| `.txt` | `text` | Entire file content becomes a single `user` message |
| `.md` | `markdown` | Optional YAML front-matter stripped into `metadata`; body becomes a single `user` message |
| `.yaml` / `.yml` | `yaml` | Expects a top-level `messages` list with `role`/`content` keys |
| `.json` | `json` | Expects either a top-level `messages` array (OpenAI chat format) or a single `prompt` string |

**YAML format example:**

```yaml
messages:
  - role: system
    content: "You are a helpful assistant."
  - role: user
    content: "Summarize the following: {{input}}"
```

**JSON format example (OpenAI-compatible):**

```json
{
  "messages": [
    { "role": "system", "content": "You are a helpful assistant." },
    { "role": "user",   "content": "Summarize: {{input}}" }
  ]
}
```

### Pipeline Manifest Format

When linting a multi-prompt pipeline, a `.promptlint-pipeline.yaml` manifest declares the stages:

```yaml
# .promptlint-pipeline.yaml
name: "patent-analyzer"
model: "claude-3-sonnet"

stages:
  - name: "technical-intake"
    file: "stage-1-intake.md"
    persona: "U.S. patent attorney"
    expected_output_tokens: 2000

  - name: "prior-art-search"
    file: "stage-2-prior-art.md"
    depends_on: ["technical-intake"]
    persona: "Patent research specialist"
    expected_output_tokens: 4000

  - name: "patentability-analysis"
    file: "stage-3-patentability.md"
    depends_on: ["technical-intake", "prior-art-search"]
    persona: "U.S. patent attorney"
    expected_output_tokens: 3500

  - name: "final-report"
    file: "stage-6-final.md"
    depends_on: ["technical-intake", "prior-art-search", "patentability-analysis"]
    persona: "U.S. patent attorney"
    expected_output_tokens: 6000
```

---

## 5. Rules Reference (`rules/`)

All rules extend the `BaseRule` abstract class defined in `rules/base.py`.

### `BaseRule` Interface

```python
class BaseRule(ABC):
    rule_id: str          # e.g. "PL001"
    name: str             # e.g. "token-budget-warn"
    default_severity: Severity
    fixable: bool = False # Whether this rule supports auto-fix

    @abstractmethod
    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        ...

    def fix(self, prompt_file: PromptFile, violation: LintViolation) -> str | None:
        """Return fixed content, or None if not fixable. Only called if fixable=True."""
        return None
```

For pipeline rules, an additional base class:

```python
class BasePipelineRule(ABC):
    rule_id: str
    name: str
    default_severity: Severity

    @abstractmethod
    def check_pipeline(self, pipeline: PromptPipeline, config: LintConfig) -> list[LintViolation]:
        ...
```

---

### 5.1 Token Budget Rules (`token_budget.py`)

| Rule ID | Name | Default Severity | Description |
|---|---|---|---|
| `PL001` | `token-budget-warn` | `warning` | Total prompt token count exceeds the warning threshold |
| `PL002` | `token-budget-error` | `error` | Total prompt token count exceeds the error threshold |
| `PL003` | `token-density-low` | `info` | Token-to-information ratio is low (high filler content detected via stop-word ratio) |

**Default thresholds (configurable):**

- `PL001` warn threshold: `2048` tokens (auto-adjusted by model profile)
- `PL002` error threshold: `4096` tokens (auto-adjusted by model profile)
- `PL003` stop-word ratio threshold: `0.60` (60% stop words triggers info)

**Model-aware threshold adjustment:**

When a `model` is specified in config, PL001 and PL002 thresholds are set as percentages of the model's context window:
- PL001 warn: 50% of context window
- PL002 error: 80% of context window

Manual thresholds in config override model-based thresholds.

**Tokenizer:** Uses `tiktoken` with the `cl100k_base` encoding (GPT-4 compatible) by default. The encoding is configurable or auto-set by model profile.

---

### 5.2 System Prompt Rules (`system_prompt.py`)

| Rule ID | Name | Default Severity | Description |
|---|---|---|---|
| `PL010` | `system-prompt-missing` | `warning` | No `system` role message found in a multi-message prompt |
| `PL011` | `system-prompt-not-first` | `error` | A `system` message exists but is not the first message in the list |
| `PL012` | `injection-vector-detected` | `error` | Content contains patterns indicative of prompt injection (see pattern list below) |
| `PL013` | `conflicting-instructions` | `warning` | System prompt contains self-contradictory instruction patterns |
| `PL014` | `system-prompt-too-long` | `warning` | System message alone exceeds the system prompt token threshold |

**Default thresholds (configurable):**

- `PL014` system prompt token threshold: `1024` tokens

**Injection detection patterns for `PL012` (regex-based):**

- `ignore (all |previous |above )?(instructions|prompts|rules|constraints)`
- `disregard (your|all) (previous |prior )?(instructions|context)`
- `you are now (a |an )?(?!helpful)`
- `forget (everything|all)( you (know|were told))?`
- `act as (a |an )?(?!(helpful|professional|expert))`
- `new (persona|personality|role|identity):`
- `\[SYSTEM\]`, `<\|system\|>`, `### (SYSTEM|INSTRUCTION)` appearing inside user content
- `enter (developer|debug|admin|god) mode`
- `system override`, `admin mode`, `maintenance mode`

**Conflicting-instructions detection patterns for `PL013`:**

Detects instruction pairs that contradict within the same prompt:

- `always {X}` paired with `never {X}` where `{X}` shares 2+ significant words
- `must {X}` paired with `do not {X}` or `don't {X}` with overlapping scope
- `be concise` / `be brief` paired with `be thorough` / `be detailed` / `be comprehensive`
- `respond only in {format}` paired with `also include {different_format}`
- `do not make assumptions` paired with `fill in any gaps` / `infer what's needed`

Detection method: Extract all imperative instructions (sentences starting with verbs or containing modal verbs: must, should, always, never, do not). Compute pairwise semantic similarity using keyword overlap. Flag pairs with contradictory polarity (affirmative vs. negative) and high topic similarity.

---

### 5.3 Formatting Rules (`formatting.py`)

| Rule ID | Name | Default Severity | Fixable | Description |
|---|---|---|---|---|
| `PL020` | `trailing-whitespace` | `info` | **Yes** | Lines contain trailing whitespace |
| `PL021` | `inconsistent-delimiters` | `warning` | No | Prompt mixes delimiter styles (e.g. `###`, `---`, `===`, XML tags) without consistent pattern |
| `PL022` | `missing-output-format` | `warning` | No | No output format instruction detected in the prompt (no mention of JSON, markdown, list, etc.) |
| `PL023` | `excessive-repetition` | `warning` | No | The same instruction or phrase appears 3+ times across messages |
| `PL024` | `line-too-long` | `info` | No | A single line exceeds the configured character limit |

**Default thresholds (configurable):**

- `PL024` max line length: `500` characters
- `PL023` repetition threshold: `3` occurrences

**Auto-fix for PL020:** Strip trailing whitespace from all lines.

---

### 5.4 Variable Rules (`variables.py`)

| Rule ID | Name | Default Severity | Fixable | Description |
|---|---|---|---|---|
| `PL030` | `undefined-variable` | `error` | No | A `{{variable}}` placeholder is referenced in content but not declared in the `variables` block |
| `PL031` | `unused-variable` | `warning` | No | A variable is declared in the `variables` block but never referenced in any message |
| `PL032` | `variable-no-default` | `info` | No | A variable is declared but has no default value specified |
| `PL033` | `variable-format-inconsistent` | `warning` | **Yes** | Variable placeholder style is mixed (e.g. `{{var}}` and `{var}` and `<var>` used in the same file) |

**Supported variable syntaxes (detected by parser):**

- `{{variable_name}}` (Jinja2 / Langchain style) — preferred
- `{variable_name}` (Python f-string style)
- `<variable_name>` (XML tag style)

**Auto-fix for PL033:** Normalize all variables to `{{variable_name}}` style.

---

### 5.5 Pipeline Rules (`pipeline.py`)

Cross-prompt analysis rules that operate on `PromptPipeline` objects. These rules only fire when a `.promptlint-pipeline.yaml` manifest is present or when linting a directory with `--pipeline` flag.

| Rule ID | Name | Default Severity | Description |
|---|---|---|---|
| `PL040` | `pipeline-no-handoff` | `warning` | Multi-file prompt set has no handoff mechanism (no references to prior stage output) between consecutive stages |
| `PL041` | `pipeline-context-growth` | `warning` | Cumulative token count across pipeline stages exceeds the model's context window. Reports at which stage overflow occurs |
| `PL042` | `pipeline-orphan-reference` | `error` | A prompt references output from a stage name that doesn't exist in the pipeline manifest |
| `PL043` | `pipeline-inconsistent-persona` | `warning` | Different prompts in the same pipeline define conflicting personas without explicit role transition language |

**Detection methods:**

- **PL040**: Scan each non-first stage for references to prior stage outputs. Look for patterns: "from Stage N", "previous output", "above analysis", stage names from the manifest, or handoff markers. If none found in a stage that declares `depends_on`, fire.
- **PL041**: Compute cumulative tokens: `stage_N_input = stage_N_prompt_tokens + sum(expected_output_tokens for all depends_on stages)`. Compare against `context_window` from model profile or config.
- **PL042**: Extract stage name references from prompt content. Compare against manifest stage names. Flag any reference to a non-existent stage.
- **PL043**: Compare `persona` fields across stages. When persona changes between consecutive stages, check for explicit transition language ("You are now...", "In this stage, your role is..."). Flag if persona changes silently.

---

### 5.6 Hallucination Risk Rules (`hallucination.py`)

Rules that detect prompt patterns known to produce unreliable or fabricated outputs.

| Rule ID | Name | Default Severity | Description |
|---|---|---|---|
| `PL050` | `asks-for-specific-numbers` | `warning` | Prompt asks for specific numerical data (search volume, statistics, prices, dates) without providing a data source or tool access |
| `PL051` | `asks-for-urls` | `warning` | Prompt asks model to provide URLs or links (high fabrication risk) |
| `PL052` | `asks-for-citations` | `info` | Prompt asks for citations or references without specifying a verification method |
| `PL053` | `no-uncertainty-instruction` | `warning` | Prompt asks for factual claims but contains no instruction to express uncertainty, flag unverified claims, or distinguish fact from inference |
| `PL054` | `fabrication-prone-task` | `info` | Prompt asks model to generate specific verifiable entities (names, dates, patent numbers, case law, ISBNs, DOIs) that are commonly fabricated |

**Detection patterns:**

- **PL050**: Regex for question patterns requesting numbers: `how many`, `what is the (volume|count|number|rate|percentage)`, `give me the (exact|specific) (number|figure|statistic)` — AND absence of: tool access declaration, data source reference, `{{data}}` variable, "from the provided data" language.
- **PL051**: Regex for URL requests: `provide (a |the )?(url|link|website)`, `include (a |the )?(link|url)`, `point me to`, `where can I find` — AND absence of: web search tool declaration.
- **PL052**: Regex for citation requests: `cite (your )?sources`, `provide references`, `include citations`, `link to (studies|papers|research)`.
- **PL053**: Absence check. If prompt contains factual-task indicators (`analyze`, `report on`, `what is`, `explain`, `describe the state of`) AND does not contain uncertainty instructions (`if unsure`, `flag uncertain`, `distinguish fact from`, `express confidence`, `say "I don't know"`), fire.
- **PL054**: Regex for verifiable entity requests: `provide the (patent|case|ISBN|DOI) number`, `name the (author|researcher|company)`, `what year did`, `who (invented|discovered|founded)`.

---

### 5.7 Security Rules (`security.py`)

| Rule ID | Name | Default Severity | Description |
|---|---|---|---|
| `PL060` | `pii-in-prompt` | `error` | Prompt contains patterns matching PII (email addresses, phone numbers, SSNs) |
| `PL061` | `hardcoded-api-key` | `error` | Prompt contains what appears to be an API key or secret token |
| `PL062` | `no-output-constraints` | `warning` | Prompt has no constraints on what the model should NOT output (no negative instructions) |
| `PL063` | `unbounded-tool-use` | `warning` | Prompt grants tool access without specifying constraints or confirmation requirements |

**Detection patterns:**

- **PL060**: Regex for email (`\b[\w.-]+@[\w.-]+\.\w+\b`), phone (`\b\d{3}[-.]?\d{3}[-.]?\d{4}\b`), SSN (`\b\d{3}-\d{2}-\d{4}\b`), credit card (`\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b`).
- **PL061**: Regex for API key patterns: `sk-[a-zA-Z0-9]{20,}`, `ghp_[a-zA-Z0-9]{36}`, `Bearer [a-zA-Z0-9._-]{20,}`, `key-[a-zA-Z0-9]{32,}`, `AKIA[A-Z0-9]{16}` (AWS), generic long hex/base64 strings preceded by "key", "token", "secret", or "password".
- **PL062**: Absence check. If total tokens > 200 AND prompt contains no negative constraint language (`do not`, `never`, `must not`, `avoid`, `refuse to`, `don't`), fire.
- **PL063**: If prompt mentions tool access (`use tools`, `you have access to`, `call the`, `execute`, `run the`) AND contains no constraint language (`only when`, `confirm before`, `ask permission`, `do not use.*without`, `limit.*to`), fire.

---

### 5.8 Prompt Smell Rules (`smells.py`)

Structural patterns indicating prompt quality problems, analogous to code smells.

| Rule ID | Name | Default Severity | Description |
|---|---|---|---|
| `PL070` | `ambiguous-quantifier` | `info` | Prompt uses vague quantifiers ("some", "a few", "several", "many", "various") where specificity would improve output |
| `PL071` | `instruction-buried` | `warning` | Critical instruction (MUST, NEVER, ALWAYS, IMPORTANT, CRITICAL) appears past the 75th percentile of the prompt by token count |
| `PL072` | `competing-instructions` | `warning` | Prompt contains both affirmative and negative statements about similar topics without explicit priority |
| `PL073` | `no-examples` | `info` | Prompt over 500 tokens contains no examples, demonstrations, or few-shot patterns |
| `PL074` | `wall-of-text` | `warning` | Prompt has no structural markers (headers, bullets, delimiters, numbered lists) and exceeds 200 tokens |

**Detection methods:**

- **PL070**: Regex for vague quantifiers in instruction context: `(include|provide|give|add|list) (some|a few|several|many|various|multiple)`. Fire only when the quantifier modifies a deliverable, not when used in descriptions.
- **PL071**: Locate critical keywords (case-insensitive: `must`, `never`, `always`, `important`, `critical`, `mandatory`, `required`). Compute their position as a percentage of total tokens. Fire if any appear after 75%.
- **PL072**: Similar to PL013 but broader scope — checks all messages, not just system prompt. Uses the same contradiction detection engine but with lower confidence threshold.
- **PL073**: Check for example indicators: `for example`, `e.g.`, `such as`, `here is an example`, `sample input`, `sample output`, code blocks, `Input:.*Output:` patterns. Fire if none found and total tokens > 500.
- **PL074**: Check for structural markers: markdown headers (`#`), bullet points (`-`, `*`, `•`), numbered lists (`1.`, `a)`), delimiters (`---`, `###`, `===`), XML tags. Fire if none found and total tokens > 200.

---

### 5.9 Gate/Constraint Rules (`gates.py`)

Detect and validate prompt gate patterns — conditional logic that controls model behavior.

| Rule ID | Name | Default Severity | Description |
|---|---|---|---|
| `PL080` | `gate-no-enforcement` | `warning` | Prompt defines conditional logic ("if X is missing", "when X is not provided") but has no hard stop instruction ("do not proceed", "stop", "block", "refuse") |
| `PL081` | `gate-no-fallback` | `info` | Prompt declares a required tool or capability ("requires web search", "use the API") but has no fallback instruction if that capability is unavailable |
| `PL082` | `output-schema-missing` | `warning` | Prompt specifies structured output ("respond in JSON", "use this format") but provides no schema, template, or example of the expected structure |
| `PL083` | `claim-no-evidence-gate` | `info` | Prompt asks model to make factual claims or recommendations but has no instruction to substantiate, source, or express confidence |

**Detection methods:**

- **PL080**: Find conditional patterns: `if .*(missing|absent|not provided|unavailable|unclear)`, `when .*(no|without|lacking)`. Check if within 3 sentences there is enforcement language: `do not (proceed|continue|generate)`, `stop`, `block`, `refuse`, `halt`, `wait`. Fire if conditional exists without nearby enforcement.
- **PL081**: Find capability declarations: `requires? (web search|tool|API|database|internet)`, `you have access to`, `using (the )?(\w+ )(tool|API|function)`. Check for fallback: `if .*(unavailable|not available|cannot access)`. Fire if capability declared without fallback.
- **PL082**: Find format specifications: `respond in (JSON|XML|YAML|CSV|markdown|table)`, `use (this|the following) format`, `output (as|in) `. Check for schema: code blocks, example outputs, field definitions, key-value templates. Fire if format specified without schema within 10 lines.
- **PL083**: Find claim-generating instructions: `analyze`, `recommend`, `assess`, `evaluate`, `determine whether`, `rate`, `score`, `rank`. Check for evidence language: `based on`, `cite`, `source`, `evidence`, `confidence`, `verified`, `if unsure`. Fire if claims requested without evidence instruction.

---

## 6. Configuration (`config.py`)

Configuration is loaded from a `.promptlint.yaml` file, walking up from the target directory to the project root. CLI flags override file config. All fields are optional.

### Full `.promptlint.yaml` Schema

```yaml
# .promptlint.yaml

# Model profile (auto-sets context window + tokenizer)
# Overrides tokenizer.encoding and token thresholds
model: "claude-3-sonnet"

# Tokenizer settings (manual override)
tokenizer:
  encoding: "cl100k_base"   # tiktoken encoding name

# Token budget thresholds
token_budget:
  warn_threshold: 2048
  error_threshold: 4096
  system_prompt_threshold: 1024
  stop_word_ratio: 0.60

# Formatting thresholds
formatting:
  max_line_length: 500
  repetition_threshold: 3

# Per-rule severity overrides (use rule ID or name)
rules:
  PL003: "error"         # Promote a rule to error
  PL022: "ignore"        # Silence a rule entirely
  trailing-whitespace: "ignore"

# Globally ignored rule IDs
ignore:
  - PL020
  - PL024

# Paths to exclude (glob patterns)
exclude:
  - "tests/fixtures/**"
  - "**/*.bak"

# Plugin directories for custom rules
plugins:
  - "./custom_rules/"
  - "/shared/team-rules/"

# Cache settings
cache:
  enabled: true
  directory: ".promptlint-cache"
```

### Config Merging Priority (highest to lowest)

1. CLI flags (`--select`, `--ignore`, `--format`, `--model`)
2. `.promptlint.yaml` in the target directory or nearest ancestor
3. Model profile defaults (if `model` specified)
4. Built-in defaults

---

## 7. Model Profiles (`profiles/models.py`)

Built-in model profiles that auto-configure context windows and tokenizers.

| Profile Name | Context Window | Tokenizer | Max Output | Notes |
|---|---|---|---|---|
| `gpt-4` | 8,192 | `cl100k_base` | 4,096 | |
| `gpt-4-turbo` | 128,000 | `cl100k_base` | 4,096 | |
| `gpt-4o` | 128,000 | `o200k_base` | 16,384 | |
| `claude-3-haiku` | 200,000 | `cl100k_base` | 4,096 | Approximate tokenizer |
| `claude-3-sonnet` | 200,000 | `cl100k_base` | 8,192 | Approximate tokenizer |
| `claude-3-opus` | 200,000 | `cl100k_base` | 4,096 | Approximate tokenizer |
| `claude-4-sonnet` | 200,000 | `cl100k_base` | 64,000 | Approximate tokenizer |
| `gemini-1.5-pro` | 1,000,000 | `cl100k_base` | 8,192 | Approximate tokenizer |
| `gemini-2.0-flash` | 1,000,000 | `cl100k_base` | 8,192 | Approximate tokenizer |

When `model` is set:
- `tokenizer_encoding` auto-set from profile
- `token_warn_threshold` set to `context_window * 0.5`
- `token_error_threshold` set to `context_window * 0.8`
- PL041 (pipeline context growth) uses `context_window` for overflow detection

---

## 8. Plugin System (`plugins/loader.py`)

Custom rules extend the linter for team-specific or domain-specific prompt standards.

### Plugin Discovery

1. Scan each directory listed in `config.plugins`
2. Import every `.py` file in those directories
3. Find all classes that subclass `BaseRule` or `BasePipelineRule`
4. Register them in the rule engine alongside built-in rules
5. Rule IDs for plugins must start with `PLX` (e.g. `PLX001`) to avoid collision with built-in rules

### Plugin Rule Example

```python
# custom_rules/my_team_rules.py
from promptlint.rules.base import BaseRule
from promptlint.models import PromptFile, LintViolation, LintConfig, Severity

class RequireTeamHeader(BaseRule):
    rule_id = "PLX001"
    name = "team-header-missing"
    default_severity = Severity.WARNING

    def check(self, prompt_file: PromptFile, config: LintConfig) -> list[LintViolation]:
        if "## Team:" not in prompt_file.raw_content:
            return [LintViolation(
                rule_id=self.rule_id,
                severity=self.default_severity,
                message="Prompt is missing the required '## Team:' header.",
                suggestion="Add a '## Team: <team-name>' header at the top of the prompt.",
                path=prompt_file.path,
                line=1,
                rule_name=self.name,
                fixable=False,
            )]
        return []
```

---

## 9. Auto-Fix System (`core/fixer.py`)

When invoked with `--fix`, the engine applies auto-fixes for fixable violations.

### Fixable Rules

| Rule | Fix Action |
|---|---|
| PL020 `trailing-whitespace` | Strip trailing whitespace from all lines |
| PL033 `variable-format-inconsistent` | Normalize all variables to `{{variable_name}}` style |
| PL011 `system-prompt-not-first` | Move system message to first position (YAML/JSON formats only) |

### Fix Process

1. Run all rules and collect violations
2. Filter to fixable violations only
3. For each fixable violation, call `rule.fix(prompt_file, violation)`
4. Write modified content back to file
5. Re-run lint to verify fix resolved the violation
6. Report: `Fixed N violations in M files. N remaining unfixable violations.`

### Safety

- `--fix` writes to original files. Use `--fix --dry-run` to preview changes without writing.
- Fixes are applied in rule-ID order to avoid conflicts.
- If a fix introduces a new violation, it is reported but not reverted.

---

## 10. Cache System (`core/cache.py`)

For large prompt directories, caching avoids re-tokenizing unchanged files.

### Cache Key

`SHA256(file_content + tokenizer_encoding)` → stored token count and parse result.

### Cache Storage

JSON file at `.promptlint-cache/cache.json`:

```json
{
  "version": 1,
  "entries": {
    "a1b2c3d4...": {
      "path": "prompts/stage-1.md",
      "token_count": 1847,
      "timestamp": "2026-03-17T12:00:00Z"
    }
  }
}
```

### Cache Behavior

- `--cache` flag enables caching (default: off)
- `--clear-cache` clears the cache directory
- Cache is invalidated when file content changes (SHA256 mismatch)
- Cache is invalidated when tokenizer encoding changes

---

## 11. CLI Interface (`cli.py`)

Entry point registered as `promptlint` via `pyproject.toml`.

### Commands

#### `promptlint check <path> [OPTIONS]`

Lint one or more prompt files or directories.

| Option | Type | Default | Description |
|---|---|---|---|
| `path` | `Path` (arg, required) | — | File or directory to lint. Use `-` to read from stdin |
| `--config` / `-c` | `Path` | auto-discover | Path to a `.promptlint.yaml` config file |
| `--format` / `-f` | `str` | `text` | Output format: `text`, `json`, `github` |
| `--input-format` | `str` | auto-detect | Force input format when reading from stdin: `text`, `md`, `yaml`, `json` |
| `--model` / `-m` | `str` | none | Model profile name (overrides config file) |
| `--select` | `str` | all rules | Comma-separated rule IDs to enable (e.g. `PL001,PL012`) |
| `--ignore` | `str` | none | Comma-separated rule IDs to suppress |
| `--min-severity` | `str` | `info` | Minimum severity to report: `info`, `warning`, `error` |
| `--no-color` | flag | false | Disable rich color output |
| `--quiet` / `-q` | flag | false | Only print errors, suppress warnings and info |
| `--stats` | flag | false | Print a rule-hit summary table after violations |
| `--fix` | flag | false | Apply auto-fixes for fixable violations |
| `--dry-run` | flag | false | With `--fix`: preview fixes without writing |
| `--pipeline` | flag | false | Treat directory as a pipeline (requires manifest or auto-detect) |
| `--baseline` | `Path` | none | Path to a previous JSON report; only show new violations |
| `--cache` | flag | false | Enable token count caching |

#### `promptlint watch <path> [OPTIONS]`

Monitor files for changes and re-lint on save.

| Option | Type | Default | Description |
|---|---|---|---|
| `path` | `Path` (arg, required) | — | File or directory to watch |
| `--config` / `-c` | `Path` | auto-discover | Path to config file |
| `--min-severity` | `str` | `warning` | Minimum severity to report during watch |
| `--clear` | flag | true | Clear terminal before each re-lint |

Behavior: Uses `watchfiles` to monitor `.txt`, `.md`, `.yaml`, `.yml`, `.json` files. On change, re-lints only the changed file (or full pipeline if `--pipeline`). Displays results with `rich.live` for clean output.

#### `promptlint rules [OPTIONS]`

List all available rules, including plugins.

| Option | Type | Description |
|---|---|---|
| `--format` | `str` | Output as `text` (default) or `json` |
| `--category` | `str` | Filter by category: `token`, `system`, `formatting`, `variable`, `pipeline`, `hallucination`, `security`, `smell`, `gate`, `plugin` |

#### `promptlint init`

Scaffold a `.promptlint.yaml` with all defaults in the current directory.

#### `promptlint init-pipeline`

Scaffold a `.promptlint-pipeline.yaml` manifest by scanning the current directory for prompt files.

---

## 12. Reporter & Output Formats (`reporter.py`)

### `text` (default)

Rich-formatted human-readable output, one violation per line:

```
path/to/prompt.yaml:12  [error]  PL012  injection-vector-detected
  → Content matches injection pattern: "ignore all previous instructions"
  ✦ Suggestion: Remove or sanitize instruction-override language from user-facing content.

path/to/prompt.yaml:1   [warning] PL010  system-prompt-missing
  → No system role message found.
  ✦ Suggestion: Add a system message to define assistant behavior.

path/to/prompt.yaml      [warning] PL053  no-uncertainty-instruction
  → Prompt asks for factual claims but contains no uncertainty instruction.
  ✦ Suggestion: Add "If unsure, say so" or "Distinguish verified facts from inferences."

Found 3 violations (1 error, 2 warnings, 0 info) in 1 file.
```

With `--stats`:

```
Rule Summary:
  PL012  injection-vector-detected     1 error
  PL010  system-prompt-missing          1 warning
  PL053  no-uncertainty-instruction     1 warning
```

### `json`

Machine-readable JSON array, one object per violation:

```json
[
  {
    "rule_id": "PL012",
    "rule_name": "injection-vector-detected",
    "severity": "error",
    "path": "path/to/prompt.yaml",
    "line": 12,
    "message": "Content matches injection pattern: \"ignore all previous instructions\"",
    "suggestion": "Remove or sanitize instruction-override language from user-facing content.",
    "fixable": false
  }
]
```

### `github`

GitHub Actions annotation format for use in CI workflows:

```
::error file=path/to/prompt.yaml,line=12,title=PL012::injection-vector-detected: Content matches injection pattern.
::warning file=path/to/prompt.yaml,line=1,title=PL010::system-prompt-missing: No system role message found.
```

---

## 13. Baseline/Diff Mode

When `--baseline <path>` is provided:

1. Load the baseline JSON report
2. Run full lint
3. Compare violations by `(rule_id, path, line, message)` tuple
4. Report only violations NOT present in the baseline
5. Exit code reflects new violations only

Use case: CI pipelines where legacy prompts have known issues. Only new violations block the build.

---

## 14. Exit Codes

| Code | Meaning |
|---|---|
| `0` | No violations found (or all violations below `--min-severity`) |
| `1` | One or more lint violations found |
| `2` | Tool error (bad config, unreadable file, parse failure) |

---

## 15. `pyproject.toml` Requirements

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "promptlint"
version = "0.2.0"
description = "Static analysis tool for LLM prompts"
requires-python = ">=3.9"
dependencies = [
    "typer[all]>=0.12",
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "tiktoken>=0.7",
    "rich>=13.0",
    "watchfiles>=0.21",
]

[project.scripts]
promptlint = "promptlint.cli:app"

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov",
    "ruff",
    "mypy",
]
```

---

## 16. Testing Requirements (`tests/`)

### `conftest.py`

Must define reusable `pytest` fixtures including: `sample_text_prompt`, `sample_yaml_prompt`, `sample_json_prompt`, `sample_prompt_with_injection`, `sample_prompt_with_variables`, `sample_pipeline` (multi-stage), `sample_prompt_with_hallucination_risk`, `sample_prompt_with_pii`, and a `default_config` fixture returning a `LintConfig` with all defaults.

### Coverage Targets

| Module | Required Coverage |
|---|---|
| `models.py` | 100% |
| `parser.py` | 95% |
| `engine.py` | 95% |
| `rules/*.py` | 90% per file |
| `cli.py` | 80% |
| `reporter.py` | 85% |
| `fixer.py` | 90% |
| `cache.py` | 85% |
| `plugins/loader.py` | 85% |

Each rule must have at minimum: one test that confirms it **fires** on a violating input, and one test that confirms it **does not fire** on a clean input.

Pipeline rules must additionally test: a clean pipeline that passes, a pipeline with each specific violation, and edge cases (single-stage pipeline, circular dependencies).
