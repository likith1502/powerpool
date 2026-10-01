"""
Feature Engineering for Feeder Demand Forecasting.
Aggregates 15-minute household load history into total feeder demand (kW)
and constructs time/calendar, weather, lag, and rolling features.
"""

import pandas as pd
import numpy as np

def prepare_feeder_demand_data(df_load_history: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates household load kWh per 15-minute slot into total feeder power demand in kW.
    Slot power (kW) = Total Slot Energy (kWh) / 0.25 hours.
    """
    df = df_load_history.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Sum kWh across all households for each timestamp
    feeder_df = df.groupby("timestamp")["kwh"].sum().reset_index()
    feeder_df.rename(columns={"kwh": "feeder_kwh"}, inplace=True)

    # Convert kWh to kW (15 minutes = 0.25 hours)
    feeder_df["demand_kw"] = (feeder_df["feeder_kwh"] / 0.25).round(2)
    feeder_df.sort_values("timestamp", inplace=True)
    return feeder_df


def create_forecasting_features(feeder_df: pd.DataFrame, weather_df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates feature set for model training & prediction.
    Features:
    - Time/Calendar: hour, minute, slot (0-95), day_of_week, is_weekend
    - Weather: temp_c, cloud_cover
    - Lags: lag_1 (15m), lag_4 (1h), lag_96 (24h / 1 day), lag_192 (48h / 2 days)
    - Rolling stats: rolling_mean_4, rolling_mean_96
    """
    df = feeder_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    weather = weather_df.copy()
    weather["timestamp"] = pd.to_datetime(weather["timestamp"])

    # Merge with weather data on timestamp
    df = pd.merge(df, weather[["timestamp", "temp_c", "cloud_cover"]], on="timestamp", how="left")
    df["temp_c"] = df["temp_c"].ffill().bfill()
    df["cloud_cover"] = df["cloud_cover"].ffill().bfill()

    # Time / Calendar features
    df["hour"] = df["timestamp"].dt.hour
    df["minute"] = df["timestamp"].dt.minute
    df["slot"] = (df["hour"] * 4) + (df["minute"] // 15)
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

    # Lag features on demand_kw
    df["lag_1"] = df["demand_kw"].shift(1)
    df["lag_4"] = df["demand_kw"].shift(4)
    df["lag_96"] = df["demand_kw"].shift(96)
    df["lag_192"] = df["demand_kw"].shift(192)

    # Rolling window features
    df["rolling_mean_4"] = df["demand_kw"].shift(1).rolling(window=4, min_periods=1).mean()
    df["rolling_mean_96"] = df["demand_kw"].shift(1).rolling(window=96, min_periods=1).mean()

    # Backfill missing lags for initial slots
    lag_cols = ["lag_1", "lag_4", "lag_96", "lag_192", "rolling_mean_4", "rolling_mean_96"]
    for col in lag_cols:
        df[col] = df[col].bfill().fillna(df["demand_kw"])

    return df
