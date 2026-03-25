# promptcost

Token budget and cost estimator for LLM prompts.

[![PyPI](https://img.shields.io/badge/PyPI-v1.0.0-blue)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]()
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)]()

## What It Does

`promptcost` estimates the dollar cost of running your LLM prompts against specific models. It provides:

- **Per-invocation cost estimation** with input/output token breakdowns
- **Multi-model comparison** to find the cheapest model for your prompt
- **Volume projections** (daily, monthly, annual costs at a given call rate)
- **Budget enforcement** with pass/fail exit codes for CI
- **Cost delta analysis** to measure the cost impact of prompt changes
- **Pipeline cost estimation** for multi-stage prompt workflows

## Installation

```bash
pip install promptcost-ai
```

**Dependencies:** prompttools-core-ai >= 1.0, typer >= 0.12, rich >= 13.0, pydantic >= 2.0

## CLI Commands

### `promptcost estimate`

Estimate costs for a prompt file or directory.

```bash
# Single file estimation
promptcost estimate prompts/greeting.yaml --model gpt-4o

# Estimate with specific output token count
promptcost estimate prompts/greeting.yaml --model gpt-4o --output-tokens 500

# Estimate with volume projections
promptcost estimate prompts/greeting.yaml --model gpt-4o --project 1000/day

# Compare across multiple models
promptcost estimate prompts/greeting.yaml --compare

# Compare specific models
promptcost estimate prompts/greeting.yaml --models gpt-4o,gpt-4o-mini,claude-4-sonnet

# Estimate all files in a directory
promptcost estimate prompts/ --model gpt-4o

# JSON output
promptcost estimate prompts/greeting.yaml --model gpt-4o --format json
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--model`, `-m` | `claude-4-sonnet` | Model profile for estimation |
| `--output-tokens` | auto | Override estimated output tokens |
| `--project` | none | Project at volume (e.g., `1000/day`, `500/hour`) |
| `--compare` | `false` | Compare across default model set |
| `--models` | none | Comma-separated model list for comparison |
| `--format`, `-f` | `text` | Output format: `text` or `json` |

### `promptcost budget`

Check prompt costs against a per-invocation budget ceiling. Exits with code 1 if any prompt exceeds the budget.

```bash
# Check a single file
promptcost budget prompts/greeting.yaml --limit 0.05 --model gpt-4o

# Check all files in a directory
promptcost budget prompts/ --limit 0.10 --model gpt-4o
```

**Options:**

| Option | Required | Description |
|--------|----------|-------------|
| `--limit`, `-l` | yes | Maximum cost per invocation in USD |
| `--model`, `-m` | no | Model profile (default: `claude-4-sonnet`) |
| `--output-tokens` | no | Override output token estimate |

### `promptcost delta`

Show the cost impact of a prompt change by comparing old and new versions.

```bash
# Basic delta
promptcost delta prompts/old.yaml prompts/new.yaml --model gpt-4o

# Delta with volume projections
promptcost delta prompts/old.yaml prompts/new.yaml --model gpt-4o --volume 1000/day
```

### `promptcost models`

List all available model profiles with pricing information.

```bash
promptcost models
```

Displays a table with model name, provider, context window, input price per million tokens, output price per million tokens, and encoding.

## Output Token Estimation

When `--output-tokens` is not specified, promptcost estimates output tokens using a heuristic based on prompt content keywords:

| Detected keywords | Estimated output | Method |
|-------------------|-----------------|--------|
| `json`, `structured`, `schema`, `format` | 500 tokens | heuristic |
| `brief`, `short`, `concise`, `summary` | 300 tokens | heuristic |
| `detailed`, `comprehensive`, `thorough`, `essay` | 2,000 tokens | heuristic |
| None of the above | 1,000 tokens | heuristic |
| `expected_output_tokens` in prompt metadata | As specified | explicit |

The estimate is capped at the model's `max_output_tokens` limit.

## Volume Projection Formats

The `--project` / `--volume` flag accepts these formats:

