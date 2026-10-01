"""
Demand Forecasting Module for PowerPool.
Trains LightGBM model (with Seasonal Baseline fallback) for next-24-hour 96-slot feeder demand prediction.
Saves model artifact and metadata.
"""

import os
import json
import logging
import pandas as pd
import numpy as np

from ml.features import create_forecasting_features, prepare_feeder_demand_data
from ml.metrics import evaluate_forecast

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "demand_model.txt")
METADATA_PATH = os.path.join(MODEL_DIR, "metadata.json")

# Safe import of LightGBM
try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    logger.warning("LightGBM not found. Using Seasonal Baseline model fallback.")


class SeasonalBaselineModel:
    """
    Fallback baseline model that predicts feeder demand based on historical
    slot (0-95) averages across recent days.
    """
    def __init__(self):
        self.slot_averages = {}
        self.overall_mean = 100.0

    def fit(self, X: pd.DataFrame, y: np.ndarray):
        df = X.copy()
        df["target"] = y
        self.slot_averages = df.groupby("slot")["target"].mean().to_dict()
        self.overall_mean = float(np.mean(y)) if len(y) > 0 else 100.0
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        preds = []
        for _, row in X.iterrows():
            slot = int(row.get("slot", 0))
            pred = self.slot_averages.get(slot, self.overall_mean)
            preds.append(float(pred))
        return np.array(preds)


def train_demand_model(df_load_history: pd.DataFrame, weather_df: pd.DataFrame, seed: int = 42):
    """
    Trains feeder demand forecasting model using LightGBM (or Seasonal Baseline fallback).
    Evaluates metrics (MAPE, MAE, RMSE) and saves model artifacts.
    """
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    feeder_df = prepare_feeder_demand_data(df_load_history)
    feature_df = create_forecasting_features(feeder_df, weather_df)

    feature_cols = [
        "slot", "hour", "minute", "day_of_week", "is_weekend",
        "temp_c", "cloud_cover", "lag_1", "lag_4", "lag_96", "lag_192",
        "rolling_mean_4", "rolling_mean_96"
    ]

    X = feature_df[feature_cols]
    y = feature_df["demand_kw"].values

    # Train/Test split (last 3 days for validation)
    split_idx = max(0, len(X) - (3 * 96))
    X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_val = y[:split_idx], y[split_idx:]

    model_type = "LightGBM"

    if LIGHTGBM_AVAILABLE:
        try:
            logger.info("Training LightGBM demand forecast model...")
            params = {
                "objective": "regression",
                "metric": "rmse",
                "boosting_type": "gbdt",
                "n_estimators": 150,
                "learning_rate": 0.05,
                "num_leaves": 31,
                "random_state": seed,
                "verbose": -1
            }
            model = lgb.LGBMRegressor(**params)
            model.fit(X_train, y_train)

            # Evaluate on validation set
            val_preds = model.predict(X_val)
            metrics = evaluate_forecast(y_val, val_preds)

            # Save model text file
            model.booster_.save_model(MODEL_PATH)
            logger.info(f"Saved LightGBM model to {MODEL_PATH}")

        except Exception as e:
            logger.warning(f"LightGBM training failed ({e}). Falling back to Seasonal Baseline.")
            model = SeasonalBaselineModel()
            model.fit(X_train, y_train)
            val_preds = model.predict(X_val)
            metrics = evaluate_forecast(y_val, val_preds)
            model_type = "SeasonalBaseline"
    else:
        model = SeasonalBaselineModel()
        model.fit(X_train, y_train)
        val_preds = model.predict(X_val)
        metrics = evaluate_forecast(y_val, val_preds)
        model_type = "SeasonalBaseline"

    logger.info(f"Model ({model_type}) Validation Metrics: MAPE={metrics['mape']}%, MAE={metrics['mae']} kW, RMSE={metrics['rmse']} kW")

    # Save Metadata JSON
    metadata = {
        "model_type": model_type,
        "features": feature_cols,
        "training_start": str(feature_df["timestamp"].min()),
        "training_end": str(feature_df["timestamp"].max()),
        "mape": metrics["mape"],
        "mae": metrics["mae"],
        "rmse": metrics["rmse"],
        "random_seed": seed
    }

    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    return model, metadata


def load_demand_model(model_path: str = MODEL_PATH):
    """
    Loads saved LightGBM model if available, otherwise returns SeasonalBaseline model.
    Returns tuple of (model, model_source).
    """
    if LIGHTGBM_AVAILABLE and os.path.exists(model_path):
        try:
            model = lgb.Booster(model_file=model_path)
            return model, "lightgbm"
        except Exception as e:
            logger.warning(f"Could not load LightGBM model file ({e}). Using baseline.")

    return SeasonalBaselineModel(), "seasonal_baseline"


