"""
Integration tests for Member A pipeline + Backend collaboration.
Tests run strictly against isolated temporary databases and never modify the working database.
"""
import os
import sqlite3
import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch

from backend.db import init_db, rows
from backend import services as svc
from backend.schemas import Household, Nudge, ForecastSlot, KPIs
from data.generator import build_and_populate_dataset
from ml.pipeline import build_forecast_for_date, populate_demo_forecasts
from ml.forecast_solar import forecast_solar
from data.weather import get_weather_with_fallback


@pytest.fixture
def temp_db(tmp_path):
    """Provides an isolated SQLite database path deleted after test."""
    db_file = str(tmp_path / "test_integration.db")
    return db_file


def test_fresh_database_initialization(temp_db):
    """Verify that init_db creates all required tables with string household ID support."""
    with patch("backend.db.DB_PATH", temp_db):
        init_db()

    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "households" in tables
    assert "appliances" in tables
    assert "forecast" in tables
    assert "nudges" in tables
    assert "load_history" in tables
    assert "weather" in tables

    # Verify column types
    hh_cols = {r[1]: r[2] for r in cursor.execute("PRAGMA table_info(households)").fetchall()}
    assert hh_cols["id"] == "TEXT"

    nudge_cols = {r[1]: r[2] for r in cursor.execute("PRAGMA table_info(nudges)").fetchall()}
    assert "source" in nudge_cols
    assert nudge_cols["household_id"] == "TEXT"
    conn.close()


def test_existing_database_migration_and_idempotency(temp_db):
    """Verify safe migration on pre-existing Member A database missing 'source'."""
    conn = sqlite3.connect(temp_db)
    # Create tables in legacy state without 'source' column
    conn.executescript("""
    CREATE TABLE households (id TEXT PRIMARY KEY, name TEXT, type TEXT, block TEXT, language TEXT, points INTEGER);
    CREATE TABLE nudges (id INTEGER PRIMARY KEY AUTOINCREMENT, household_id TEXT, appliance_id INTEGER,
                         from_slot INTEGER, to_slot INTEGER, kwh_shifted REAL, points INTEGER,
                         saving_rs REAL, status TEXT DEFAULT 'pending');
    INSERT INTO households VALUES ('HH001', 'Test House', 'mid', 'Block A', 'en', 10);
    INSERT INTO nudges (household_id, appliance_id, from_slot, to_slot, kwh_shifted, points, saving_rs)
    VALUES ('HH001', 1, 76, 44, 2.0, 50, 12.0);
    """)
    conn.commit()
    conn.close()

    # Run init_db migration
    with patch("backend.db.DB_PATH", temp_db):
        init_db()
        # Call second time to test idempotency
        init_db()

    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cols = [r[1] for r in cursor.execute("PRAGMA table_info(nudges)").fetchall()]
    assert "source" in cols

    # Verify existing row preservation
    row = cursor.execute("SELECT household_id, points, source FROM nudges WHERE id = 1").fetchone()
    assert row[0] == "HH001"
    assert row[1] == 50
    assert row[2] == "optimize"

    hh = cursor.execute("SELECT id, points FROM households WHERE id = 'HH001'").fetchone()
    assert hh[0] == "HH001"
    assert hh[1] == 10
    conn.close()


def test_ml_pipeline_generation_and_persistence(temp_db):
    """Verify data generation, forecast building, and persistence against isolated DB."""
    # 1. Generate small synthetic dataset
    build_and_populate_dataset(num_households=10, days=2, seed=42, db_path=temp_db)

    # 2. Build forecast dataframe for sunny scenario
    df_forecast = build_forecast_for_date("2026-10-01", scenario="sunny", db_path=temp_db)
    assert len(df_forecast) == 96
    assert set(df_forecast.columns) >= {"timestamp", "demand_kw", "solar_kw", "capacity_kw", "gap_kw", "is_stress"}
    assert (df_forecast["demand_kw"] >= 0).all()
    assert (df_forecast["solar_kw"] >= 0).all()

    # 3. Populate demo forecasts
    full_df = populate_demo_forecasts(db_path=temp_db)
    assert len(full_df) == 288  # 3 days x 96 slots

    # 4. Backend load_forecast retrieval
    with patch("backend.db.DB_PATH", temp_db):
        f_slots = svc.load_forecast("2026-10-01")
        assert len(f_slots) == 96
        assert f_slots[0]["timestamp"].startswith("2026-10-01")


