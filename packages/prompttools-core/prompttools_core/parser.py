"""Multi-format prompt file parser.

Auto-detects format from file extension, delegates to format-specific
parsers, and provides directory and pipeline scanning.
"""

from __future__ import annotations

import fnmatch
import logging
from pathlib import Path
from typing import Optional

import yaml

from prompttools_core.errors import ParseError
from prompttools_core.models import (
    PipelineStage,
    PromptFile,
    PromptFormat,
    PromptPipeline,
    ToolConfig,
)
from prompttools_core.formats.text import parse_text
from prompttools_core.formats.markdown import parse_markdown
from prompttools_core.formats.yaml_parser import parse_yaml
from prompttools_core.formats.json_parser import parse_json
from prompttools_core.formats._variables import extract_variables  # noqa: F401 (re-export)

logger = logging.getLogger(__name__)

_FORMAT_MAP: dict[str, PromptFormat] = {
    ".txt": PromptFormat.TEXT,
    ".md": PromptFormat.MARKDOWN,
    ".yaml": PromptFormat.YAML,
    ".yml": PromptFormat.YAML,
    ".json": PromptFormat.JSON,
}

_SUB_PARSERS = {
    PromptFormat.TEXT: parse_text,
    PromptFormat.MARKDOWN: parse_markdown,
    PromptFormat.YAML: parse_yaml,
    PromptFormat.JSON: parse_json,
}


def _detect_format(path: Path) -> PromptFormat:
    """Determine prompt format from the file extension."""
    ext = path.suffix.lower()
    fmt = _FORMAT_MAP.get(ext)
    if fmt is None:
        raise ParseError(
            f"Unsupported file extension '{ext}' for {path}. "
            f"Supported: {', '.join(_FORMAT_MAP)}"
        )
    return fmt


def parse_file(path: Path, config: Optional[ToolConfig] = None) -> PromptFile:
    """Parse a prompt file at *path*, auto-detecting format by extension.

    Parameters
    ----------
    path:
        Path to the prompt file.
    config:
        Optional tool configuration (currently unused, reserved for future).

    Returns
    -------
    PromptFile
        The parsed prompt.

    Raises
    ------
    ParseError
        If the format is unsupported or the file content is malformed.
    FileNotFoundError
        If the file does not exist.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    fmt = _detect_format(path)
    content = path.read_text(encoding="utf-8")
    parser_fn = _SUB_PARSERS[fmt]
    return parser_fn(path, content)


def parse_stdin(content: str, format: str) -> PromptFile:
    """Parse prompt content read from stdin.

    Parameters
    ----------
    content:
        The raw text read from stdin.
    format:
        One of ``text``, ``md``, ``yaml``, ``json``.

    Returns
    -------
    PromptFile
        The parsed prompt with ``path`` set to ``Path("-")``.
    """
    fmt_map = {
        "text": PromptFormat.TEXT,
        "md": PromptFormat.MARKDOWN,
        "yaml": PromptFormat.YAML,
        "json": PromptFormat.JSON,
    }
    fmt = fmt_map.get(format)
    if fmt is None:
        raise ParseError(
            f"Unsupported input format '{format}'. "
            f"Supported: {', '.join(fmt_map)}"
        )

    stdin_path = Path("-")
    parser_fn = _SUB_PARSERS[fmt]
    return parser_fn(stdin_path, content)


def parse_directory(
    path: Path,
    config: Optional[ToolConfig] = None,
    patterns: Optional[list[str]] = None,
) -> list[PromptFile]:
    """Parse all prompt files in a directory.

    Parameters
    ----------
    path:
        Directory to scan.
    config:
        Optional config with ``exclude`` patterns.
    patterns:
        Glob patterns to match (default: all supported extensions).

    Returns
    -------
    list[PromptFile]
        Parsed prompt files, skipping any that fail to parse.
    """
    path = Path(path)
    if not path.is_dir():
        raise ParseError(f"Not a directory: {path}")

    if patterns is None:
        patterns = [f"*{ext}" for ext in _FORMAT_MAP]

    exclude = config.exclude if config else []

    results: list[PromptFile] = []
    for pattern in patterns:
        for file_path in sorted(path.rglob(pattern)):
            # Check excludes
            rel = str(file_path.relative_to(path))
            if any(fnmatch.fnmatch(rel, ex) for ex in exclude):
                continue
            try:
                results.append(parse_file(file_path, config))
            except (ParseError, FileNotFoundError) as exc:
                logger.warning("Failed to parse %s: %s", file_path, exc)
                continue

    return results


def parse_pipeline(
    manifest_path: Path,
    config: Optional[ToolConfig] = None,
) -> PromptPipeline:
    """Parse a pipeline manifest and all referenced prompt files.

    Parameters
    ----------
    manifest_path:
        Path to the pipeline manifest YAML.
    config:
        Optional tool configuration.

    Returns
    -------
    PromptPipeline
        A pipeline with all stages parsed.

    Raises
    ------
    ParseError
        If the manifest is malformed or a referenced file is missing.
    """
    manifest_path = Path(manifest_path)
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Pipeline manifest not found: {manifest_path}")

    content = manifest_path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ParseError(f"Invalid YAML in pipeline manifest {manifest_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ParseError(f"Pipeline manifest {manifest_path} must be a YAML mapping")

    name = str(data.get("name", manifest_path.stem))
    model = data.get("model")
    manifest_dir = manifest_path.parent

    stages_raw = data.get("stages")
    if not isinstance(stages_raw, list):
        raise ParseError(f"Pipeline manifest {manifest_path} must contain a 'stages' list")

    stages: list[PipelineStage] = []
    for stage_raw in stages_raw:
        if not isinstance(stage_raw, dict):
            raise ParseError("Each pipeline stage must be a mapping")

        stage_name = str(stage_raw.get("name", "unnamed"))
        file_rel = stage_raw.get("file")
        if not file_rel:
            raise ParseError(f"Pipeline stage '{stage_name}' is missing 'file' key")

        prompt_path = manifest_dir / file_rel
        prompt_file = parse_file(prompt_path, config)

        depends_on = stage_raw.get("depends_on", [])
        if not isinstance(depends_on, list):
            depends_on = [depends_on]

        stages.append(
            PipelineStage(
                name=stage_name,
                file=Path(file_rel),
                prompt_file=prompt_file,
                depends_on=[str(d) for d in depends_on],
                expected_output_tokens=stage_raw.get("expected_output_tokens", 0),
                persona=stage_raw.get("persona"),
            )
        )

    return PromptPipeline(
        name=name,
        model=model,
        stages=stages,
        manifest_path=manifest_path.resolve(),
    )