def predict_demand(
    df_load_history: pd.DataFrame,
    weather_df: pd.DataFrame,
    target_timestamps: list,
    model_path: str = MODEL_PATH
) -> tuple[pd.DataFrame, str]:
    """
    Production demand inference using trained LightGBM model (or Seasonal Baseline fallback).
    
    Inputs:
    - df_load_history: pd.DataFrame with historical load data (household_id, timestamp, kwh)
    - weather_df: pd.DataFrame with weather data (timestamp, temp_c, cloud_cover) covering history and target
    - target_timestamps: list/DatetimeIndex of target forecast timestamps (e.g. 96 slots)
    - model_path: path to trained LightGBM model artifact (ml/models/demand_model.txt)
    
    Returns:
    - tuple of:
        1. demand_df: pd.DataFrame with columns ['timestamp', 'demand_kw']
        2. model_source: str ("lightgbm" or "seasonal_baseline")
    """
    model, model_source = load_demand_model(model_path)
    
    target_ts_objs = [pd.to_datetime(ts) for ts in target_timestamps]
    
    if df_load_history is None or len(df_load_history) == 0:
        logger.warning("Empty load history provided. Falling back to baseline demand prediction.")
        model_source = "seasonal_baseline"
        fallback = SeasonalBaselineModel()
        dummy_df = pd.DataFrame({"slot": [(ts.hour * 4 + ts.minute // 15) for ts in target_ts_objs]})
        preds = fallback.predict(dummy_df)
        res_df = pd.DataFrame({
            "timestamp": [ts.strftime("%Y-%m-%dT%H:%M:%S") for ts in target_ts_objs],
            "demand_kw": np.round(preds, 2)
        })
        return res_df, model_source

    feeder_df = prepare_feeder_demand_data(df_load_history)
    
    feature_cols = [
        "slot", "hour", "minute", "day_of_week", "is_weekend",
        "temp_c", "cloud_cover", "lag_1", "lag_4", "lag_96", "lag_192",
        "rolling_mean_4", "rolling_mean_96"
    ]

    current_feeder = feeder_df.copy()
    full_weather = weather_df.copy()
    full_weather["timestamp"] = pd.to_datetime(full_weather["timestamp"])
    full_weather["temp_c"] = pd.to_numeric(full_weather["temp_c"], errors="coerce")
    full_weather["cloud_cover"] = pd.to_numeric(full_weather["cloud_cover"], errors="coerce")

    predicted_records = []
    
    # If seasonal baseline fallback is active, fit on load history
    if model_source != "lightgbm":
        if not isinstance(model, SeasonalBaselineModel):
            model = SeasonalBaselineModel()
        feat_hist = create_forecasting_features(feeder_df, full_weather)
        model.fit(feat_hist, feat_hist["demand_kw"].values)

    for ts in target_ts_objs:
        ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
        
        if model_source == "lightgbm":
            recent_feeder = current_feeder.tail(250).copy()
            new_row = pd.DataFrame([{"timestamp": ts, "feeder_kwh": 0.0, "demand_kw": 0.0}])
            temp_feeder = pd.concat([recent_feeder, new_row], ignore_index=True)
            
            feat_df = create_forecasting_features(temp_feeder, full_weather)
            target_feat = feat_df[feat_df["timestamp"] == ts][feature_cols].copy()
            
            for col in feature_cols:
                target_feat[col] = pd.to_numeric(target_feat[col], errors="coerce").astype(float)

            if len(target_feat) == 0:
                logger.warning(f"Could not construct features for {ts_str}, fallback to baseline mean.")
                pred = float(current_feeder["demand_kw"].tail(96).mean() if len(current_feeder) > 0 else 100.0)
            else:
                try:
                    pred = float(model.predict(target_feat)[0])
                except Exception as e:
                    logger.error(f"LightGBM predict() failed at {ts_str}: {e}")
                    model_source = "seasonal_baseline"
                    fallback_model = SeasonalBaselineModel()
                    feat_hist = create_forecasting_features(feeder_df, full_weather)
                    fallback_model.fit(feat_hist, feat_hist["demand_kw"].values)
                    model = fallback_model
                    slot = (ts.hour * 4) + (ts.minute // 15)
                    pred = float(model.predict(pd.DataFrame([{"slot": slot}]))[0])
        else:
            slot = (ts.hour * 4) + (ts.minute // 15)
            single_row = pd.DataFrame([{"slot": slot}])
            pred = float(model.predict(single_row)[0])
            
        pred_kw = round(max(0.0, pred), 2)
        predicted_records.append({
            "timestamp": ts_str,
            "demand_kw": pred_kw
        })
        
        current_feeder = pd.concat([
            current_feeder,
            pd.DataFrame([{"timestamp": ts, "feeder_kwh": pred_kw * 0.25, "demand_kw": pred_kw}])
        ], ignore_index=True)

    res_df = pd.DataFrame(predicted_records)
    logger.info(f"Demand forecasting completed using model_source='{model_source}' for {len(res_df)} slots.")
    return res_df, model_source

