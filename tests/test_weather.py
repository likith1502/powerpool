"""
Unit tests for data/weather.py
"""

import pytest
import pandas as pd
from data.weather import generate_synthetic_weather, get_weather_with_fallback, validate_weather_data

def test_weather_schema():
    df = generate_synthetic_weather("2026-09-01", days=2)
    assert len(df) == 2 * 96
    assert set(df.columns) == {"timestamp", "temp_c", "cloud_cover", "irradiance_wm2"}

def test_weather_fallback():
    df = get_weather_with_fallback("2026-09-01", days=1)
    assert len(df) == 96
    assert validate_weather_data(df)

def test_irradiance_nonnegative():
    df = generate_synthetic_weather("2026-09-01", days=5)
    assert (df["irradiance_wm2"] >= 0).all()
    assert not df["temp_c"].isna().any()