def test_resident_workflow_end_to_end(temp_db):
    """Verify complete resident workflow: retrieve HH -> nudges -> respond -> points update."""
    build_and_populate_dataset(num_households=5, days=2, seed=42, db_path=temp_db)
    populate_demo_forecasts(db_path=temp_db)

    with patch("backend.db.DB_PATH", temp_db):
        init_db()
        # 1. List households
        hh_list = rows("SELECT * FROM households ORDER BY id")
        assert len(hh_list) == 5
        target_id = hh_list[0]["id"]
        assert target_id == "HH001"

        # 2. Run optimize to generate nudges
        opt = svc.run_optimize("2026-10-01")
        assert opt["nudges_created"] > 0

        # 3. Retrieve nudges for target household
        nudges = svc.nudges_for(target_id)
        if not nudges:
            for h in hh_list:
                nudges = svc.nudges_for(h["id"])
                if nudges:
                    target_id = h["id"]
                    break

        assert len(nudges) > 0
        target_nudge = nudges[0]
        assert target_nudge["household_id"] == target_id
        assert target_nudge["status"] == "pending"

        # 4. Resident accepts nudge
        res = svc.respond(target_nudge["id"], accept=True)
        assert res["status"] == "accepted"
        assert res["household_points"] > 0

        # 5. Check household points updated in DB
        hh_after = rows("SELECT points FROM households WHERE id = ?", (target_id,))[0]
        assert hh_after["points"] == res["household_points"]


def test_discom_workflow_end_to_end(temp_db):
    """Verify complete DISCOM workflow: forecasts -> KPIs -> DR event -> API verification."""
    build_and_populate_dataset(num_households=10, days=2, seed=42, db_path=temp_db)
    populate_demo_forecasts(db_path=temp_db)

    with patch("backend.db.DB_PATH", temp_db):
        init_db()
        # 1. Retrieve 96-slot forecast
        forecast_slots = svc.load_forecast("2026-10-01")
        assert len(forecast_slots) == 96

        # 2. Run scheduler
        opt = svc.run_optimize("2026-10-01")
        assert "peak_before_kw" in opt
        assert "peak_after_kw" in opt

        # 3. Retrieve KPIs
        kpis = svc.kpis("2026-10-01")
        assert kpis["total_households"] == 10
        assert "transformer_risk" in kpis
        assert kpis["transformer_risk"] in ["LOW", "MEDIUM", "HIGH"]

        # 4. Trigger demand-response event
        dr = svc.run_dr_event(start=72, end=84, target_kw=15.0, date="2026-10-01")
        assert "nudges_created" in dr
        assert "after" in dr
        assert len(dr["after"]) == 96

        # 5. Flex capacity check
        flex = svc.flex_capacity()
        assert len(flex) == 24


def test_scenarios_solar_and_demand_contrast(temp_db):
    """Verify that sunny, cloudy, and heatwave scenarios produce expected physical contrasts."""
    build_and_populate_dataset(num_households=5, days=2, seed=42, db_path=temp_db)

    sunny_df = build_forecast_for_date("2026-10-01", scenario="sunny", db_path=temp_db)
    cloudy_df = build_forecast_for_date("2026-10-02", scenario="cloudy", db_path=temp_db)
    heatwave_df = build_forecast_for_date("2026-10-03", scenario="heatwave", db_path=temp_db)

    # Sunny scenario should produce significantly higher peak solar than cloudy
    assert sunny_df["solar_kw"].max() > cloudy_df["solar_kw"].max() * 1.5

    # Heatwave scenario should have higher peak afternoon demand than cloudy
    assert heatwave_df["demand_kw"].max() >= cloudy_df["demand_kw"].max()
