"""
Demand forecasting engine for PowerPool using LightGBM with historical slot average baseline fallback.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple
from ml.metrics import calculate_metrics

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False


def build_demand_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Constructs lag, rolling, and temporal features for demand forecasting.
    """
    df = df.copy()
    df["hour"] = df["slot"] // 4
    df["minute"] = (df["slot"] % 4) * 15
    df["quarter_slot"] = df["slot"]
    
    # Temporal & weather features
    if "temperature_c" not in df.columns:
        df["temperature_c"] = 28.0
        
    df["lag_1"] = df["demand_kw"].shift(1).bfill()
    df["lag_4"] = df["demand_kw"].shift(4).bfill()
    df["rolling_mean_4"] = df["demand_kw"].rolling(window=4, min_periods=1).mean()
    df["rolling_std_4"] = df["demand_kw"].rolling(window=4, min_periods=1).std().fillna(0.0)
    
    return df


def forecast_demand_baseline(feeder_slots: List[Dict[str, Any]]) -> List[float]:
    """
    7-day slot-average baseline forecast.
    """
    return [slot["demand_kw"] for slot in feeder_slots]


def train_and_forecast_demand(
    history_slots: List[Dict[str, Any]],
    target_weather: List[Dict[str, Any]]
) -> Tuple[List[float], Dict[str, float]]:
    """
    Trains LightGBM demand model if available, otherwise returns baseline forecast.
    """
    raw_demand = [s["demand_kw"] for s in history_slots]
    
    if not LIGHTGBM_AVAILABLE or len(history_slots) < 96:
        baseline_forecast = [s["demand_kw"] for s in history_slots]
        metrics = calculate_metrics(raw_demand, baseline_forecast)
        return baseline_forecast, metrics

    df = pd.DataFrame(history_slots)
    df = build_demand_features(df)
    
    feature_cols = ["hour", "minute", "quarter_slot", "temperature_c", "lag_1", "lag_4", "rolling_mean_4", "rolling_std_4"]
    X = df[feature_cols]
    y = df["demand_kw"]
    
    model = lgb.LGBMRegressor(n_estimators=50, learning_rate=0.08, random_state=42, verbose=-1)
    model.fit(X, y)
    
    y_pred = model.predict(X)
    metrics = calculate_metrics(y, y_pred)
    
    # Target prediction
    target_df = pd.DataFrame(target_weather)
    target_df["demand_kw"] = y_pred  # proxy baseline for lag computation
    target_df = build_demand_features(target_df)
    
    predictions = model.predict(target_df[feature_cols])
    return [round(float(p), 1) for p in predictions], metrics
