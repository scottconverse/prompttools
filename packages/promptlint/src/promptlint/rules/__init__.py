"""promptlint rules package.

Exports all built-in rule classes and provides ``get_all_rules()`` for
convenient discovery by the lint engine.
"""

from __future__ import annotations

from typing import Union

from promptlint.rules.base import BasePipelineRule, BaseRule

# Token budget rules
from promptlint.rules.token_budget import (
    TokenBudgetErrorRule,
    TokenBudgetWarnRule,
    TokenDensityLowRule,
)

# System prompt rules
from promptlint.rules.system_prompt import (
    ConflictingInstructionsRule,
    InjectionVectorDetectedRule,
    SystemPromptMissingRule,
    SystemPromptNotFirstRule,
    SystemPromptTooLongRule,
)

# Formatting rules
from promptlint.rules.formatting import (
    ExcessiveRepetitionRule,
    InconsistentDelimitersRule,
    LineTooLongRule,
    MissingOutputFormatRule,
    TrailingWhitespaceRule,
)

# Variable rules
from promptlint.rules.variables import (
    UndefinedVariableRule,
    UnusedVariableRule,
    VariableFormatInconsistentRule,
    VariableNoDefaultRule,
)

# Pipeline rules
from promptlint.rules.pipeline import (
    PipelineContextGrowthRule,
    PipelineInconsistentPersonaRule,
    PipelineNoHandoffRule,
    PipelineOrphanReferenceRule,
)

# Hallucination rules
from promptlint.rules.hallucination import (
    AsksForCitationsRule,
    AsksForSpecificNumbersRule,
    AsksForURLsRule,
    FabricationProneTaskRule,
    NoUncertaintyInstructionRule,
)

# Security rules
from promptlint.rules.security import (
    HardcodedAPIKeyRule,
    NoOutputConstraintsRule,
    PIIInPromptRule,
    UnboundedToolUseRule,
)

# Smell rules
from promptlint.rules.smells import (
    AmbiguousQuantifierRule,
    CompetingInstructionsRule,
    InstructionBuriedRule,
    NoExamplesRule,
    WallOfTextRule,
)

# Gate rules
from promptlint.rules.gates import (
    ClaimNoEvidenceGateRule,
    GateNoEnforcementRule,
    GateNoFallbackRule,
    OutputSchemaMissingRule,
)

# Tokenizer warning rules
from promptlint.rules.tokenizer_warnings import (
    ApproximateTokenizerWarning,
)

__all__ = [
    # Base
    "BaseRule",
    "BasePipelineRule",
    # Token budget
    "TokenBudgetWarnRule",
    "TokenBudgetErrorRule",
    "TokenDensityLowRule",
    # System prompt
    "SystemPromptMissingRule",
    "SystemPromptNotFirstRule",
    "InjectionVectorDetectedRule",
    "ConflictingInstructionsRule",
    "SystemPromptTooLongRule",
    # Formatting
    "TrailingWhitespaceRule",
    "InconsistentDelimitersRule",
    "MissingOutputFormatRule",
    "ExcessiveRepetitionRule",
    "LineTooLongRule",
    # Variables
    "UndefinedVariableRule",
    "UnusedVariableRule",
    "VariableNoDefaultRule",
    "VariableFormatInconsistentRule",
    # Pipeline
    "PipelineNoHandoffRule",
    "PipelineContextGrowthRule",
    "PipelineOrphanReferenceRule",
    "PipelineInconsistentPersonaRule",
    # Hallucination
    "AsksForSpecificNumbersRule",
    "AsksForURLsRule",
    "AsksForCitationsRule",
    "NoUncertaintyInstructionRule",
    "FabricationProneTaskRule",
    # Security
    "PIIInPromptRule",
    "HardcodedAPIKeyRule",
    "NoOutputConstraintsRule",
    "UnboundedToolUseRule",
    # Smells
    "AmbiguousQuantifierRule",
    "InstructionBuriedRule",
    "CompetingInstructionsRule",
    "NoExamplesRule",
    "WallOfTextRule",
    # Gates
    "GateNoEnforcementRule",
    "GateNoFallbackRule",
    "OutputSchemaMissingRule",
    "ClaimNoEvidenceGateRule",
    # Tokenizer warnings
    "ApproximateTokenizerWarning",
    # Discovery
    "get_all_rules",
    "get_all_pipeline_rules",
]


def get_all_rules() -> list[BaseRule]:
    """Return instances of all built-in single-file rules.

    The rules are returned in rule-ID order (PL001, PL002, ...).
    """
    return [
        # PL001-PL003
        TokenBudgetWarnRule(),
        TokenBudgetErrorRule(),
        TokenDensityLowRule(),
        # PL010-PL014
        SystemPromptMissingRule(),
        SystemPromptNotFirstRule(),
        InjectionVectorDetectedRule(),
        ConflictingInstructionsRule(),
        SystemPromptTooLongRule(),
        # PL020-PL024
        TrailingWhitespaceRule(),
        InconsistentDelimitersRule(),
        MissingOutputFormatRule(),
        ExcessiveRepetitionRule(),
        LineTooLongRule(),
        # PL030-PL033
        UndefinedVariableRule(),
        UnusedVariableRule(),
        VariableNoDefaultRule(),
        VariableFormatInconsistentRule(),
        # PL050-PL054
        AsksForSpecificNumbersRule(),
        AsksForURLsRule(),
        AsksForCitationsRule(),
        NoUncertaintyInstructionRule(),
        FabricationProneTaskRule(),
        # PL060-PL063
        PIIInPromptRule(),
        HardcodedAPIKeyRule(),
        NoOutputConstraintsRule(),
        UnboundedToolUseRule(),
        # PL070-PL074
        AmbiguousQuantifierRule(),
        InstructionBuriedRule(),
        CompetingInstructionsRule(),
        NoExamplesRule(),
        WallOfTextRule(),
        # PL080-PL083
        GateNoEnforcementRule(),
        GateNoFallbackRule(),
        OutputSchemaMissingRule(),
        ClaimNoEvidenceGateRule(),
        # PL090
        ApproximateTokenizerWarning(),
    ]


def get_all_pipeline_rules() -> list[BasePipelineRule]:
    """Return instances of all built-in pipeline rules.

    The rules are returned in rule-ID order (PL040, PL041, ...).
    """
    return [
        PipelineNoHandoffRule(),
        PipelineContextGrowthRule(),
        PipelineOrphanReferenceRule(),
        PipelineInconsistentPersonaRule(),
    ]
