"""Tests for promptcost.estimator."""

import pytest
from pathlib import Path

from prompttools_core import Message, PromptFile, PromptFormat

from promptcost.estimator import estimate_file


class TestEstimateFile:
    def test_returns_cost_estimate(self, simple_prompt):
        est = estimate_file(simple_prompt, "gpt-4o")
        assert est.model == "gpt-4o"
        assert est.input_tokens > 0
        assert est.estimated_output_tokens > 0
        assert est.total_cost > 0

    def test_cost_is_sum_of_input_and_output(self, simple_prompt):
        est = estimate_file(simple_prompt, "gpt-4o")
        assert abs(est.total_cost - (est.input_cost + est.output_cost)) < 1e-10

    def test_explicit_output_tokens(self, simple_prompt):
        est = estimate_file(simple_prompt, "gpt-4o", output_tokens=100)
        assert est.estimated_output_tokens == 100
        assert est.output_estimation_method == "explicit"

    def test_heuristic_output_tokens(self, simple_prompt):
        est = estimate_file(simple_prompt, "gpt-4o")
        assert est.output_estimation_method == "heuristic"
        assert est.estimated_output_tokens > 0

    def test_unknown_model_raises(self, simple_prompt):
        with pytest.raises(ValueError, match="Unknown model"):
            estimate_file(simple_prompt, "nonexistent-model")

    def test_cheaper_model_costs_less(self, simple_prompt):
        expensive = estimate_file(simple_prompt, "gpt-4")
        cheap = estimate_file(simple_prompt, "gpt-4o-mini")
        assert cheap.total_cost < expensive.total_cost

    def test_cost_accuracy(self):
        """Verify cost calculation with known values."""
        pf = PromptFile(
            path=Path("test.txt"),
            format=PromptFormat.TEXT,
            raw_content="test",
            messages=[Message(role="user", content="test", line_start=1)],
        )
        est = estimate_file(pf, "gpt-4o-mini", output_tokens=1000)
        # Input: ~5 tokens (1 word + overhead) @ $0.15/Mtok
        # Output: 1000 tokens @ $0.60/Mtok = $0.0006
        assert est.output_cost == pytest.approx(1000 / 1_000_000 * 0.60, abs=1e-6)
