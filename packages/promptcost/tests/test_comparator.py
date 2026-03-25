"""Tests for promptcost.comparator."""

import pytest
from promptcost.comparator import compare_models


class TestCompareModels:
    def test_identifies_cheapest(self, simple_prompt):
        result = compare_models(
            simple_prompt,
            ["gpt-4", "gpt-4o-mini"],
        )
        assert result.cheapest == "gpt-4o-mini"
        assert result.most_expensive == "gpt-4"

    def test_savings_positive(self, simple_prompt):
        result = compare_models(
            simple_prompt,
            ["gpt-4", "gpt-4o-mini"],
        )
        assert result.savings_vs_most_expensive > 0

    def test_single_model(self, simple_prompt):
        result = compare_models(simple_prompt, ["gpt-4o"])
        assert result.cheapest == "gpt-4o"
        assert result.most_expensive == "gpt-4o"
        assert result.savings_vs_most_expensive == 0

    def test_empty_models_raises(self, simple_prompt):
        with pytest.raises(ValueError, match="At least one model"):
            compare_models(simple_prompt, [])

    def test_all_models_in_estimates(self, simple_prompt):
        models = ["gpt-4o", "gpt-4o-mini", "claude-4-sonnet"]
        result = compare_models(simple_prompt, models)
        for m in models:
            assert m in result.estimates
