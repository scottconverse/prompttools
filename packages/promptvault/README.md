# promptvault

Version control and registry for prompt assets. Part of the [prompttools](https://github.com/scottconverse/prompttools) suite.

## Features

- **Package manifests** -- Define prompt packages with `promptvault.yaml`, including metadata, prompt entries, dependencies, and quality gates
- **Local registry** -- Publish, install, search, and list versioned prompt packages in a local file-system registry
- **Dependency resolution** -- Resolve dependencies with semver range matching (caret `^`, tilde `~`, PEP 440 ranges)
- **Lockfile management** -- Generate and verify lockfiles for reproducible installations with integrity checking
- **CLI** -- Full command-line interface for all operations

## Installation

```bash
pip install promptvault-ai
```

## Quick Start

### Initialize a package

```bash
promptvault init --name @my-org/my-prompts --author "Your Name"
```

This creates a `promptvault.yaml` manifest:

```yaml
name: '@my-org/my-prompts'
version: 0.1.0
description: A prompt package
author: Your Name
license: MIT
prompts: []
dependencies: {}
quality:
  lint: optional
  test: optional
  format: optional
```

### Add prompts to the manifest

Edit `promptvault.yaml` to declare your prompt files:

```yaml
prompts:
  - file: prompts/greeting.yaml
    name: greeting
    description: A friendly greeting prompt
    variables: [user_name]
    model: claude-4-sonnet
```

### Publish to local registry

```bash
promptvault publish
```

### Install dependencies

```bash
promptvault install
```

### Search the registry

```bash
promptvault search greeting
```

### Verify lockfile integrity

```bash
promptvault verify
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `promptvault init` | Scaffold a new `promptvault.yaml` manifest |
| `promptvault publish` | Publish the current package to the local registry |
| `promptvault install` | Resolve dependencies and generate a lockfile |
| `promptvault search <query>` | Search the registry catalog |
| `promptvault info <package>` | Show package details |
| `promptvault list` | List all packages in the registry |
| `promptvault verify` | Verify lockfile integrity |

### Global Options

- `--registry <path>` -- Override the default registry location (`~/.promptvault/registry/`)
- `--format text|json` -- Output format (default: `text`)

## Version Ranges

Dependency version ranges follow semver conventions:

| Syntax | Meaning | Example |
|--------|---------|---------|
| `^1.2.3` | Compatible with 1.x.x | `>=1.2.3, <2.0.0` |
| `~1.2.3` | Patch-level changes | `>=1.2.3, <1.3.0` |
| `>=1.0,<2.0` | PEP 440 range | Explicit range |
| `1.2.3` | Exact version | `==1.2.3` |

## Python API

```python
from promptvault import LocalRegistry, PackageManifest, resolve_dependencies

# Create a registry
registry = LocalRegistry()

# Publish a package
entry = registry.publish(Path("./my-package"))

# Search
results = registry.search("greeting")

# Resolve dependencies
manifest = PackageManifest(...)
resolved = resolve_dependencies(manifest, registry)
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
