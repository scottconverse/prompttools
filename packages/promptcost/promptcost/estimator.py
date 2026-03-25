"""Core cost estimation engine for promptcost."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from prompttools_core import (
    ModelProfile,
    PromptFile,
    PromptPipeline,
    Tokenizer,
    get_profile,
)

from promptcost.models import CostEstimate, PipelineCostEstimate, StageCostEstimate


def _get_profile_or_raise(model: str) -> ModelProfile:
    """Look up a model profile, raising ValueError if not found."""
    profile = get_profile(model)
    if profile is None:
        raise ValueError(f"Unknown model profile: '{model}'")
    return profile


def _estimate_output_tokens(
    prompt_file: PromptFile,
    profile: ModelProfile,
    explicit_output_tokens: Optional[int] = None,
) -> tuple[int, str]:
    """Estimate output tokens using the configured strategy.

    Returns (token_count, method).
    """
    if explicit_output_tokens is not None:
        return explicit_output_tokens, "explicit"

    # Check prompt metadata for expected_output_tokens
    meta_tokens = prompt_file.metadata.get("expected_output_tokens")
    if meta_tokens is not None:
        return int(meta_tokens), "explicit"

    # Heuristic: estimate based on prompt characteristics
    # Short prompts with questions → longer responses
    # Structured output requests → moderate responses
    # System prompts with constraints → shorter responses
    total_content = " ".join(m.content for m in prompt_file.messages)
    content_lower = total_content.lower()

    if any(kw in content_lower for kw in ["json", "structured", "schema", "format"]):
        # Structured output tends to be moderate
        return min(500, profile.max_output_tokens or 4096), "heuristic"
    elif any(kw in content_lower for kw in ["brief", "short", "concise", "summary"]):
        return min(300, profile.max_output_tokens or 4096), "heuristic"
    elif any(kw in content_lower for kw in ["detailed", "comprehensive", "thorough", "essay"]):
        return min(2000, profile.max_output_tokens or 4096), "heuristic"
    else:
        # Default: moderate response
        return min(1000, profile.max_output_tokens or 4096), "heuristic"


def _compute_cost(
    input_tokens: int,
    output_tokens: int,
    profile: ModelProfile,
) -> tuple[float, float, float]:
    """Compute input cost, output cost, and total cost."""
    input_price = profile.input_price_per_mtok or 0.0
    output_price = profile.output_price_per_mtok or 0.0

    input_cost = input_tokens / 1_000_000 * input_price
    output_cost = output_tokens / 1_000_000 * output_price
    total_cost = input_cost + output_cost

    return input_cost, output_cost, total_cost


def estimate_file(
    prompt_file: PromptFile,
    model: str,
    output_tokens: Optional[int] = None,
) -> CostEstimate:
    """Estimate cost for a single prompt file invocation.

    Parameters
    ----------
    prompt_file:
        Parsed prompt file.
    model:
        Model profile name.
    output_tokens:
        Explicit output token count. If None, uses heuristic.

    Returns
    -------
    CostEstimate
    """
    profile = _get_profile_or_raise(model)
    tokenizer = Tokenizer(encoding=profile.encoding, provider=profile.provider)

    input_tokens = tokenizer.count_file(prompt_file)
    est_output, method = _estimate_output_tokens(prompt_file, profile, output_tokens)
    input_cost, output_cost, total_cost = _compute_cost(input_tokens, est_output, profile)

    return CostEstimate(
        file_path=prompt_file.path,
        model=model,
        input_tokens=input_tokens,
        estimated_output_tokens=est_output,
        output_estimation_method=method,
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=total_cost,
    )


def estimate_pipeline(
    pipeline: PromptPipeline,
    model: str,
    output_tokens: Optional[int] = None,
) -> PipelineCostEstimate:
    """Estimate cost for an entire pipeline.

    Each stage's output feeds into the next stage's input context.
    """
    model_name = pipeline.model or model
    profile = _get_profile_or_raise(model_name)
    tokenizer = Tokenizer(encoding=profile.encoding, provider=profile.provider)

    stages: list[StageCostEstimate] = []
    accumulated_context = 0

    for stage in pipeline.stages:
        if stage.prompt_file is None:
            continue

        # Input = prompt tokens + accumulated context from previous stages
        stage_input = tokenizer.count_file(stage.prompt_file) + accumulated_context

        # Output estimation
        if stage.expected_output_tokens > 0:
            est_output = stage.expected_output_tokens
        elif output_tokens is not None:
            est_output = output_tokens
        else:
            est_output, _ = _estimate_output_tokens(
                stage.prompt_file, profile, None
            )

        input_cost, output_cost, total_cost = _compute_cost(
            stage_input, est_output, profile
        )

        stages.append(StageCostEstimate(
            stage_name=stage.name,
            input_tokens=stage_input,
            estimated_output_tokens=est_output,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
        ))

        # Output of this stage becomes part of next stage's context
        accumulated_context += est_output

    total_cost = sum(s.total_cost for s in stages)
    cumulative_tokens = sum(s.input_tokens + s.estimated_output_tokens for s in stages)

    return PipelineCostEstimate(
        pipeline_name=pipeline.name,
        model=model_name,
        stages=stages,
        total_cost=total_cost,
        cumulative_tokens=cumulative_tokens,
    )
