"""Multi-model cost comparison for promptcost."""

from __future__ import annotations

import logging
from typing import Optional

from prompttools_core import PromptFile, get_profile, list_profiles

from promptcost.estimator import estimate_file
from promptcost.models import CostComparison

logger = logging.getLogger(__name__)


def compare_models(
    prompt_file: PromptFile,
    models: list[str],
    output_tokens: Optional[int] = None,
) -> CostComparison:
    """Compare costs for a prompt across multiple models.

    Parameters
    ----------
    prompt_file:
        Parsed prompt file.
    models:
        List of model profile names to compare.
    output_tokens:
        Explicit output token override.

    Returns
    -------
    CostComparison
    """
    if not models:
        raise ValueError("At least one model must be specified for comparison")

    estimates = {}
    for model in models:
        profile = get_profile(model)
        if profile is None:
            logger.warning("Skipping unknown model '%s' — no profile found", model)
            continue
        est = estimate_file(prompt_file, model, output_tokens)
        estimates[model] = est

    if not estimates:
        raise ValueError(
            "No valid model profiles found. Skipped: "
            + ", ".join(models)
        )

    cheapest = min(estimates, key=lambda m: estimates[m].total_cost)
    most_expensive = max(estimates, key=lambda m: estimates[m].total_cost)

    max_cost = estimates[most_expensive].total_cost
    min_cost = estimates[cheapest].total_cost
    savings = max_cost - min_cost

    # Use the first estimate's token counts (input tokens vary by encoding)
    first = next(iter(estimates.values()))

    return CostComparison(
        file_path=prompt_file.path,
        input_tokens=first.input_tokens,
        estimated_output_tokens=first.estimated_output_tokens,
        estimates=estimates,
        cheapest=cheapest,
        most_expensive=most_expensive,
        savings_vs_most_expensive=savings,
    )
