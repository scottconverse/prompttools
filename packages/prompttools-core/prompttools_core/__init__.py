"""prompttools-core: Shared foundation library for the prompttools suite.

Public API exports for convenience imports::

    from prompttools_core import PromptFile, Message, parse_file, Tokenizer
"""

from prompttools_core.errors import (
    CacheError,
    ConfigError,
    ParseError,
    PluginError,
    ProfileNotFoundError,
    PromptToolsError,
    TokenizerError,
)
from prompttools_core.models import (
    Message,
    ModelProfile,
    PipelineStage,
    PromptFile,
    PromptFormat,
    PromptPipeline,
    ToolConfig,
)
from prompttools_core.parser import (
    parse_directory,
    parse_file,
    parse_pipeline,
    parse_stdin,
)
from prompttools_core.tokenizer import Tokenizer, count_tokens, get_encoding
from prompttools_core.profiles import (
    BUILTIN_PROFILES,
    get_profile,
    list_profiles,
    register_profile,
)
from prompttools_core.cache import PromptCache
from prompttools_core.config import find_config_file, load_config
from prompttools_core.plugins import discover_plugins, load_plugin

__version__ = "1.0.0"

__all__ = [
    # Errors
    "CacheError",
    "ConfigError",
    "ParseError",
    "PluginError",
    "ProfileNotFoundError",
    "PromptToolsError",
    "TokenizerError",
    # Models
    "Message",
    "ModelProfile",
    "PipelineStage",
    "PromptFile",
    "PromptFormat",
    "PromptPipeline",
    "ToolConfig",
    # Parser
    "parse_directory",
    "parse_file",
    "parse_pipeline",
    "parse_stdin",
    # Tokenizer
    "Tokenizer",
    "count_tokens",
    "get_encoding",
    # Profiles
    "BUILTIN_PROFILES",
    "get_profile",
    "list_profiles",
    "register_profile",
    # Cache
    "PromptCache",
    # Config
    "find_config_file",
    "load_config",
    # Plugins
    "discover_plugins",
    "load_plugin",
]
