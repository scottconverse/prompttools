"""Unit tests for promptcost.models — all 7 Pydantic data models."""

import pytest
from pathlib import Path

from promptcost.models import (
    BudgetResult,
    CostComparison,
    CostDelta,
    CostEstimate,
    CostProjection,
    PipelineCostEstimate,
    StageCostEstimate,
)


# ---------------------------------------------------------------------------
# CostEstimate
# ---------------------------------------------------------------------------


class TestCostEstimate:
    def test_construction_with_all_fields(self):
        est = CostEstimate(
            file_path=Path("test.yaml"),
            model="gpt-4o",
            input_tokens=100,
            estimated_output_tokens=500,
            output_estimation_method="heuristic",
            input_cost=0.001,
            output_cost=0.002,
            total_cost=0.003,
        )
        assert est.file_path == Path("test.yaml")
        assert est.model == "gpt-4o"
        assert est.input_tokens == 100
        assert est.estimated_output_tokens == 500
        assert est.input_cost == 0.001
        assert est.output_cost == 0.002
        assert est.total_cost == 0.003

    def test_output_estimation_method_explicit(self):
        est = CostEstimate(
            file_path=Path("t.yaml"),
            model="gpt-4o",
            input_tokens=10,
            estimated_output_tokens=50,
            output_estimation_method="explicit",
            input_cost=0.0,
            output_cost=0.0,
            total_cost=0.0,
        )
        assert est.output_estimation_method == "explicit"

    def test_output_estimation_method_max(self):
        est = CostEstimate(
            file_path=Path("t.yaml"),
            model="gpt-4o",
            input_tokens=10,
            estimated_output_tokens=50,
            output_estimation_method="max",
            input_cost=0.0,
            output_cost=0.0,
            total_cost=0.0,
        )
        assert est.output_estimation_method == "max"

    def test_output_estimation_method_invalid_rejected(self):
        with pytest.raises(Exception):
            CostEstimate(
                file_path=Path("t.yaml"),
                model="gpt-4o",
                input_tokens=10,
                estimated_output_tokens=50,
                output_estimation_method="invalid_method",
                input_cost=0.0,
                output_cost=0.0,
                total_cost=0.0,
            )

    def test_json_roundtrip(self):
        est = CostEstimate(
            file_path=Path("roundtrip.yaml"),
            model="claude-4-sonnet",
            input_tokens=200,
            estimated_output_tokens=1000,
            output_estimation_method="heuristic",
            input_cost=0.0006,
            output_cost=0.015,
            total_cost=0.0156,
        )
        json_str = est.model_dump_json()
        restored = CostEstimate.model_validate_json(json_str)
        assert restored.file_path == est.file_path
        assert restored.model == est.model
        assert restored.input_tokens == est.input_tokens
        assert restored.estimated_output_tokens == est.estimated_output_tokens
        assert restored.output_estimation_method == est.output_estimation_method
        assert restored.total_cost == pytest.approx(est.total_cost)


# ---------------------------------------------------------------------------
# StageCostEstimate
# ---------------------------------------------------------------------------


class TestStageCostEstimate:
    def test_construction(self):
        stage = StageCostEstimate(
            stage_name="extract",
            input_tokens=500,
            estimated_output_tokens=200,
            input_cost=0.001,
            output_cost=0.002,
            total_cost=0.003,
        )
        assert stage.stage_name == "extract"
        assert stage.input_tokens == 500
        assert stage.estimated_output_tokens == 200
        assert stage.total_cost == 0.003


# ---------------------------------------------------------------------------
# PipelineCostEstimate
# ---------------------------------------------------------------------------


class TestPipelineCostEstimate:
    def test_construction_with_stages(self):
        s1 = StageCostEstimate(
            stage_name="stage1",
            input_tokens=100,
            estimated_output_tokens=50,
            input_cost=0.001,
            output_cost=0.002,
            total_cost=0.003,
        )
        s2 = StageCostEstimate(
            stage_name="stage2",
            input_tokens=150,
            estimated_output_tokens=60,
            input_cost=0.002,
            output_cost=0.003,
            total_cost=0.005,
        )
        pipe = PipelineCostEstimate(
            pipeline_name="my-pipeline",
            model="gpt-4o",
            stages=[s1, s2],
            total_cost=0.008,
            cumulative_tokens=360,
        )
        assert pipe.pipeline_name == "my-pipeline"
        assert len(pipe.stages) == 2
        assert pipe.total_cost == 0.008
        assert pipe.cumulative_tokens == 360

    def test_empty_stages(self):
        pipe = PipelineCostEstimate(
            pipeline_name="empty",
            model="gpt-4o",
            stages=[],
            total_cost=0.0,
            cumulative_tokens=0,
        )
        assert len(pipe.stages) == 0


# ---------------------------------------------------------------------------
# CostProjection
# ---------------------------------------------------------------------------


