"""
backend/tests/test_ai_personalization.py — Tests for Phase 4.3 AI Nudge Personalization.

Verifies:
1. Default behavior is 100% deterministic template fallback.
2. AI Personalization is strictly opt-in via AI_NUDGE_PERSONALIZATION and ANTHROPIC_API_KEY.
3. Mocked Anthropic client generates personalized nudge when enabled.
4. Safe fallback to deterministic template on API failure, timeout, or missing key.
5. No household personal information (PII) is included in LLM prompts.
6. Automated tests make ZERO real external network calls.
"""

import os
from unittest.mock import patch, MagicMock
import pytest

from backend.translations import (
    nudge_text,
    personalize_nudge,
    is_ai_personalization_enabled,
)


def test_ai_personalization_disabled_by_default():
    """Verify AI personalization is off by default."""
    with patch.dict(os.environ, {"AI_NUDGE_PERSONALIZATION": "", "ANTHROPIC_API_KEY": ""}):
        assert not is_ai_personalization_enabled()


def test_ai_personalization_enabled_flag():
    """Verify flag is True only when both config flag and API key are set."""
    with patch.dict(os.environ, {"AI_NUDGE_PERSONALIZATION": "true", "ANTHROPIC_API_KEY": "sk-ant-test"}):
        assert is_ai_personalization_enabled()

    with patch.dict(os.environ, {"AI_NUDGE_PERSONALIZATION": "false", "ANTHROPIC_API_KEY": "sk-ant-test"}):
        assert not is_ai_personalization_enabled()

    with patch.dict(os.environ, {"AI_NUDGE_PERSONALIZATION": "true", "ANTHROPIC_API_KEY": ""}):
        assert not is_ai_personalization_enabled()


def test_personalize_nudge_fallback_when_disabled():
    """When disabled, returns deterministic template text."""
    with patch.dict(os.environ, {"AI_NUDGE_PERSONALIZATION": "false"}):
        result = personalize_nudge("Geyser", 74, 50, 20, 5.0, lang="en")
        expected = nudge_text("Geyser", 74, 50, 20, 5.0, lang="en")
        assert result == expected


def test_personalize_nudge_mocked_success():
    """When enabled with mock Anthropic client, returns polished AI nudge."""
    mock_msg = MagicMock()
    mock_content = MagicMock()
    mock_content.text = "Hey! Move your Geyser run to 12:30 today to grab 20 points and save Rs 5!"
    mock_msg.content = [mock_content]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_msg

    with patch.dict(os.environ, {"AI_NUDGE_PERSONALIZATION": "true", "ANTHROPIC_API_KEY": "sk-ant-mock"}):
        with patch("anthropic.Anthropic", return_value=mock_client):
            result = personalize_nudge("Geyser", 74, 50, 20, 5.0, lang="en")
            assert result == "Hey! Move your Geyser run to 12:30 today to grab 20 points and save Rs 5!"
            mock_client.messages.create.assert_called_once()
            call_kwargs = mock_client.messages.create.call_args.kwargs
            prompt = call_kwargs["messages"][0]["content"]
            # Verify no PII in prompt
            assert "HH00" not in prompt
            assert "Sharma" not in prompt
            assert "Block" not in prompt
            assert "Geyser" in prompt


def test_personalize_nudge_fallback_on_exception():
    """When Anthropic API errors, safely returns deterministic fallback."""
    with patch.dict(os.environ, {"AI_NUDGE_PERSONALIZATION": "true", "ANTHROPIC_API_KEY": "sk-ant-mock"}):
        with patch("anthropic.Anthropic", side_effect=Exception("API connection error")):
            result = personalize_nudge("Washing machine", 76, 44, 45, 13.5, lang="en")
            expected = nudge_text("Washing machine", 76, 44, 45, 13.5, lang="en")
            assert result == expected
