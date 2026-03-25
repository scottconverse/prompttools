"""Core diff engine for promptdiff.

Compares two prompt files parsed via prompttools_core and produces a
structured PromptDiff with message-level, variable-level, and metadata-level
change information.
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any, Optional

from prompttools_core import PromptFile, Tokenizer, count_tokens, parse_file
from prompttools_core.models import Message

from promptdiff.analyzer import analyze_breaking_changes
from promptdiff.models import (
    ChangeStatus,
    MessageDiff,
    MetadataDiff,
    PromptDiff,
    TokenDelta,
    VariableDiff,
)

# Default encoding used for token counting when no model is specified.
_DEFAULT_ENCODING = "cl100k_base"


def diff_files(
    old_path: Path,
    new_path: Path,
    encoding: str = _DEFAULT_ENCODING,
) -> PromptDiff:
    """Parse and diff two prompt files.

    Parameters
    ----------
    old_path:
        Path to the old prompt file.
    new_path:
        Path to the new prompt file.
    encoding:
        tiktoken encoding name for token counting.

    Returns
    -------
    PromptDiff
        A structured diff between the two files.
    """
    old_file = parse_file(Path(old_path))
    new_file = parse_file(Path(new_path))

    msg_diffs = diff_messages(old_file.messages, new_file.messages, encoding)
    var_diffs = diff_variables(
        old_file.variables,
        new_file.variables,
        old_file.variable_defaults,
        new_file.variable_defaults,
    )
    meta_diffs = diff_metadata(old_file.metadata, new_file.metadata)
    token_d = compute_token_delta(old_file, new_file, encoding)

    result = PromptDiff(
        file_path=new_path,
        old_hash=old_file.content_hash,
        new_hash=new_file.content_hash,
        message_diffs=msg_diffs,
        variable_diffs=var_diffs,
        metadata_diffs=meta_diffs,
        token_delta=token_d,
        breaking_changes=[],
    )

    # Run breaking change analysis and attach results.
    result.breaking_changes = analyze_breaking_changes(result)

    return result


def diff_messages(
    old_msgs: list[Message],
    new_msgs: list[Message],
    encoding: str = _DEFAULT_ENCODING,
) -> list[MessageDiff]:
    """Align and diff two ordered lists of messages.

    Alignment is done by (role, position-within-role). Messages are matched
    by role in the order they appear -- the first system message in old is
    compared with the first system message in new, etc.

    Parameters
    ----------
    old_msgs:
        Messages from the old prompt file.
    new_msgs:
        Messages from the new prompt file.
    encoding:
        tiktoken encoding name for token counting.

    Returns
    -------
    list[MessageDiff]
        Ordered list of message diffs.
    """
    # Group messages by role, preserving order within each role.
    old_by_role: dict[str, list[Message]] = {}
    new_by_role: dict[str, list[Message]] = {}

    for msg in old_msgs:
        old_by_role.setdefault(msg.role, []).append(msg)
    for msg in new_msgs:
        new_by_role.setdefault(msg.role, []).append(msg)

    all_roles_ordered: list[str] = []
    seen: set[str] = set()
    for msg in old_msgs:
        if msg.role not in seen:
            all_roles_ordered.append(msg.role)
            seen.add(msg.role)
    for msg in new_msgs:
        if msg.role not in seen:
            all_roles_ordered.append(msg.role)
            seen.add(msg.role)

    diffs: list[MessageDiff] = []

    for role in all_roles_ordered:
        old_list = old_by_role.get(role, [])
        new_list = new_by_role.get(role, [])

        max_len = max(len(old_list), len(new_list))
        for i in range(max_len):
            old_msg = old_list[i] if i < len(old_list) else None
            new_msg = new_list[i] if i < len(new_list) else None
            diffs.append(_diff_single_message(old_msg, new_msg, role, encoding))

    return diffs


def _diff_single_message(
    old_msg: Optional[Message],
    new_msg: Optional[Message],
    role: str,
    encoding: str,
) -> MessageDiff:
    """Diff a single aligned pair of messages."""
    if old_msg is None and new_msg is not None:
        # Added
        new_tokens = count_tokens(new_msg.content, encoding)
        return MessageDiff(
            status=ChangeStatus.ADDED,
            role=role,
            new_content=new_msg.content,
            token_delta=new_tokens,
            changes=[f"Added {role} message ({new_tokens} tokens)"],
        )

    if old_msg is not None and new_msg is None:
        # Removed
        old_tokens = count_tokens(old_msg.content, encoding)
        return MessageDiff(
            status=ChangeStatus.REMOVED,
            role=role,
            old_content=old_msg.content,
            token_delta=-old_tokens,
            changes=[f"Removed {role} message ({old_tokens} tokens)"],
        )

    # Both exist -- compare content.
    assert old_msg is not None and new_msg is not None

    if old_msg.content == new_msg.content:
        return MessageDiff(
            status=ChangeStatus.UNCHANGED,
            role=role,
            old_content=old_msg.content,
            new_content=new_msg.content,
            token_delta=0,
        )

    # Modified
    old_tokens = count_tokens(old_msg.content, encoding)
    new_tokens = count_tokens(new_msg.content, encoding)
    delta = new_tokens - old_tokens

    content_diff = "\n".join(
        difflib.unified_diff(
            old_msg.content.splitlines(),
            new_msg.content.splitlines(),
            lineterm="",
            fromfile="old",
            tofile="new",
        )
    )

    changes: list[str] = []
    if delta != 0:
        direction = "increased" if delta > 0 else "decreased"
        changes.append(
            f"{role.capitalize()} message {direction} by {abs(delta)} tokens"
        )
    changes.append(f"{role.capitalize()} message content modified")

    return MessageDiff(
        status=ChangeStatus.MODIFIED,
        role=role,
        old_content=old_msg.content,
        new_content=new_msg.content,
        content_diff=content_diff,
        token_delta=delta,
        changes=changes,
    )


def diff_variables(
    old_vars: dict[str, str],
    new_vars: dict[str, str],
    old_defaults: dict[str, str],
    new_defaults: dict[str, str],
) -> list[VariableDiff]:
    """Compare variable sets between old and new prompt versions.

    Parameters
    ----------
    old_vars:
        Variables found in the old version (name -> syntax style).
    new_vars:
        Variables found in the new version (name -> syntax style).
    old_defaults:
        Default values from the old version metadata.
    new_defaults:
        Default values from the new version metadata.

    Returns
    -------
    list[VariableDiff]
        List of variable diffs.
    """
    all_names = sorted(set(old_vars) | set(new_vars))
    diffs: list[VariableDiff] = []

    for name in all_names:
        in_old = name in old_vars
        in_new = name in new_vars

        if in_old and not in_new:
            diffs.append(
                VariableDiff(
                    name=name,
                    status=ChangeStatus.REMOVED,
                    old_default=old_defaults.get(name),
                    is_breaking=True,
                )
            )
        elif not in_old and in_new:
            new_default = new_defaults.get(name)
            # Breaking if no default is provided for the new variable.
            diffs.append(
                VariableDiff(
                    name=name,
                    status=ChangeStatus.ADDED,
                    new_default=new_default,
                    is_breaking=new_default is None,
                )
            )
        else:
            # Present in both -- check if default changed.
            old_def = old_defaults.get(name)
            new_def = new_defaults.get(name)
            if old_def == new_def:
                diffs.append(
                    VariableDiff(
                        name=name,
                        status=ChangeStatus.UNCHANGED,
                        old_default=old_def,
                        new_default=new_def,
                    )
                )
            else:
                diffs.append(
                    VariableDiff(
                        name=name,
                        status=ChangeStatus.MODIFIED,
                        old_default=old_def,
                        new_default=new_def,
                    )
                )

    return diffs


def diff_metadata(
    old_meta: dict[str, Any],
    new_meta: dict[str, Any],
) -> list[MetadataDiff]:
    """Compare metadata dictionaries.

    Parameters
    ----------
    old_meta:
        Metadata from the old prompt file.
    new_meta:
        Metadata from the new prompt file.

    Returns
    -------
    list[MetadataDiff]
        List of metadata diffs.
    """
    all_keys = sorted(set(old_meta) | set(new_meta))
    diffs: list[MetadataDiff] = []

    for key in all_keys:
        in_old = key in old_meta
        in_new = key in new_meta

        if in_old and not in_new:
            diffs.append(
                MetadataDiff(
                    key=key,
                    status=ChangeStatus.REMOVED,
                    old_value=old_meta[key],
                )
            )
        elif not in_old and in_new:
            diffs.append(
                MetadataDiff(
                    key=key,
                    status=ChangeStatus.ADDED,
                    new_value=new_meta[key],
                )
            )
        elif old_meta[key] == new_meta[key]:
            diffs.append(
                MetadataDiff(
                    key=key,
                    status=ChangeStatus.UNCHANGED,
                    old_value=old_meta[key],
                    new_value=new_meta[key],
                )
            )
        else:
            diffs.append(
                MetadataDiff(
                    key=key,
                    status=ChangeStatus.MODIFIED,
                    old_value=old_meta[key],
                    new_value=new_meta[key],
                )
            )

    return diffs


def compute_token_delta(
    old_file: PromptFile,
    new_file: PromptFile,
    encoding: str = _DEFAULT_ENCODING,
) -> TokenDelta:
    """Compute token count comparison between two prompt files.

    Parameters
    ----------
    old_file:
        The old parsed prompt file.
    new_file:
        The new parsed prompt file.
    encoding:
        tiktoken encoding name for token counting.

    Returns
    -------
    TokenDelta
        Token count delta.
    """
    tokenizer = Tokenizer(encoding=encoding)
    old_total = tokenizer.count_file(old_file)
    new_total = tokenizer.count_file(new_file)

    delta = new_total - old_total
    if old_total == 0:
        percent_change = 100.0 if new_total > 0 else 0.0
    else:
        percent_change = round((delta / old_total) * 100, 2)

    return TokenDelta(
        old_total=old_total,
        new_total=new_total,
        delta=delta,
        percent_change=percent_change,
    )
