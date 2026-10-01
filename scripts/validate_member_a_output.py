"""
Validation Script for Member A Implementation.
Verifies database integrity, household count, appliance types, load resolution,
forecast slot count (96/day), gap formula, stress detection, peak demand > 170 kW, and MAPE metrics.
"""

import os
import sys
import json
import sqlite3
import logging
import pandas as pd
import numpy as np

# Ensure root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.generator import DB_PATH, REQUIRED_FLEXIBLE_APPLIANCES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("validate_member_a")

def validate():
    logger.info("=== Starting Member A Validation Suite ===")

    # 1. Database File Check
    if not os.path.exists(DB_PATH):
        raise AssertionError(f"FAIL: Database file does not exist at {DB_PATH}")
    logger.info("✔ Database file exists.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 2. Required Tables Check
    required_tables = {"households", "appliances", "load_history", "weather", "forecast", "nudges"}
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    existing_tables = {row[0] for row in cursor.fetchall()}

    missing_tables = required_tables - existing_tables
    if missing_tables:
        raise AssertionError(f"FAIL: Missing required tables: {missing_tables}")
    logger.info("✔ All required database tables exist.")

    # 3. Households Validation
    df_hh = pd.read_sql("SELECT * FROM households", conn)
    hh_count = len(df_hh)
    if not (60 <= hh_count <= 100):
        raise AssertionError(f"FAIL: Household count ({hh_count}) must be between 60 and 100.")

    valid_types = {"low", "mid", "shop"}
    if not set(df_hh["type"]).issubset(valid_types):
        raise AssertionError(f"FAIL: Invalid household type found: {set(df_hh['type']) - valid_types}")

    valid_langs = {"en", "hi", "te"}
    if not set(df_hh["language"]).issubset(valid_langs):
        raise AssertionError(f"FAIL: Invalid language found: {set(df_hh['language']) - valid_langs}")

    if (df_hh["points"] < 0).any():
        raise AssertionError("FAIL: Household points must be non-negative.")
    logger.info(f"✔ Households valid ({hh_count} households, correct types/languages).")

    # 4. Appliances Validation
    df_app = pd.read_sql("SELECT * FROM appliances", conn)
    if df_app.empty:
        raise AssertionError("FAIL: Appliances table is empty.")

    if not set(df_app["household_id"]).issubset(set(df_hh["id"])):
        raise AssertionError("FAIL: Orphan household_id in appliances table.")

    if (df_app["earliest_slot"] < 0).any() or (df_app["earliest_slot"] > 95).any():
        raise AssertionError("FAIL: Appliance earliest_slot out of 0-95 range.")

    if (df_app["latest_slot"] < 0).any() or (df_app["latest_slot"] > 95).any():
        raise AssertionError("FAIL: Appliance latest_slot out of 0-95 range.")

    if (df_app["usual_slot"] < 0).any() or (df_app["usual_slot"] > 95).any():
        raise AssertionError("FAIL: Appliance usual_slot out of 0-95 range.")

    existing_app_names = set(df_app["name"])
    for req_app in REQUIRED_FLEXIBLE_APPLIANCES:
        if req_app not in existing_app_names:
            raise AssertionError(f"FAIL: Required flexible appliance '{req_app}' missing from appliances table.")
    logger.info(f"✔ Appliances valid (all 6 required flexible appliance types present).")

    # 5. Load History Validation
    df_load = pd.read_sql("SELECT * FROM load_history", conn)
    if df_load.empty:
        raise AssertionError("FAIL: Load history table is empty.")

    if (df_load["kwh"] < 0).any():
        raise AssertionError("FAIL: Negative kWh values found in load_history.")

    if df_load["kwh"].isna().any():
        raise AssertionError("FAIL: NaN values found in load_history.")
    logger.info(f"✔ Load history valid ({len(df_load)} rows, no negative/NaN values).")

    # 6. Weather Validation
    df_weather = pd.read_sql("SELECT * FROM weather", conn)
    if df_weather.empty:
        raise AssertionError("FAIL: Weather table is empty.")

    if (df_weather["irradiance_wm2"] < 0).any():
        raise AssertionError("FAIL: Negative irradiance found in weather table.")

    if df_weather[["temp_c", "cloud_cover", "irradiance_wm2"]].isna().any().any():
        raise AssertionError("FAIL: NaN values found in weather table.")
    logger.info(f"✔ Weather valid ({len(df_weather)} rows).")

    # 7. Forecast Validation
    df_forecast = pd.read_sql("SELECT * FROM forecast", conn)
    if len(df_forecast) != 288: # 3 dates x 96 slots
        raise AssertionError(f"FAIL: Forecast table row count ({len(df_forecast)}) must be exactly 288 (3 x 96 slots).")

    # Gap formula verification: gap_kw == demand_kw - solar_kw - capacity_kw
    expected_gap = (df_forecast["demand_kw"] - df_forecast["solar_kw"] - df_forecast["capacity_kw"]).round(2)
    gap_diff = (df_forecast["gap_kw"] - expected_gap).abs().max()
    if gap_diff > 0.05:
        raise AssertionError(f"FAIL: gap_kw formula mismatch (max diff={gap_diff})")

    # Stress flag verification: is_stress == (1 if gap_kw > 0 else 0)
    expected_stress = (df_forecast["gap_kw"] > 0).astype(int)
    if not (df_forecast["is_stress"] == expected_stress).all():
        raise AssertionError("FAIL: is_stress flag mismatch with gap_kw > 0")

    # Peak demand check > 170 kW
    max_demand = df_forecast["demand_kw"].max()
    if max_demand <= 170.0:
        raise AssertionError(f"FAIL: Max demand ({max_demand:.2f} kW) must exceed 170 kW for meaningful optimization demo.")
    logger.info(f"✔ Forecast table valid (288 slots, exact gap formula verified, peak demand={max_demand:.2f} kW > 170 kW).")

    # 8. Model Metadata Check
    metadata_file = os.path.join(os.path.dirname(__file__), "..", "ml", "models", "metadata.json")
    if not os.path.exists(metadata_file):
        raise AssertionError(f"FAIL: Metadata file missing at {metadata_file}")

    with open(metadata_file, "r") as f:
        meta = json.load(f)

    mape = meta.get("mape", None)
    if mape is None or not isinstance(mape, (int, float)):
        raise AssertionError("FAIL: Valid numeric MAPE metric missing from metadata.json")
    logger.info(f"✔ Model metadata valid (Model={meta.get('model_type')}, MAPE={mape}%).")

    conn.close()
    logger.info("=== ALL MEMBER A VALIDATION CHECKS PASSED SUCCESSFULLY ===")
    return True

if __name__ == "__main__":
    validate()
