# prompttools-core

Shared foundation library for the prompttools suite.

[![PyPI](https://img.shields.io/badge/PyPI-v1.0.0-blue)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]()
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)]()

## What It Provides

`prompttools-core` is the shared library used by all tools in the prompttools suite (`promptfmt`, `promptcost`, `prompttest`, `promptlint`). It provides:

- **Multi-format prompt parsing** -- YAML, JSON, Markdown, and plain text
- **Tokenization engine** -- tiktoken-based token counting with model-aware encoding selection
- **Model profiles** -- Built-in profiles for OpenAI, Anthropic, and Google models with pricing and context window data
- **Configuration system** -- Hierarchical config file discovery and merging
- **Content caching** -- SHA256-based file-system cache to avoid redundant computation
- **Plugin system** -- Discover and load custom plugin classes from directories
- **Template variable extraction** -- Detects `{{var}}`, `{var}`, and `<var>` syntax across all formats

## Installation

```bash
pip install prompttools-core
```

**Dependencies:** pydantic >= 2.0, pyyaml >= 6.0, tiktoken >= 0.7

## Supported Formats

| Extension | Format | Description |
|-----------|--------|-------------|
| `.yaml`, `.yml` | YAML | Structured messages with front-matter metadata |
| `.json` | JSON | Structured messages with metadata |
| `.md` | Markdown | Heading-delimited message sections |
| `.txt` | Text | Plain text, single or `---` delimited messages |

## API Reference

### Parsing

```python
from prompttools_core import parse_file, parse_directory, parse_stdin, parse_pipeline

# Parse a single prompt file (auto-detects format from extension)
prompt = parse_file("prompts/greeting.yaml")

# Parse from stdin
prompt = parse_stdin(content, format="yaml")  # format: text, md, yaml, json

# Parse all prompt files in a directory
prompts = parse_directory("prompts/")

# Parse a pipeline manifest
pipeline = parse_pipeline("pipeline.yaml")
```

**`parse_file(path, config=None) -> PromptFile`**
Parse a prompt file, auto-detecting format by extension. Raises `ParseError` for unsupported formats and `FileNotFoundError` if the file does not exist.

**`parse_directory(path, config=None, patterns=None) -> list[PromptFile]`**
Recursively parse all prompt files in a directory. Skips files that fail to parse. Respects `config.exclude` patterns.

**`parse_stdin(content, format) -> PromptFile`**
Parse prompt content from stdin. The `format` parameter must be one of: `text`, `md`, `yaml`, `json`.

**`parse_pipeline(manifest_path, config=None) -> PromptPipeline`**
Parse a pipeline manifest YAML and all referenced prompt files. The manifest defines stages with `name`, `file`, `depends_on`, `expected_output_tokens`, and `persona` fields.

### Tokenization

```python
from prompttools_core import Tokenizer, count_tokens, get_encoding

# Quick token count
tokens = count_tokens("Hello, world!", encoding="cl100k_base")

# Model-aware tokenizer
tokenizer = Tokenizer.for_model("gpt-4o")
tokens = tokenizer.count("Some text")

# Count tokens for a full prompt file (populates token_count on each message)
total = tokenizer.count_file(prompt)

# Count tokens across messages including role overhead
total = tokenizer.count_messages(prompt.messages)
```

**`Tokenizer(encoding="cl100k_base", provider="default")`**
Create a tokenizer with a specific encoding. The `provider` parameter controls per-message role overhead (OpenAI: 4 tokens, Anthropic: 3, Google: 3).

**`Tokenizer.for_model(model_name) -> Tokenizer`**
Factory method that looks up the model profile and creates a tokenizer with the correct encoding and provider.

**`count_tokens(text, encoding="cl100k_base") -> int`**
Standalone convenience function to count tokens in a string.

### Model Profiles

```python
from prompttools_core import get_profile, list_profiles, register_profile, ModelProfile

# Look up a built-in profile
profile = get_profile("gpt-4o")
print(f"Context: {profile.context_window}, Encoding: {profile.encoding}")
print(f"Input: ${profile.input_price_per_mtok}/Mtok")

# List all profiles
for name, p in list_profiles().items():
    print(f"{name}: {p.provider}, {p.context_window} tokens")

# Register a custom profile
register_profile(ModelProfile(
    name="my-model",
    context_window=32000,
    encoding="cl100k_base",
    provider="custom",
    input_price_per_mtok=1.0,
    output_price_per_mtok=3.0,
))
```

#### Built-in Profiles

