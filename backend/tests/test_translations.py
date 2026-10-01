"""
test_translations.py — Unit tests for multilingual nudge text generation and fallbacks.

Tests cover:
  - All six flexible appliance categories across Hindi and Telugu.
  - Unicode script assertions for Devanagari and Telugu blocks.
  - Template formatting (slots, points, savings).
  - Graceful fallback for unsupported languages and unknown appliances.
  - Deterministic behavior of llm_translate without API credentials.
"""
import pytest
from backend.translations import nudge_text, llm_translate, APPLIANCE_NAMES

ALL_APPLIANCES = [
    "Washing machine",
    "Water pump",
    "Inverter charging",
    "Geyser",
    "Iron",
    "E-rickshaw charging",
]


def has_devanagari(text: str) -> bool:
    """Check if string contains any character in the Devanagari Unicode block (U+0900 - U+097F)."""
    return any("\u0900" <= ch <= "\u097F" for ch in text)


def has_telugu(text: str) -> bool:
    """Check if string contains any character in the Telugu Unicode block (U+0C00 - U+0C7F)."""
    return any("\u0C00" <= ch <= "\u0C7F" for ch in text)


@pytest.mark.parametrize("appliance", ALL_APPLIANCES)
def test_hindi_translation_all_appliances(appliance):
    """Verify Hindi nudge text contains Devanagari text and localized appliance name."""
    from_slot, to_slot, points, saving = 76, 52, 10, 3.0
    text = nudge_text(appliance, from_slot, to_slot, points, saving, lang="hi")

    assert isinstance(text, str)
    assert len(text.strip()) > 0
    assert has_devanagari(text), f"Expected Devanagari script in Hindi text: '{text}'"

    # Verify localized appliance name is present
    expected_hi_name = APPLIANCE_NAMES[appliance]["hi"]
    assert expected_hi_name in text, f"Expected '{expected_hi_name}' in '{text}'"


@pytest.mark.parametrize("appliance", ALL_APPLIANCES)
def test_telugu_translation_all_appliances(appliance):
    """Verify Telugu nudge text contains Telugu script and localized appliance name."""
    from_slot, to_slot, points, saving = 76, 52, 10, 3.0
    text = nudge_text(appliance, from_slot, to_slot, points, saving, lang="te")

    assert isinstance(text, str)
    assert len(text.strip()) > 0
    assert has_telugu(text), f"Expected Telugu script in Telugu text: '{text}'"

    # Verify localized appliance name is present
    expected_te_name = APPLIANCE_NAMES[appliance]["te"]
    assert expected_te_name in text, f"Expected '{expected_te_name}' in '{text}'"


def test_english_translation():
    """Verify standard English template formatting."""
    text = nudge_text("Geyser", 74, 50, 15, 4.5, lang="en")
    assert isinstance(text, str)
    assert "Geyser" in text
    assert "18:30" in text  # slot 74 -> 18:30
    assert "12:30" in text  # slot 50 -> 12:30
    assert "15 points" in text


def test_unsupported_language_fallback():
    """Unsupported language codes must fall back to the English template."""
    text_fr = nudge_text("Water pump", 76, 48, 8, 2.4, lang="fr")
    text_en = nudge_text("Water pump", 76, 48, 8, 2.4, lang="en")
    assert text_fr == text_en
    assert "Run your Water pump at" in text_fr


def test_unknown_appliance_graceful_handling():
    """Appliances not present in APPLIANCE_NAMES should format cleanly without raising errors."""
    text_hi = nudge_text("Air Conditioner", 80, 56, 20, 6.0, lang="hi")
    assert "Air Conditioner" in text_hi
    assert has_devanagari(text_hi)

    text_te = nudge_text("Air Conditioner", 80, 56, 20, 6.0, lang="te")
    assert "Air Conditioner" in text_te
    assert has_telugu(text_te)


def test_llm_translate_fallback_without_api_key():
    """llm_translate must return the original text untouched when no API key is set."""
    sample = "Run your Geyser at 12:30 today instead of 18:30."
    assert llm_translate(sample, "en") == sample
    assert llm_translate(sample, "hi") == sample
    assert llm_translate(sample, "te") == sample
