"""Volume-based cost projections for promptcost."""

from __future__ import annotations

import re

from promptcost.models import CostEstimate, CostProjection


def _parse_volume(volume: str) -> int:
    """Parse a volume string like '1000/day' or '500/hour' into calls per day."""
    volume = volume.strip().lower()
    match = re.match(r"^(\d+)\s*/\s*(hour|day|week|month)$", volume)
    if not match:
        raise ValueError(
            f"Invalid volume format: '{volume}'. "
            f"Expected: N/hour, N/day, N/week, or N/month"
        )

    count = int(match.group(1))
    period = match.group(2)

    multipliers = {
        "hour": 24,
        "day": 1,
        "week": 1.0 / 7.0,
        "month": 1.0 / 30.0,
    }

    return int(count * multipliers[period])


def project_cost(
    estimate: CostEstimate,
    volume: str,
) -> CostProjection:
    """Project costs at a given call volume.

    Parameters
    ----------
    estimate:
        Per-invocation cost estimate.
    volume:
        Volume string like ``"1000/day"``, ``"500/hour"``.

    Returns
    -------
    CostProjection
    """
    calls_per_day = _parse_volume(volume)
    daily = estimate.total_cost * calls_per_day
    monthly = daily * 30
    annual = daily * 365

    return CostProjection(
        volume=volume,
        calls_per_day=calls_per_day,
        daily_cost=daily,
        monthly_cost=monthly,
        annual_cost=annual,
    )
