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


def load_demand_model():
    """
    Loads saved LightGBM model if available, otherwise returns SeasonalBaseline model.
    """
    if LIGHTGBM_AVAILABLE and os.path.exists(MODEL_PATH):
        try:
            model = lgb.Booster(model_file=MODEL_PATH)
            return model, "LightGBM"
        except Exception as e:
            logger.warning(f"Could not load LightGBM model file ({e}). Using baseline.")

    return SeasonalBaselineModel(), "SeasonalBaseline"
