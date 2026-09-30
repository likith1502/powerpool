"""
Unit tests for SQLite database schema and records
"""

import os
import pytest
import sqlite3
import pandas as pd
from data.generator import build_and_populate_dataset, DB_PATH
from ml.pipeline import populate_demo_forecasts

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "test_db_powerpool.db")

@pytest.fixture(scope="module")
def full_db():
    build_and_populate_dataset(num_households=50, days=2, seed=42, db_path=TEST_DB_PATH)
    populate_demo_forecasts(db_path=TEST_DB_PATH)
    yield TEST_DB_PATH
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_required_tables(full_db):
    conn = sqlite3.connect(full_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()
    assert {"households", "appliances", "load_history", "weather", "forecast", "nudges"}.issubset(tables)

def test_required_columns(full_db):
    conn = sqlite3.connect(full_db)
    df_forecast = pd.read_sql("SELECT * FROM forecast LIMIT 1", conn)
    conn.close()
    assert set(df_forecast.columns) == {"timestamp", "demand_kw", "solar_kw", "capacity_kw", "gap_kw", "is_stress"}

def test_forecast_row_count(full_db):
    conn = sqlite3.connect(full_db)
    df_forecast = pd.read_sql("SELECT * FROM forecast", conn)
    conn.close()
    assert len(df_forecast) == 288
