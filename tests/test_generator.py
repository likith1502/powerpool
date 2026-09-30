"""
Unit tests for data/generator.py
"""

import os
import pytest
import pandas as pd
from data.generator import generate_households_and_appliances, generate_load_history, REQUIRED_FLEXIBLE_APPLIANCES

def test_household_count():
    households, appliances = generate_households_and_appliances(num_households=100, seed=42)
    assert len(households) == 100

def test_appliance_schema():
    households, appliances = generate_households_and_appliances(num_households=100, seed=42)
    assert len(appliances) > 0
    app_names = {app["name"] for app in appliances}
    for req_app in REQUIRED_FLEXIBLE_APPLIANCES:
        assert req_app in app_names

def test_load_resolution():
    households, appliances = generate_households_and_appliances(num_households=5, seed=42)
    df_load = generate_load_history(households, appliances, start_date="2026-09-01", days=1, seed=42)
    # 5 households x 96 slots = 480 rows
    assert len(df_load) == 5 * 96

def test_no_negative_load():
    households, appliances = generate_households_and_appliances(num_households=10, seed=42)
    df_load = generate_load_history(households, appliances, start_date="2026-09-01", days=2, seed=42)
    assert (df_load["kwh"] >= 0).all()

def test_deterministic_seed():
    h1, a1 = generate_households_and_appliances(num_households=10, seed=42)
    h2, a2 = generate_households_and_appliances(num_households=10, seed=42)
    assert h1 == h2
    assert a1 == a2