| Format | Meaning |
|--------|---------|
| `1000/day` | 1,000 calls per day |
| `500/hour` | 500 calls per hour (converted to per-day) |
| `200/week` | 200 calls per week (converted to per-day) |
| `5000/month` | 5,000 calls per month (converted to per-day) |

Projections are calculated as: daily, monthly (30 days), and annual (365 days).

## Programmatic Usage

```python
from prompttools_core import parse_file, parse_pipeline
from promptcost import (
    estimate_file,
    estimate_pipeline,
    compare_models,
    project_cost,
    check_budget,
)

# Single file estimation
prompt = parse_file("prompts/greeting.yaml")
estimate = estimate_file(prompt, model="gpt-4o")
print(f"Input tokens: {estimate.input_tokens}")
print(f"Est. output tokens: {estimate.estimated_output_tokens}")
print(f"Total cost: ${estimate.total_cost:.4f}")

# Model comparison
comparison = compare_models(prompt, ["gpt-4o", "gpt-4o-mini", "claude-4-sonnet"])
print(f"Cheapest: {comparison.cheapest}")
print(f"Savings: ${comparison.savings_vs_most_expensive:.4f}/call")

# Volume projection
projection = project_cost(estimate, "1000/day")
print(f"Monthly cost: ${projection.monthly_cost:.2f}")

# Budget enforcement
estimates = [estimate_file(pf, "gpt-4o") for pf in parse_directory("prompts/")]
results = check_budget(estimates, budget=0.05)
for r in results:
    print(f"{r.file_path.name}: {'OVER' if r.over_budget else 'OK'}")

# Pipeline estimation
pipeline = parse_pipeline("pipeline.yaml")
pipeline_est = estimate_pipeline(pipeline, model="gpt-4o")
print(f"Pipeline total: ${pipeline_est.total_cost:.4f}")
```

## Data Models

**`CostEstimate`** -- Per-invocation cost for a single prompt.
- `file_path`, `model`, `input_tokens`, `estimated_output_tokens`
- `output_estimation_method` (`"explicit"`, `"heuristic"`, `"max"`)
- `input_cost`, `output_cost`, `total_cost`

**`CostComparison`** -- Comparison across multiple models.
- `file_path`, `input_tokens`, `estimated_output_tokens`
- `estimates: dict[str, CostEstimate]`, `cheapest`, `most_expensive`
- `savings_vs_most_expensive`

**`CostProjection`** -- Volume-based cost projections.
- `volume`, `calls_per_day`, `daily_cost`, `monthly_cost`, `annual_cost`

**`BudgetResult`** -- Budget check result.
- `file_path`, `model`, `estimated_cost`, `budget`, `over_budget`, `overage`

**`CostDelta`** -- Cost impact of a prompt change.
- `file_path`, `model`, `old_estimate`, `new_estimate`
- `cost_change`, `percent_change`, `monthly_impact` (optional)

**`PipelineCostEstimate`** -- Pipeline-level cost estimate.
- `pipeline_name`, `model`, `stages: list[StageCostEstimate]`
- `total_cost`, `cumulative_tokens`

**`StageCostEstimate`** -- Per-stage cost breakdown.
- `stage_name`, `input_tokens`, `estimated_output_tokens`
- `input_cost`, `output_cost`, `total_cost`

## CI Integration

### GitHub Actions -- Budget Gate

```yaml
- name: Check prompt budget
  run: promptcost budget prompts/ --limit 0.10 --model gpt-4o
```

### GitHub Actions -- Cost Delta on PR

```yaml
- name: Check cost impact
  run: |
    git show HEAD~1:prompts/main.yaml > /tmp/old.yaml
    promptcost delta /tmp/old.yaml prompts/main.yaml --model gpt-4o --volume 1000/day
```

Exit codes:

| Code | Meaning |
|------|---------|
| 0 | All prompts within budget / estimation succeeded |
| 1 | One or more prompts exceed budget |
| 2 | Path not found or other error |

## License

MIT License. Author: Scott Converse.
