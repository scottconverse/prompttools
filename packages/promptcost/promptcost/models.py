"""Data models for promptcost."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CostEstimate(BaseModel):
    """Cost estimate for a single prompt invocation."""

    file_path: Path
    model: str
    input_tokens: int
    estimated_output_tokens: int
    output_estimation_method: Literal["explicit", "heuristic", "max"] = "heuristic"
    input_cost: float
    output_cost: float
    total_cost: float


class StageCostEstimate(BaseModel):
    """Cost estimate for a single pipeline stage."""

    stage_name: str
    input_tokens: int
    estimated_output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float


class PipelineCostEstimate(BaseModel):
    """Cost estimate for an entire pipeline."""

    pipeline_name: str
    model: str
    stages: list[StageCostEstimate]
    total_cost: float
    cumulative_tokens: int


class CostProjection(BaseModel):
    """Cost projection at a given call volume."""

    volume: str
    calls_per_day: int
    daily_cost: float
    monthly_cost: float
    annual_cost: float


class CostComparison(BaseModel):
    """Cost comparison across multiple models."""

    file_path: Path
    input_tokens: int
    estimated_output_tokens: int
    estimates: dict[str, CostEstimate]
    cheapest: str
    most_expensive: str
    savings_vs_most_expensive: float


class CostDelta(BaseModel):
    """Cost impact of a prompt change."""

    file_path: Path
    model: str
    old_estimate: CostEstimate
    new_estimate: CostEstimate
    cost_change: float
    percent_change: float
    monthly_impact: Optional[float] = None


class BudgetResult(BaseModel):
    """Result of a budget check for a single prompt."""

    file_path: Path
    model: str
    estimated_cost: float
    budget: float
    over_budget: bool
    overage: float
