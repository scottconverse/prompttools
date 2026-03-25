"""Tests for prompttools_core.profiles."""

import pytest

from prompttools_core.models import ModelProfile
from prompttools_core.profiles import (
    BUILTIN_PROFILES,
    _custom_profiles,
    get_profile,
    list_profiles,
    register_profile,
)


class TestGetProfile:
    def test_known_profiles(self):
        for name in ("gpt-4", "gpt-4o", "claude-3-haiku", "gemini-1.5-pro"):
            profile = get_profile(name)
            assert profile is not None
            assert profile.name == name

    def test_unknown_profile_returns_none(self):
        assert get_profile("nonexistent-model-xyz") is None


class TestBuiltinProfiles:
    def test_all_have_pricing(self):
        for name, profile in BUILTIN_PROFILES.items():
            assert profile.input_price_per_mtok is not None, (
                f"{name} missing input_price_per_mtok"
            )
            assert profile.output_price_per_mtok is not None, (
                f"{name} missing output_price_per_mtok"
            )

    def test_all_have_encoding(self):
        for name, profile in BUILTIN_PROFILES.items():
            assert profile.encoding, f"{name} missing encoding"

    def test_all_have_context_window(self):
        for name, profile in BUILTIN_PROFILES.items():
            assert profile.context_window > 0, f"{name} has invalid context_window"


class TestListProfiles:
    def test_includes_all_builtin(self):
        profiles = list_profiles()
        for name in BUILTIN_PROFILES:
            assert name in profiles


class TestRegisterProfile:
    def test_register_custom_profile(self):
        custom = ModelProfile(
            name="test-custom-model",
            context_window=2048,
            encoding="cl100k_base",
            provider="custom",
            input_price_per_mtok=1.0,
            output_price_per_mtok=2.0,
        )
        try:
            register_profile(custom)
            retrieved = get_profile("test-custom-model")
            assert retrieved is not None
            assert retrieved.name == "test-custom-model"
            assert retrieved.provider == "custom"

            # Should appear in list_profiles
            assert "test-custom-model" in list_profiles()
        finally:
            # Clean up to avoid polluting other tests
            _custom_profiles.pop("test-custom-model", None)

    def test_custom_overrides_builtin(self):
        custom = ModelProfile(
            name="gpt-4",
            context_window=999,
            encoding="cl100k_base",
            provider="custom-override",
        )
        try:
            register_profile(custom)
            profile = get_profile("gpt-4")
            assert profile is not None
            assert profile.provider == "custom-override"
            assert profile.context_window == 999
        finally:
            _custom_profiles.pop("gpt-4", None)
