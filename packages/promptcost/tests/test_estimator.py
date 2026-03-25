"""Tests for promptcost.estimator."""

import pytest
from pathlib import Path

from prompttools_core import Message, PromptFile, PromptFormat, PromptPipeline, PipelineStage

from promptcost.estimator import estimate_file, estimate_pipeline, _estimate_output_tokens


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


class TestEstimateOutputTokensHeuristics:
    """Tests for _estimate_output_tokens internal heuristic."""

    def _make_prompt(self, content: str, metadata: dict | None = None) -> PromptFile:
        return PromptFile(
            path=Path("heuristic_test.yaml"),
            format=PromptFormat.YAML,
            raw_content=content,
            messages=[Message(role="user", content=content, line_start=1)],
            metadata=metadata or {},
        )

    def _get_profile(self):
        from prompttools_core import get_profile
        return get_profile("gpt-4o")

    def test_json_keyword_returns_500(self):
        pf = self._make_prompt("Please return the data as JSON")
        tokens, method = _estimate_output_tokens(pf, self._get_profile())
        assert tokens == 500
        assert method == "heuristic"

    def test_brief_keyword_returns_300(self):
        pf = self._make_prompt("Give me a brief summary")
        tokens, method = _estimate_output_tokens(pf, self._get_profile())
        assert tokens == 300
        assert method == "heuristic"

    def test_detailed_keyword_returns_2000(self):
        pf = self._make_prompt("Provide a detailed and comprehensive analysis")
        tokens, method = _estimate_output_tokens(pf, self._get_profile())
        assert tokens == 2000
        assert method == "heuristic"

    def test_metadata_expected_output_tokens(self):
        pf = self._make_prompt("Hello", metadata={"expected_output_tokens": 750})
        tokens, method = _estimate_output_tokens(pf, self._get_profile())
        assert tokens == 750
        assert method == "explicit"

    def test_generic_content_returns_1000(self):
        pf = self._make_prompt("Tell me about the weather today")
        tokens, method = _estimate_output_tokens(pf, self._get_profile())
        assert tokens == 1000
        assert method == "heuristic"


class TestEstimatePipeline:
    """Tests for estimate_pipeline()."""

    def test_pipeline_returns_correct_stage_count(self, simple_prompt):
        stage1 = PipelineStage(
            name="extract",
            prompt_file=simple_prompt,
            expected_output_tokens=200,
        )
        stage2 = PipelineStage(
            name="summarize",
            prompt_file=simple_prompt,
            expected_output_tokens=100,
        )
        pipeline = PromptPipeline(
            name="test-pipeline",
            manifest_path=Path("pipeline.yaml"),
            stages=[stage1, stage2],
        )
        result = estimate_pipeline(pipeline, "gpt-4o")
        assert len(result.stages) == 2
        assert result.pipeline_name == "test-pipeline"
        assert result.total_cost > 0
        assert result.cumulative_tokens > 0
