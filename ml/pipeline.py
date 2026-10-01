"""
Forecast Pipeline Module for PowerPool.
Orchestrates demand forecasting, solar forecasting, gap computation, and stress flag assignment
for demo scenarios (sunny, cloudy, heatwave).
"""

import os
import sqlite3
import logging
import datetime
import pandas as pd
import numpy as np

from data.weather import get_weather_with_fallback
from ml.forecast_solar import forecast_solar
from ml.forecast_demand import train_demand_model, predict_demand, SeasonalBaselineModel, MODEL_PATH, LIGHTGBM_AVAILABLE
from ml.features import create_forecasting_features, prepare_feeder_demand_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "powerpool.db")
FEEDER_CAPACITY_KW = float(os.getenv("FEEDER_CAPACITY_KW", "170.0"))


def build_forecast_for_date(
    date_str: str,
    scenario: str = "sunny",
    db_path: str = DB_PATH,
    capacity_kw: float = FEEDER_CAPACITY_KW
) -> pd.DataFrame:
    """
    Builds next-24-hour forecast (96 slots of 15-minute intervals) for a specific date using trained LightGBM model.
    Calculates:
    - demand_kw (predicted feeder demand via LightGBM predict())
    - solar_kw (solar generation forecast)
    - capacity_kw (feeder capacity)
    - gap_kw = demand_kw - solar_kw - capacity_kw
    - is_stress = 1 if gap_kw > 0 else 0
    """
    target_dt = pd.to_datetime(date_str)
    start_ts = target_dt.strftime("%Y-%m-%d")
    
    # 96 slots for the target date
    timestamps = [target_dt + pd.Timedelta(minutes=15 * i) for i in range(96)]

    # Fetch weather for target date
    target_weather = get_weather_with_fallback(start_ts, days=1)
    
    # Apply scenario weather adjustments for target date weather if scenario specified
    w_df = target_weather.copy()
    if scenario == "heatwave":
        w_df["temp_c"] = w_df["temp_c"] + 5.0
    elif scenario == "cloudy":
        w_df["cloud_cover"] = np.maximum(w_df["cloud_cover"], 75.0)

    # Solar forecast for scenario using target weather
    solar_df = forecast_solar(w_df, scenario=scenario)
    solar_kw_values = solar_df["solar_kw"].values

    # Demand forecast calculation using predict_demand (LightGBM)
    conn = sqlite3.connect(db_path)
    df_load_history = pd.read_sql("SELECT household_id, timestamp, kwh FROM load_history", conn)
    hist_weather = pd.read_sql("SELECT timestamp, temp_c, cloud_cover, irradiance_wm2 FROM weather", conn)
    conn.close()

    # Combine historical weather with target date weather
    full_weather = pd.concat([hist_weather, w_df], ignore_index=True).drop_duplicates("timestamp")

    demand_res, model_source = predict_demand(df_load_history, full_weather, timestamps)
    logger.info(f"Built forecast for {date_str} ({scenario}) using model_source='{model_source}'.")
    demand_kw_values = demand_res["demand_kw"].values

    # Compute gap and stress flag
    records = []
    for i in range(96):
        d_kw = float(demand_kw_values[i])
        s_kw = float(solar_kw_values[i])
        gap = round(d_kw - s_kw - capacity_kw, 2)
        is_stress = 1 if gap > 0 else 0

        records.append({
            "timestamp": demand_res["timestamp"].iloc[i],
            "demand_kw": d_kw,
            "solar_kw": s_kw,
            "capacity_kw": capacity_kw,
            "gap_kw": gap,
            "is_stress": is_stress
        })

    df_forecast = pd.DataFrame(records)
    df_forecast.attrs["model_source"] = model_source
    return df_forecast


def populate_demo_forecasts(db_path: str = DB_PATH):
    """
    Populates SQLite database `forecast` table with the three required demo dates:
    - 2026-10-01: Sunny scenario
    - 2026-10-02: Cloudy scenario
    - 2026-10-03: Heatwave scenario
    Total rows = 3 x 96 = 288 rows.
    """
    demo_scenarios = [
        ("2026-10-01", "sunny"),
        ("2026-10-02", "cloudy"),
        ("2026-10-03", "heatwave")
    ]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Clear existing forecast table
    cursor.execute("DELETE FROM forecast")
    conn.commit()

    all_forecast_dfs = []

    for date_str, scenario in demo_scenarios:
        logger.info(f"Generating 96-slot forecast for {date_str} ({scenario} scenario)...")
        df_f = build_forecast_for_date(date_str, scenario=scenario, db_path=db_path)
        all_forecast_dfs.append(df_f)

        # Insert into forecast table
        cursor.executemany("""
        INSERT INTO forecast (timestamp, demand_kw, solar_kw, capacity_kw, gap_kw, is_stress)
        VALUES (:timestamp, :demand_kw, :solar_kw, :capacity_kw, :gap_kw, :is_stress)
        """, df_f.to_dict(orient="records"))

    conn.commit()
    conn.close()

    full_forecast_df = pd.concat(all_forecast_dfs, ignore_index=True)
    logger.info(f"Successfully populated {len(full_forecast_df)} forecast rows across 3 demo scenarios.")
    return full_forecast_df
