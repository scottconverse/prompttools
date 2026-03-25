"""Budget enforcement for promptcost."""

from __future__ import annotations

from promptcost.models import BudgetResult, CostEstimate


def check_budget(
    estimates: list[CostEstimate],
    budget: float,
) -> list[BudgetResult]:
    """Check whether prompt costs are within budget.

    Parameters
    ----------
    estimates:
        List of cost estimates to check.
    budget:
        Maximum allowed cost per invocation in USD.

    Returns
    -------
    list[BudgetResult]
        One result per estimate with pass/fail status.
    """
    results: list[BudgetResult] = []
    for est in estimates:
        over = est.total_cost > budget
        overage = max(0.0, est.total_cost - budget)
        results.append(BudgetResult(
            file_path=est.file_path,
            model=est.model,
            estimated_cost=est.total_cost,
            budget=budget,
            over_budget=over,
            overage=overage,
        ))
    return results
