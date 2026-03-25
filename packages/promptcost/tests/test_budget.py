"""Tests for promptcost.budget."""

import pytest
from promptcost.budget import check_budget
from promptcost.estimator import estimate_file


class TestCheckBudget:
    def test_within_budget(self, simple_prompt):
        est = estimate_file(simple_prompt, "gpt-4o-mini")
        results = check_budget([est], 1.00)
        assert len(results) == 1
        assert not results[0].over_budget
        assert results[0].overage == 0.0

    def test_over_budget(self, simple_prompt):
        est = estimate_file(simple_prompt, "gpt-4")
        results = check_budget([est], 0.0001)
        assert len(results) == 1
        assert results[0].over_budget
        assert results[0].overage > 0

    def test_multiple_files(self, simple_prompt, detailed_prompt):
        est1 = estimate_file(simple_prompt, "gpt-4o")
        est2 = estimate_file(detailed_prompt, "gpt-4o")
        results = check_budget([est1, est2], 1.00)
        assert len(results) == 2

    def test_exact_budget(self, simple_prompt):
        est = estimate_file(simple_prompt, "gpt-4o")
        results = check_budget([est], est.total_cost)
        assert not results[0].over_budget

    def test_empty_estimates_returns_empty(self):
        results = check_budget([], 1.00)
        assert results == []
