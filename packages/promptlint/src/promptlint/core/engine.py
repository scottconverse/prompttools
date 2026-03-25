"""Lint engine for promptlint.

Discovers rules, counts tokens, runs rules against parsed prompts, and
filters results based on configuration.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Any

import promptlint.rules as _rules_pkg
from promptlint.models import (
    LintConfig,
    LintViolation,
    PromptFile,
    PromptPipeline,
    Severity,
)
from promptlint.rules.base import BasePipelineRule, BaseRule
from promptlint.utils.tokenizers import count_tokens

# ---------------------------------------------------------------------------
# Severity helpers
# ---------------------------------------------------------------------------

_SEVERITY_ORDER = {
    Severity.INFO: 0,
    Severity.WARNING: 1,
    Severity.ERROR: 2,
}


def _severity_from_str(value: str) -> Severity | None:
    """Convert a string to a Severity enum value, or None if invalid."""
    value = value.strip().lower()
    try:
        return Severity(value)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Rule discovery
# ---------------------------------------------------------------------------

_builtin_rules_cache: list[BaseRule] | None = None
_builtin_pipeline_rules_cache: list[BasePipelineRule] | None = None


def _discover_builtin_rules() -> tuple[list[BaseRule], list[BasePipelineRule]]:
    """Import all modules in ``promptlint.rules`` and instantiate rule classes."""
    global _builtin_rules_cache, _builtin_pipeline_rules_cache

    if _builtin_rules_cache is not None and _builtin_pipeline_rules_cache is not None:
        return _builtin_rules_cache, _builtin_pipeline_rules_cache

    file_rules: list[BaseRule] = []
    pipeline_rules: list[BasePipelineRule] = []

    package_path = _rules_pkg.__path__
    for importer, modname, ispkg in pkgutil.iter_modules(package_path):
        if modname == "base":
            continue
        full_name = f"promptlint.rules.{modname}"
        try:
            module = importlib.import_module(full_name)
        except Exception:
            continue

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if not isinstance(attr, type):
                continue
            if attr is BaseRule or attr is BasePipelineRule:
                continue
            try:
                if issubclass(attr, BaseRule) and hasattr(attr, "rule_id"):
                    file_rules.append(attr())
                elif issubclass(attr, BasePipelineRule) and hasattr(attr, "rule_id"):
                    pipeline_rules.append(attr())
            except TypeError:
                continue

    _builtin_rules_cache = file_rules
    _builtin_pipeline_rules_cache = pipeline_rules
    return file_rules, pipeline_rules


def _load_plugin_rules(plugin_dirs: list[Path]) -> tuple[list[BaseRule], list[BasePipelineRule]]:
    """Load custom rule classes from plugin directories."""
    file_rules: list[BaseRule] = []
    pipeline_rules: list[BasePipelineRule] = []

    for plugin_dir in plugin_dirs:
        plugin_dir = Path(plugin_dir)
        if not plugin_dir.is_dir():
            continue
        for py_file in plugin_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            module_name = f"promptlint_plugin_{py_file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec is None or spec.loader is None:
                continue
            try:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception:
                continue

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if not isinstance(attr, type):
                    continue
                try:
                    if issubclass(attr, BaseRule) and attr is not BaseRule and hasattr(attr, "rule_id"):
                        file_rules.append(attr())
                    elif (
                        issubclass(attr, BasePipelineRule)
                        and attr is not BasePipelineRule
                        and hasattr(attr, "rule_id")
                    ):
                        pipeline_rules.append(attr())
                except TypeError:
                    continue

    return file_rules, pipeline_rules


def get_all_rules(config: LintConfig | None = None) -> list[BaseRule]:
    """Return all available file-level rules (built-in + plugins).

    Parameters
    ----------
    config:
        If provided, plugin directories from the config are included.
    """
    builtin_file, _ = _discover_builtin_rules()
    rules = list(builtin_file)

    if config and config.plugin_dirs:
        plugin_file, _ = _load_plugin_rules(config.plugin_dirs)
        rules.extend(plugin_file)

    return rules


def get_all_pipeline_rules(config: LintConfig | None = None) -> list[BasePipelineRule]:
    """Return all available pipeline-level rules (built-in + plugins)."""
    _, builtin_pipeline = _discover_builtin_rules()
    rules = list(builtin_pipeline)

    if config and config.plugin_dirs:
        _, plugin_pipeline = _load_plugin_rules(config.plugin_dirs)
        rules.extend(plugin_pipeline)

    return rules


# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------

def _populate_token_counts(prompt_file: PromptFile, encoding: str) -> None:
    """Count tokens for each message and set ``total_tokens`` on the file."""
    total = 0
    for msg in prompt_file.messages:
        msg.token_count = count_tokens(msg.content, encoding)
        total += msg.token_count
    prompt_file.total_tokens = total


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def _effective_severity(
    rule: BaseRule | BasePipelineRule,
    config: LintConfig,
) -> Severity | None:
    """Determine the effective severity for a rule after applying overrides.

    Returns ``None`` if the rule should be ignored.
    """
    # Check if rule is globally ignored
    if rule.rule_id in config.ignored_rules or rule.name in config.ignored_rules:
        return None

    # Check rule_overrides
    override = config.rule_overrides.get(rule.rule_id) or config.rule_overrides.get(rule.name)
    if override:
        if override.lower() == "ignore":
            return None
        sev = _severity_from_str(override)
        if sev is not None:
            return sev

    return rule.default_severity


def _filter_violations(
    violations: list[LintViolation],
    config: LintConfig,
    min_severity: str = "info",
) -> list[LintViolation]:
    """Remove violations below the minimum severity."""
    min_sev = _severity_from_str(min_severity)
    if min_sev is None:
        min_sev = Severity.INFO

    min_order = _SEVERITY_ORDER[min_sev]
    return [v for v in violations if _SEVERITY_ORDER.get(v.severity, 0) >= min_order]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def lint_file(
    prompt_file: PromptFile,
    config: LintConfig,
    min_severity: str = "info",
) -> list[LintViolation]:
    """Lint a single ``PromptFile`` against all enabled rules.

    Parameters
    ----------
    prompt_file:
        The parsed prompt to lint.
    config:
        Merged lint configuration.
    min_severity:
        Minimum severity to include in results (``info``, ``warning``, ``error``).

    Returns
    -------
    list[LintViolation]
        Violations found, sorted by line number then rule ID.
    """
    # Count tokens for each message
    _populate_token_counts(prompt_file, config.tokenizer_encoding)

    rules = get_all_rules(config)
    violations: list[LintViolation] = []

    for rule in rules:
        effective_sev = _effective_severity(rule, config)
        if effective_sev is None:
            continue

        try:
            rule_violations = rule.check(prompt_file, config)
        except Exception:
            continue

        # Apply severity override to each violation
        for v in rule_violations:
            if effective_sev != rule.default_severity:
                v.severity = effective_sev
            violations.append(v)

    violations = _filter_violations(violations, config, min_severity)

    # Sort by line (None sorts first), then rule_id
    violations.sort(key=lambda v: (v.line or 0, v.rule_id))
    return violations


def lint_pipeline(
    pipeline: PromptPipeline,
    config: LintConfig,
    min_severity: str = "info",
) -> list[LintViolation]:
    """Lint a ``PromptPipeline`` against file-level and pipeline-level rules.

    Runs file-level rules on each stage's prompt, then runs pipeline
    rules on the full pipeline.

    Parameters
    ----------
    pipeline:
        The parsed pipeline to lint.
    config:
        Merged lint configuration.
    min_severity:
        Minimum severity to include.

    Returns
    -------
    list[LintViolation]
        All violations found across stages and pipeline rules.
    """
    all_violations: list[LintViolation] = []

    # Lint each stage individually
    for stage in pipeline.stages:
        stage_violations = lint_file(stage.prompt_file, config, min_severity)
        all_violations.extend(stage_violations)

    # Compute cumulative tokens for pipeline-level analysis
    cumulative: list[int] = []
    running_total = 0
    for stage in pipeline.stages:
        stage_tokens = stage.prompt_file.total_tokens or 0
        # Add expected output tokens from dependencies
        for dep_name in stage.depends_on:
            for other_stage in pipeline.stages:
                if other_stage.name == dep_name and other_stage.expected_output_tokens:
                    stage_tokens += other_stage.expected_output_tokens
        running_total += stage_tokens
        cumulative.append(running_total)

    pipeline.cumulative_tokens = cumulative
    pipeline.total_tokens = cumulative[-1] if cumulative else 0

    # Run pipeline-level rules
    pipeline_rules = get_all_pipeline_rules(config)
    for rule in pipeline_rules:
        effective_sev = _effective_severity(rule, config)
        if effective_sev is None:
            continue

        try:
            rule_violations = rule.check_pipeline(pipeline, config)
        except Exception:
            continue

        for v in rule_violations:
            if effective_sev != rule.default_severity:
                v.severity = effective_sev
            all_violations.append(v)

    all_violations = _filter_violations(all_violations, config, min_severity)
    all_violations.sort(key=lambda v: (v.path.name, v.line or 0, v.rule_id))
    return all_violations