| Model | Provider | Context | Encoding | Input $/Mtok | Output $/Mtok |
|-------|----------|---------|----------|-------------|--------------|
| gpt-4 | openai | 8,192 | cl100k_base | $30.00 | $60.00 |
| gpt-4-turbo | openai | 128,000 | cl100k_base | $10.00 | $30.00 |
| gpt-4o | openai | 128,000 | o200k_base | $2.50 | $10.00 |
| gpt-4o-mini | openai | 128,000 | o200k_base | $0.15 | $0.60 |
| claude-3-haiku | anthropic | 200,000 | cl100k_base | $0.25 | $1.25 |
| claude-3-sonnet | anthropic | 200,000 | cl100k_base | $3.00 | $15.00 |
| claude-3-opus | anthropic | 200,000 | cl100k_base | $15.00 | $75.00 |
| claude-4-sonnet | anthropic | 200,000 | cl100k_base | $3.00 | $15.00 |
| gemini-1.5-pro | google | 1,000,000 | cl100k_base | $1.25 | $5.00 |
| gemini-2.0-flash | google | 1,048,576 | cl100k_base | $0.10 | $0.40 |

Non-OpenAI models use `cl100k_base` as an approximation (indicated by `approximate_tokenizer=True` on the profile).

### Configuration

```python
from prompttools_core import load_config, find_config_file

# Auto-discover and load config
config = load_config(tool_name="fmt", start_dir=Path("."))

# Load with explicit path and CLI overrides
config = load_config(
    tool_name="cost",
    config_path=Path(".prompttools.yaml"),
    cli_overrides={"model": "gpt-4o"},
)
```

**Config file discovery order** (at each directory level, walking upward):

1. `.prompt{tool_name}.yaml` (e.g., `.promptfmt.yaml`)
2. `.prompttools.yaml`
3. `.promptlint.yaml` (backward compatibility)

**Merge priority** (highest to lowest):

1. CLI overrides
2. Config file
3. Model profile defaults
4. Built-in defaults

#### Configuration File Format

```yaml
# .prompttools.yaml
model: gpt-4o
exclude:
  - "vendor/**"
  - "*.generated.*"
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
cost:
  default_output_tokens: 1000
```

### Caching

```python
from prompttools_core import PromptCache

cache = PromptCache(cache_dir=Path(".prompttools-cache"))

# Generate a content-based key
key = PromptCache.content_key(content="Hello", encoding="cl100k_base")

# Store and retrieve values (with optional TTL in seconds)
cache.set(key, 42, ttl=3600)
value = cache.get(key)  # Returns None if expired

# Invalidate a single key or clear all
cache.invalidate(key)
cache.clear()
```

### Plugin System

```python
from prompttools_core import discover_plugins, load_plugin

# Load plugin classes from a single file
classes = load_plugin(Path("my_plugin.py"), base_class=MyBaseClass)

# Discover all plugins in directories
classes = discover_plugins(
    plugin_dirs=[Path("./plugins"), Path("./custom-rules")],
    base_class=MyBaseClass,
)
```

Plugins are Python files containing classes that subclass a given base class. The plugin system is used by promptlint for custom lint rules and by promptfmt for custom formatters.

### Data Models

**`PromptFile`** -- Represents a parsed prompt file.
- `path: Path` -- Source file path
- `format: PromptFormat` -- Detected format (TEXT, MARKDOWN, YAML, JSON)
- `raw_content: str` -- Original file content
- `messages: list[Message]` -- Parsed messages
- `variables: dict[str, str]` -- Template variables mapped to syntax style
- `variable_defaults: dict[str, str]` -- Default values from metadata
- `metadata: dict[str, Any]` -- Front-matter or top-level metadata
- `total_tokens: Optional[int]` -- Populated by tokenizer
- `content_hash: str` -- SHA256 hash of raw_content

**`Message`** -- A single turn in a prompt conversation.
- `role: Literal["system", "user", "assistant", "tool"]`
- `content: str`
- `line_start: Optional[int]`, `line_end: Optional[int]`
- `token_count: Optional[int]`
- `metadata: dict[str, Any]`

**`ModelProfile`** -- Configuration for a specific LLM model.
- `name`, `context_window`, `encoding`, `provider`
- `input_price_per_mtok`, `output_price_per_mtok`
- `max_output_tokens`, `supports_system_message`, `supports_tools`
- `approximate_tokenizer: bool`

**`ToolConfig`** -- Base configuration shared by all tools.
- `model`, `tokenizer_encoding`, `exclude`, `plugins`
- `cache_enabled`, `cache_dir`, `extra`

**`PromptPipeline`** / **`PipelineStage`** -- Multi-stage pipeline support.

### Error Hierarchy

All exceptions inherit from `PromptToolsError`:

- `ParseError` -- File cannot be parsed (also a `ValueError`)
- `ConfigError` -- Configuration is invalid
- `TokenizerError` -- Tokenization fails
- `ProfileNotFoundError` -- Unknown model profile
- `PluginError` -- Plugin loading or execution fails
- `CacheError` -- Cache read/write fails

### Template Variable Extraction

```python
from prompttools_core.parser import extract_variables

vars = extract_variables("Hello {{name}}, your order {id} is in <status>")
# {'name': 'jinja', 'id': 'fstring', 'status': 'xml'}
```

Common HTML tags (`div`, `span`, `p`, etc.) are automatically excluded from XML-style variable detection.

## License

MIT License. Author: Scott Converse.
