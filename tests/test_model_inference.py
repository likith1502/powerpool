"""
Unit tests to verify production demand inference path loads trained LightGBM artifact
and invokes predict(), while making fallback explicit.
"""

import os
import pytest
import sqlite3
import pandas as pd
from unittest.mock import MagicMock, patch

from ml.forecast_demand import predict_demand, load_demand_model, MODEL_PATH
from ml.pipeline import build_forecast_for_date


def test_predict_demand_uses_lightgbm_predict():
    """
    Verifies that predict_demand actually loads the LightGBM model artifact and calls predict().
    """
    model, model_source = load_demand_model(MODEL_PATH)
    assert model_source == "lightgbm", "Expected model_source to be 'lightgbm'"

    # Create a mock booster
    mock_booster = MagicMock()
    mock_booster.predict.return_value = [125.0]

    with patch("ml.forecast_demand.load_demand_model", return_value=(mock_booster, "lightgbm")):
        conn = sqlite3.connect("data/powerpool.db")
        df_load = pd.read_sql("SELECT household_id, timestamp, kwh FROM load_history", conn)
        weather_df = pd.read_sql("SELECT timestamp, temp_c, cloud_cover, irradiance_wm2 FROM weather", conn)
        conn.close()

        target_ts = [pd.Timestamp("2026-10-01 00:00:00") + pd.Timedelta(minutes=15 * i) for i in range(96)]
        
        demand_df, source = predict_demand(df_load, weather_df, target_ts)

        assert source == "lightgbm"
        assert mock_booster.predict.call_count == 96, f"Expected 96 predict calls, got {mock_booster.predict.call_count}"
        assert len(demand_df) == 96
        assert (demand_df["demand_kw"] == 125.0).all()


def test_pipeline_build_forecast_invokes_lightgbm():
    """
    Verifies that build_forecast_for_date invokes LightGBM predict and returns model_source attribute.
    """
    df_f = build_forecast_for_date("2026-10-01", scenario="sunny")
    assert len(df_f) == 96
    assert df_f.attrs.get("model_source") == "lightgbm"


def test_predict_demand_fallback_detection(tmp_path):
    """
    Verifies that when model artifact cannot be loaded, model_source is explicitly 'seasonal_baseline'.
    """
    non_existent_path = str(tmp_path / "non_existent_model.txt")
    
    conn = sqlite3.connect("data/powerpool.db")
    df_load = pd.read_sql("SELECT household_id, timestamp, kwh FROM load_history", conn)
    weather_df = pd.read_sql("SELECT timestamp, temp_c, cloud_cover, irradiance_wm2 FROM weather", conn)
    conn.close()

    target_ts = [pd.Timestamp("2026-10-01 00:00:00") + pd.Timedelta(minutes=15 * i) for i in range(96)]

    demand_df, source = predict_demand(df_load, weather_df, target_ts, model_path=non_existent_path)
    
    assert source == "seasonal_baseline", f"Expected 'seasonal_baseline', got '{source}'"
    assert len(demand_df) == 96
