"""
test_ui_provenance_labels.py — Regression tests for honest data-source labelling across UI translations and API schema.
"""
import pytest
from frontend.ui_strings import t, LANG_CODES
from backend.schemas import ForecastSlot


def test_data_source_labels_all_languages():
    """Verify that data_source_model and data_source_mock are accurately translated and non-empty across all languages."""
    for lang in LANG_CODES:
        model_label = t("data_source_model", lang)
        mock_label = t("data_source_mock", lang)

        assert model_label and not model_label.startswith("[")
        assert mock_label and not mock_label.startswith("[")

        # Explicitly verify honesty: must mention precomputed/scenario, NOT claim live inference
        if lang == "en":
            assert "precomputed scenario" in model_label.lower()
            assert "seeded demo" in mock_label.lower()


def test_data_source_fallback_language():
    """Verify that requesting an unknown language falls back to English."""
    assert t("data_source_model", "fr") == "📊 Precomputed scenario forecast"
    assert t("data_source_mock", "de") == "📋 Seeded demo data"


def test_forecast_slot_schema_accepts_model_and_mock():
    """Verify backend schema validation accepts both 'model' and 'mock' data sources."""
    slot_model = ForecastSlot(
        slot=0, time="00:00", demand_kw=100.0, solar_kw=0.0,
        capacity_kw=170.0, gap_kw=-70.0, is_stress=False, data_source="model"
    )
    assert slot_model.data_source == "model"

    slot_mock = ForecastSlot(
        slot=0, time="00:00", demand_kw=100.0, solar_kw=0.0,
        capacity_kw=170.0, gap_kw=-70.0, is_stress=False, data_source="mock"
    )
    assert slot_mock.data_source == "mock"
