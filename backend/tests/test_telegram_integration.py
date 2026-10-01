"""
backend/tests/test_telegram_integration.py — Tests for Phase 4.2 Telegram Integration.

Verifies:
1. telegram_service degrades safely when TELEGRAM_TOKEN is missing.
2. telegram_service does not make external network requests during unconfigured runs.
3. telegram_service handles successful responses when mocked.
4. telegram_service safely handles timeouts, HTTP errors, and never leaks tokens.
5. POST /nudge/send endpoint behaves correctly across configured and unconfigured states.
"""

import os
from unittest.mock import patch, MagicMock
import requests
import pytest

from backend.telegram_service import (
    is_telegram_configured,
    send_telegram_message,
    _sanitize_log_message,
)


def test_telegram_configured_flag():
    """Verify is_telegram_configured correctly inspects TELEGRAM_TOKEN."""
    with patch.dict(os.environ, {"TELEGRAM_TOKEN": ""}):
        assert not is_telegram_configured()

    with patch.dict(os.environ, {"TELEGRAM_TOKEN": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"}):
        assert is_telegram_configured()


def test_telegram_missing_parameters_return_false():
    """Empty token or chat_id returns False without making any network call."""
    with patch("requests.post") as mock_post:
        assert not send_telegram_message(chat_id="", text="Hello", token="")
        assert not send_telegram_message(chat_id="99999", text="Hello", token="")
        assert not send_telegram_message(chat_id="", text="Hello", token="fake_token")
        mock_post.assert_not_called()


def test_telegram_successful_delivery():
    """Mock successful Telegram API response (HTTP 200)."""
    fake_token = "123456:TEST_TOKEN_SECRET"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"ok": True, "result": {"message_id": 42}}

    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = send_telegram_message(
            chat_id="12345678",
            text="Shift your load today!",
            token=fake_token,
        )
        assert result is True
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert f"bot{fake_token}" in args[0]
        assert kwargs["json"]["chat_id"] == "12345678"
        assert kwargs["json"]["text"] == "Shift your load today!"


def test_telegram_http_error_handled_safely():
    """Telegram API error (e.g. 400 Chat Not Found) is handled without raising."""
    fake_token = "123456:TEST_TOKEN_SECRET"
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = f'{{"ok":false,"error_code":400,"description":"Bad Request: chat not found for {fake_token}"}}'

    with patch("requests.post", return_value=mock_resp):
        result = send_telegram_message(
            chat_id="nonexistent_user",
            text="Test message",
            token=fake_token,
        )
        assert result is False


def test_telegram_network_exception_handled_safely():
    """Network connection timeout is caught and logged safely."""
    fake_token = "123456:TEST_TOKEN_SECRET"
    with patch("requests.post", side_effect=requests.exceptions.ConnectTimeout("Connection timed out")):
        result = send_telegram_message(
            chat_id="12345678",
            text="Test message",
            token=fake_token,
        )
        assert result is False


def test_token_sanitization():
    """Confirm tokens are redacted from error logs."""
    token = "987654321:AAFakeSecretBotTokenKey123"
    raw_message = f"Failed to call https://api.telegram.org/bot{token}/sendMessage with error"
    sanitized = _sanitize_log_message(raw_message, token)
    assert token not in sanitized
    assert "[REDACTED_TELEGRAM_TOKEN]" in sanitized or "[REDACTED_TOKEN]" in sanitized


def test_api_nudge_send_without_telegram_token(client):
    """When TELEGRAM_TOKEN is unset, /nudge/send returns api_only and delivered=False."""
    with patch.dict(os.environ, {"TELEGRAM_TOKEN": ""}):
        resp = client.post("/nudge/send", json={"household_id": "HH001"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["channel"] == "api_only"
        assert body["delivered"] is False


def test_api_nudge_send_with_token_no_chat_id(client):
    """When TELEGRAM_TOKEN is set but no chat_id given, returns telegram channel with delivered=False."""
    with patch.dict(os.environ, {"TELEGRAM_TOKEN": "123456:FAKE_TOKEN"}):
        resp = client.post("/nudge/send", json={"household_id": "HH001"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["channel"] == "telegram"
        assert body["delivered"] is False


def test_api_nudge_send_with_token_and_chat_id_success(fresh_client):
    """When TELEGRAM_TOKEN is set and chat_id is provided, sends via mocked telegram service."""
    # Run optimize first to create pending nudges
    fresh_client.post("/optimize", json={"scenario": "sunny"})
    
    with patch.dict(os.environ, {"TELEGRAM_TOKEN": "123456:FAKE_TOKEN"}):
        with patch("backend.telegram_service.send_telegram_message", return_value=True) as mock_send:
            resp = fresh_client.post(
                "/nudge/send",
                json={"household_id": "HH001", "chat_id": "987654"}
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["channel"] == "telegram"
            # If there were pending nudges for HH001, delivered is True
            if body["nudges_queued"] > 0:
                assert body["delivered"] is True
                mock_send.assert_called()
            else:
                assert body["delivered"] is False
