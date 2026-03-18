"""Tests for ai_agents_core.base — model resolution and agent creation."""

from unittest.mock import MagicMock, patch

import pytest

from ai_agents_core.base import resolve_model

# ── resolve_model ────────────────────────────────────────────────────


class TestResolveModel:
    def _clean_env(self, monkeypatch):
        for var in (
            "MODEL_PROVIDER",
            "MODEL_NAME",
            "GEMINI_MODEL_VERSION",
        ):
            monkeypatch.delenv(var, raising=False)

    def test_defaults_to_gemini(self, monkeypatch):
        self._clean_env(monkeypatch)
        result = resolve_model()
        assert result == "gemini-2.0-flash"

    def test_gemini_model_name_override(self, monkeypatch):
        self._clean_env(monkeypatch)
        monkeypatch.setenv("MODEL_NAME", "gemini-2.5-pro")
        result = resolve_model()
        assert result == "gemini-2.5-pro"

    def test_gemini_legacy_env_var(self, monkeypatch):
        self._clean_env(monkeypatch)
        monkeypatch.setenv("GEMINI_MODEL_VERSION", "gemini-1.5-pro")
        result = resolve_model()
        assert result == "gemini-1.5-pro"

    def test_model_name_takes_precedence_over_legacy(self, monkeypatch):
        self._clean_env(monkeypatch)
        monkeypatch.setenv("MODEL_NAME", "gemini-2.5-pro")
        monkeypatch.setenv("GEMINI_MODEL_VERSION", "gemini-1.5-pro")
        result = resolve_model()
        assert result == "gemini-2.5-pro"

    @patch("ai_agents_core.base.LiteLlm", create=True)
    def test_anthropic_provider(self, mock_litellm_cls, monkeypatch):
        self._clean_env(monkeypatch)
        monkeypatch.setenv("MODEL_PROVIDER", "anthropic")
        monkeypatch.setenv("MODEL_NAME", "anthropic/claude-sonnet-4-20250514")

        # Patch the import inside resolve_model
        mock_instance = MagicMock()
        mock_litellm_cls.return_value = mock_instance

        with patch.dict(
            "sys.modules",
            {"google.adk.models.lite_llm": MagicMock(LiteLlm=mock_litellm_cls)},
        ):
            result = resolve_model()

        assert result is mock_instance
        mock_litellm_cls.assert_called_once_with(model="anthropic/claude-sonnet-4-20250514")

    @patch("ai_agents_core.base.LiteLlm", create=True)
    def test_provider_prefix_auto_added(self, mock_litellm_cls, monkeypatch):
        self._clean_env(monkeypatch)
        monkeypatch.setenv("MODEL_PROVIDER", "openai")
        monkeypatch.setenv("MODEL_NAME", "gpt-4o")

        mock_instance = MagicMock()
        mock_litellm_cls.return_value = mock_instance

        with patch.dict(
            "sys.modules",
            {"google.adk.models.lite_llm": MagicMock(LiteLlm=mock_litellm_cls)},
        ):
            resolve_model()

        # Should auto-prefix with "openai/"
        mock_litellm_cls.assert_called_once_with(model="openai/gpt-4o")

    def test_non_gemini_without_model_name_raises(self, monkeypatch):
        self._clean_env(monkeypatch)
        monkeypatch.setenv("MODEL_PROVIDER", "anthropic")

        with pytest.raises(ValueError, match="MODEL_NAME must be set"):
            resolve_model()

    def test_provider_case_insensitive(self, monkeypatch):
        self._clean_env(monkeypatch)
        monkeypatch.setenv("MODEL_PROVIDER", "GEMINI")
        monkeypatch.setenv("MODEL_NAME", "gemini-2.5-pro")
        result = resolve_model()
        assert result == "gemini-2.5-pro"
