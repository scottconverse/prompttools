"""Tests for promptcost.projector."""

import pytest
from promptcost.projector import project_cost, _parse_volume
from promptcost.estimator import estimate_file


class TestParseVolume:
    def test_per_day(self):
        assert _parse_volume("1000/day") == 1000

    def test_per_hour(self):
        assert _parse_volume("100/hour") == 2400

    def test_per_week(self):
        assert _parse_volume("7000/week") == 1000

    def test_per_month(self):
        assert _parse_volume("30000/month") == 1000

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid volume"):
            _parse_volume("1000 calls")


class TestProjectCost:
    def test_projection_math(self, simple_prompt):
        est = estimate_file(simple_prompt, "gpt-4o")
        proj = project_cost(est, "1000/day")

        assert proj.calls_per_day == 1000
        assert proj.daily_cost == pytest.approx(est.total_cost * 1000)
        assert proj.monthly_cost == pytest.approx(proj.daily_cost * 30)
        assert proj.annual_cost == pytest.approx(proj.daily_cost * 365)

    def test_volume_string_preserved(self, simple_prompt):
        est = estimate_file(simple_prompt, "gpt-4o")
        proj = project_cost(est, "500/day")
        assert proj.volume == "500/day"
