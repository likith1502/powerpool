"""
Telegram Notification Service for PowerPool.

Provides safe, optional, token-sanitized push delivery of nudges to Telegram.
Adheres strictly to Phase 4.2 requirements:
- Fully optional: core app works without TELEGRAM_TOKEN.
- Tokens read from environment variable only.
- Tokens are never exposed in logs or exception messages.
- Network errors and Telegram API errors are caught and logged safely.
- No real network calls are made during automated tests.
"""

import os
import re
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


def _sanitize_log_message(msg: str, token: Optional[str] = None) -> str:
    """Strip token from any log or error string."""
    if token and token in msg:
        msg = msg.replace(token, "[REDACTED_TELEGRAM_TOKEN]")
    # Also strip any bot<token> pattern
    return re.sub(r"bot\d+:[A-Za-z0-9_-]+", "bot[REDACTED_TOKEN]", msg)


def is_telegram_configured() -> bool:
    """Return True if TELEGRAM_TOKEN is set in environment."""
    return bool(os.getenv("TELEGRAM_TOKEN", "").strip())


def send_telegram_message(
    chat_id: str,
    text: str,
    token: Optional[str] = None,
    timeout: int = 5,
) -> bool:
    """
    Send a text message to a specific Telegram chat_id.
    
    Returns True if sent successfully, False otherwise.
    Safe against network errors, invalid tokens, and non-existent chat IDs.
    """
    active_token = token or os.getenv("TELEGRAM_TOKEN", "").strip()
    if not active_token:
        logger.debug("Telegram delivery skipped: TELEGRAM_TOKEN not configured.")
        return False

    if not chat_id:
        logger.debug("Telegram delivery skipped: chat_id not provided.")
        return False

    url = f"https://api.telegram.org/bot{active_token}/sendMessage"
    payload = {
        "chat_id": str(chat_id),
        "text": text,
        "parse_mode": "HTML",
    }

    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        if resp.status_code == 200:
            logger.info("Telegram notification delivered successfully to chat_id=%s", chat_id)
            return True
        else:
            sanitized_err = _sanitize_log_message(resp.text, active_token)
            logger.warning("Telegram API error status=%d: %s", resp.status_code, sanitized_err)
            return False
    except requests.RequestException as exc:
        sanitized_err = _sanitize_log_message(str(exc), active_token)
        logger.warning("Telegram network failure: %s", sanitized_err)
        return False
    except Exception as exc:
        sanitized_err = _sanitize_log_message(str(exc), active_token)
        logger.error("Unexpected error delivering Telegram message: %s", sanitized_err)
        return False
