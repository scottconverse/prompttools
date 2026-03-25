"""Built-in model profiles for context-aware linting.

Delegates to prompttools-core for profile data.
"""

from __future__ import annotations

from typing import Optional

# Re-export from prompttools-core
from prompttools_core.profiles import (  # noqa: F401
    BUILTIN_PROFILES,
    get_profile,
)
from prompttools_core.models import ModelProfile  # noqa: F401