class TestCostProjection:
    def test_construction(self):
        proj = CostProjection(
            volume="1000/day",
            calls_per_day=1000,
            daily_cost=5.0,
            monthly_cost=150.0,
            annual_cost=1825.0,
        )
        assert proj.volume == "1000/day"
        assert proj.calls_per_day == 1000
        assert proj.daily_cost == 5.0
        assert proj.monthly_cost == 150.0
        assert proj.annual_cost == 1825.0


# ---------------------------------------------------------------------------
# CostComparison
# ---------------------------------------------------------------------------


class TestCostComparison:
    def test_construction_with_estimates_dict(self):
        est1 = CostEstimate(
            file_path=Path("t.yaml"),
            model="gpt-4o",
            input_tokens=100,
            estimated_output_tokens=500,
            output_estimation_method="heuristic",
            input_cost=0.001,
            output_cost=0.005,
            total_cost=0.006,
        )
        est2 = CostEstimate(
            file_path=Path("t.yaml"),
            model="gpt-4o-mini",
            input_tokens=100,
            estimated_output_tokens=500,
            output_estimation_method="heuristic",
            input_cost=0.0001,
            output_cost=0.001,
            total_cost=0.0011,
        )
        comp = CostComparison(
            file_path=Path("t.yaml"),
            input_tokens=100,
            estimated_output_tokens=500,
            estimates={"gpt-4o": est1, "gpt-4o-mini": est2},
            cheapest="gpt-4o-mini",
            most_expensive="gpt-4o",
            savings_vs_most_expensive=0.0049,
        )
        assert comp.cheapest == "gpt-4o-mini"
        assert comp.most_expensive == "gpt-4o"
        assert len(comp.estimates) == 2
        assert comp.savings_vs_most_expensive == pytest.approx(0.0049)


# ---------------------------------------------------------------------------
# CostDelta
# ---------------------------------------------------------------------------


class TestCostDelta:
    def test_construction(self):
        old = CostEstimate(
            file_path=Path("old.yaml"),
            model="gpt-4o",
            input_tokens=100,
            estimated_output_tokens=500,
            output_estimation_method="heuristic",
            input_cost=0.001,
            output_cost=0.005,
            total_cost=0.006,
        )
        new = CostEstimate(
            file_path=Path("new.yaml"),
            model="gpt-4o",
            input_tokens=200,
            estimated_output_tokens=500,
            output_estimation_method="heuristic",
            input_cost=0.002,
            output_cost=0.005,
            total_cost=0.007,
        )
        delta = CostDelta(
            file_path=Path("test.yaml"),
            model="gpt-4o",
            old_estimate=old,
            new_estimate=new,
            cost_change=0.001,
            percent_change=16.67,
        )
        assert delta.cost_change == 0.001
        assert delta.percent_change == pytest.approx(16.67)

    def test_monthly_impact_defaults_to_none(self):
        old = CostEstimate(
            file_path=Path("a.yaml"),
            model="gpt-4o",
            input_tokens=10,
            estimated_output_tokens=50,
            output_estimation_method="heuristic",
            input_cost=0.0,
            output_cost=0.0,
            total_cost=0.0,
        )
        delta = CostDelta(
            file_path=Path("a.yaml"),
            model="gpt-4o",
            old_estimate=old,
            new_estimate=old,
            cost_change=0.0,
            percent_change=0.0,
        )
        assert delta.monthly_impact is None

    def test_monthly_impact_set_explicitly(self):
        old = CostEstimate(
            file_path=Path("a.yaml"),
            model="gpt-4o",
            input_tokens=10,
            estimated_output_tokens=50,
            output_estimation_method="heuristic",
            input_cost=0.0,
            output_cost=0.0,
            total_cost=0.0,
        )
        delta = CostDelta(
            file_path=Path("a.yaml"),
            model="gpt-4o",
            old_estimate=old,
            new_estimate=old,
            cost_change=0.0,
            percent_change=0.0,
            monthly_impact=42.50,
        )
        assert delta.monthly_impact == 42.50


# ---------------------------------------------------------------------------
# BudgetResult
# ---------------------------------------------------------------------------


class TestBudgetResult:
    def test_over_budget_true(self):
        result = BudgetResult(
            file_path=Path("expensive.yaml"),
            model="gpt-4",
            estimated_cost=0.10,
            budget=0.05,
            over_budget=True,
            overage=0.05,
        )
        assert result.over_budget is True
        assert result.overage == 0.05

    def test_over_budget_false(self):
        result = BudgetResult(
            file_path=Path("cheap.yaml"),
            model="gpt-4o-mini",
            estimated_cost=0.001,
            budget=0.05,
            over_budget=False,
            overage=0.0,
        )
        assert result.over_budget is False
        assert result.overage == 0.0

    def test_overage_non_negative(self):
        result = BudgetResult(
            file_path=Path("t.yaml"),
            model="gpt-4o",
            estimated_cost=0.01,
            budget=0.05,
            over_budget=False,
            overage=0.0,
        )
        assert result.overage >= 0.0
