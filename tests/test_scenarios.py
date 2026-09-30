"""
Unit tests for demo scenarios (sunny, cloudy, heatwave)
"""

import pytest
import pandas as pd
from ml.pipeline import build_forecast_for_date

def test_sunny_scenario():
    df = build_forecast_for_date("2026-10-01", scenario="sunny")
    assert len(df) == 96
    # Midday solar output should be positive
    midday_solar = df.iloc[40:60]["solar_kw"].max()
    assert midday_solar > 20.0

def test_cloudy_scenario():
    df_sunny = build_forecast_for_date("2026-10-01", scenario="sunny")
    df_cloudy = build_forecast_for_date("2026-10-02", scenario="cloudy")
    # Cloudy midday solar should be less than sunny midday solar
    assert df_cloudy.iloc[48]["solar_kw"] < df_sunny.iloc[48]["solar_kw"]

def test_heatwave_scenario():
    df_heatwave = build_forecast_for_date("2026-10-03", scenario="heatwave")
    assert len(df_heatwave) == 96
    peak = df_heatwave["demand_kw"].max()
    assert peak > 170.0
