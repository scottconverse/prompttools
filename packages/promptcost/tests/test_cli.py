"""CLI-level tests for promptcost using typer.testing.CliRunner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from promptcost.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SIMPLE_PROMPT_YAML = (
    "messages:\n"
    "  - role: system\n"
    '    content: "You are a helpful assistant."\n'
    "  - role: user\n"
    '    content: "Hello world"\n'
)

EXPENSIVE_PROMPT_YAML = (
    "messages:\n"
    "  - role: system\n"
    '    content: "You are a detailed research analyst. Provide a comprehensive, '
    "thorough, and detailed analysis of the topic below. Include citations, "
    "references, methodology, data tables, and a complete bibliography. "
    "Cover every aspect exhaustively. Do not skip any details. "
    'Write at least 5000 words."\n'
    "  - role: user\n"
    '    content: "Analyze the global economic impact of renewable energy."\n'
)


def _write_prompt(tmp_path: Path, name: str, content: str) -> Path:
    f = tmp_path / name
    f.write_text(content, encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# estimate — single file
# ---------------------------------------------------------------------------


class TestEstimateSingleFile:
    def test_estimate_shows_cost_info(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "prompt.yaml", SIMPLE_PROMPT_YAML)
        result = runner.invoke(app, ["estimate", str(f)])
        assert result.exit_code == 0
        assert "Cost per invocation" in result.output or "cost" in result.output.lower()

    def test_estimate_shows_token_count(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "prompt.yaml", SIMPLE_PROMPT_YAML)
        result = runner.invoke(app, ["estimate", str(f)])
        assert result.exit_code == 0
        assert "token" in result.output.lower()


# ---------------------------------------------------------------------------
# estimate --model
# ---------------------------------------------------------------------------


class TestEstimateModel:
    def test_estimate_with_model(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "prompt.yaml", SIMPLE_PROMPT_YAML)
        result = runner.invoke(app, ["estimate", "--model", "gpt-4o", str(f)])
        assert result.exit_code == 0
        assert "gpt-4o" in result.output

    def test_estimate_with_different_models(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "prompt.yaml", SIMPLE_PROMPT_YAML)
        for model in ["gpt-4o", "gpt-4o-mini"]:
            result = runner.invoke(
                app, ["estimate", "--model", model, str(f)]
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# estimate --compare
# ---------------------------------------------------------------------------


class TestEstimateCompare:
    def test_compare_shows_comparison_table(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "prompt.yaml", SIMPLE_PROMPT_YAML)
        result = runner.invoke(app, ["estimate", "--compare", str(f)])
        assert result.exit_code == 0
        assert "Cheapest" in result.output or "cheapest" in result.output.lower()

    def test_compare_with_specific_models(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "prompt.yaml", SIMPLE_PROMPT_YAML)
        result = runner.invoke(
            app,
            ["estimate", "--compare", "--models", "gpt-4o,gpt-4o-mini", str(f)],
        )
        assert result.exit_code == 0

    def test_compare_shows_savings(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "prompt.yaml", SIMPLE_PROMPT_YAML)
        result = runner.invoke(app, ["estimate", "--compare", str(f)])
        assert result.exit_code == 0
        assert "Saving" in result.output or "saving" in result.output.lower()


# ---------------------------------------------------------------------------
# estimate --project
# ---------------------------------------------------------------------------


class TestEstimateProject:
    def test_project_volume(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "prompt.yaml", SIMPLE_PROMPT_YAML)
        result = runner.invoke(
            app, ["estimate", "--project", "1000/day", str(f)]
        )
        assert result.exit_code == 0
        assert "Daily" in result.output or "Monthly" in result.output


# ---------------------------------------------------------------------------
# estimate --format json
# ---------------------------------------------------------------------------


class TestEstimateFormatJson:
    def test_json_output_is_valid(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "prompt.yaml", SIMPLE_PROMPT_YAML)
        result = runner.invoke(
            app, ["estimate", "--format", "json", str(f)]
        )
        assert result.exit_code == 0
        # Output should be parseable JSON
        data = json.loads(result.output)
        assert "input_tokens" in data
        assert "total_cost" in data

    def test_compare_json_output(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "prompt.yaml", SIMPLE_PROMPT_YAML)
        result = runner.invoke(
            app,
            ["estimate", "--format", "json", "--compare", str(f)],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "estimates" in data or "cheapest" in data


# ---------------------------------------------------------------------------
# estimate --output-tokens
# ---------------------------------------------------------------------------


class TestEstimateOutputTokens:
    def test_explicit_output_tokens(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "prompt.yaml", SIMPLE_PROMPT_YAML)
        result = runner.invoke(
            app, ["estimate", "--output-tokens", "500", str(f)]
        )
        assert result.exit_code == 0

    def test_explicit_output_tokens_json(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "prompt.yaml", SIMPLE_PROMPT_YAML)
        result = runner.invoke(
            app,
            ["estimate", "--format", "json", "--output-tokens", "500", str(f)],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["estimated_output_tokens"] == 500
        assert data["output_estimation_method"] == "explicit"


# ---------------------------------------------------------------------------
# budget — under budget
# ---------------------------------------------------------------------------


class TestBudgetUnder:
    def test_budget_ok(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "prompt.yaml", SIMPLE_PROMPT_YAML)
        # Use a very high limit so the prompt is under budget
        result = runner.invoke(
            app, ["budget", "--limit", "10.0", str(f)]
        )
        assert result.exit_code == 0
        assert "OK" in result.output


# ---------------------------------------------------------------------------
# budget — over budget
# ---------------------------------------------------------------------------


class TestBudgetOver:
    def test_budget_over(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "prompt.yaml", SIMPLE_PROMPT_YAML)
        # Use an impossibly low limit
        result = runner.invoke(
            app, ["budget", "--limit", "0.0000001", str(f)]
        )
        assert result.exit_code == 1
        assert "OVER" in result.output


# ---------------------------------------------------------------------------
# budget — directory
# ---------------------------------------------------------------------------


class TestBudgetDirectory:
    def test_budget_directory(self, tmp_path: Path):
        _write_prompt(tmp_path, "a.yaml", SIMPLE_PROMPT_YAML)
        _write_prompt(tmp_path, "b.yaml", SIMPLE_PROMPT_YAML)
        result = runner.invoke(
            app, ["budget", "--limit", "10.0", str(tmp_path)]
        )
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# models
# ---------------------------------------------------------------------------


class TestModels:
    def test_models_lists_profiles(self):
        result = runner.invoke(app, ["models"])
        assert result.exit_code == 0
        assert "gpt-4o" in result.output or "Model" in result.output

    def test_models_shows_pricing(self):
        result = runner.invoke(app, ["models"])
        assert result.exit_code == 0
        # Should show a table with pricing columns
        assert "$" in result.output or "Mtok" in result.output


# ---------------------------------------------------------------------------
# delta
# ---------------------------------------------------------------------------


class TestDelta:
    def test_delta_two_files(self, tmp_path: Path):
        old = _write_prompt(tmp_path, "old.yaml", SIMPLE_PROMPT_YAML)
        new = _write_prompt(tmp_path, "new.yaml", EXPENSIVE_PROMPT_YAML)
        result = runner.invoke(app, ["delta", str(old), str(new)])
        assert result.exit_code == 0
        assert "Delta" in result.output or "delta" in result.output.lower()

    def test_delta_same_file(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "prompt.yaml", SIMPLE_PROMPT_YAML)
        result = runner.invoke(app, ["delta", str(f), str(f)])
        assert result.exit_code == 0
        # Cost change should be zero
        assert "+0" in result.output or "0.0%" in result.output

    def test_delta_with_model(self, tmp_path: Path):
        old = _write_prompt(tmp_path, "old.yaml", SIMPLE_PROMPT_YAML)
        new = _write_prompt(tmp_path, "new.yaml", EXPENSIVE_PROMPT_YAML)
        result = runner.invoke(
            app, ["delta", "--model", "gpt-4o", str(old), str(new)]
        )
        assert result.exit_code == 0

    def test_delta_with_volume(self, tmp_path: Path):
        old = _write_prompt(tmp_path, "old.yaml", SIMPLE_PROMPT_YAML)
        new = _write_prompt(tmp_path, "new.yaml", EXPENSIVE_PROMPT_YAML)
        result = runner.invoke(
            app, ["delta", "--volume", "1000/day", str(old), str(new)]
        )
        assert result.exit_code == 0
        assert "Monthly" in result.output or "month" in result.output.lower()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestEstimateDirectory:
    def test_estimate_directory_shows_table(self, tmp_path: Path):
        _write_prompt(tmp_path, "a.yaml", SIMPLE_PROMPT_YAML)
        _write_prompt(tmp_path, "b.yaml", SIMPLE_PROMPT_YAML)
        result = runner.invoke(app, ["estimate", str(tmp_path)])
        assert result.exit_code == 0
        assert "a.yaml" in result.output
        assert "b.yaml" in result.output

    def test_estimate_directory_with_project(self, tmp_path: Path):
        _write_prompt(tmp_path, "a.yaml", SIMPLE_PROMPT_YAML)
        result = runner.invoke(
            app, ["estimate", "--project", "500/hour", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "Monthly" in result.output or "Annual" in result.output


class TestEstimateOutputTokensEdge:
    def test_output_tokens_zero_exits_2(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "prompt.yaml", SIMPLE_PROMPT_YAML)
        result = runner.invoke(
            app, ["estimate", "--output-tokens", "0", str(f)]
        )
        assert result.exit_code == 2

    def test_output_tokens_negative_exits_2(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "prompt.yaml", SIMPLE_PROMPT_YAML)
        result = runner.invoke(
            app, ["estimate", "--output-tokens", "-5", str(f)]
        )
        assert result.exit_code == 2


class TestBudgetLimitZero:
    def test_budget_limit_zero_fails(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "prompt.yaml", SIMPLE_PROMPT_YAML)
        result = runner.invoke(
            app, ["budget", "--limit", "0", str(f)]
        )
        # Should fail with BadParameter or non-zero exit
        assert result.exit_code != 0


class TestDeltaOutputTokens:
    def test_delta_with_output_tokens(self, tmp_path: Path):
        old = _write_prompt(tmp_path, "old.yaml", SIMPLE_PROMPT_YAML)
        new = _write_prompt(tmp_path, "new.yaml", EXPENSIVE_PROMPT_YAML)
        result = runner.invoke(
            app, ["delta", "--output-tokens", "500", str(old), str(new)]
        )
        assert result.exit_code == 0
        assert "Delta" in result.output or "delta" in result.output.lower()


class TestCompareJsonFormat:
    def test_compare_json_has_estimates_key(self, tmp_path: Path):
        f = _write_prompt(tmp_path, "prompt.yaml", SIMPLE_PROMPT_YAML)
        result = runner.invoke(
            app,
            ["estimate", "--format", "json", "--compare", "--models", "gpt-4o,gpt-4o-mini", str(f)],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "estimates" in data


class TestErrors:
    def test_estimate_nonexistent_file(self, tmp_path: Path):
        bad = tmp_path / "nonexistent.yaml"
        result = runner.invoke(app, ["estimate", str(bad)])
        assert result.exit_code == 2
        assert "not found" in result.output.lower() or "Path not found" in result.output

    def test_budget_nonexistent_file(self, tmp_path: Path):
        bad = tmp_path / "nonexistent.yaml"
        result = runner.invoke(app, ["budget", "--limit", "1.0", str(bad)])
        assert result.exit_code == 2

    def test_estimate_empty_directory(self, tmp_path: Path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = runner.invoke(app, ["estimate", str(empty_dir)])
        assert result.exit_code == 0
        assert "No prompt files" in result.output
