"""
Unit tests for forecasting and gap formula logic
"""

import os
import pytest
import sqlite3
import pandas as pd
from data.generator import build_and_populate_dataset, DB_PATH
from ml.pipeline import build_forecast_for_date

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "test_forecast_powerpool.db")

@pytest.fixture(scope="module")
def setup_db():
    build_and_populate_dataset(num_households=20, days=3, seed=42, db_path=TEST_DB_PATH)
    yield TEST_DB_PATH
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_forecast_has_96_slots(setup_db):
    df_f = build_forecast_for_date("2026-10-01", scenario="sunny", db_path=setup_db)
    assert len(df_f) == 96

def test_forecast_schema(setup_db):
    df_f = build_forecast_for_date("2026-10-01", scenario="sunny", db_path=setup_db)
    expected_cols = {"timestamp", "demand_kw", "solar_kw", "capacity_kw", "gap_kw", "is_stress"}
    assert expected_cols.issubset(set(df_f.columns))

def test_gap_formula(setup_db):
    df_f = build_forecast_for_date("2026-10-01", scenario="sunny", db_path=setup_db)
    calc_gap = (df_f["demand_kw"] - df_f["solar_kw"] - df_f["capacity_kw"]).round(2)
    assert (df_f["gap_kw"] == calc_gap).all()

def test_stress_flag(setup_db):
    df_f = build_forecast_for_date("2026-10-01", scenario="sunny", db_path=setup_db)
    expected_stress = (df_f["gap_kw"] > 0).astype(int)
    assert (df_f["is_stress"] == expected_stress).all()
