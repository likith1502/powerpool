"""
Metrics module for forecast evaluation.
Calculates MAPE (with epsilon protection against zero division), MAE, and RMSE.
"""

import numpy as np

def calculate_mape(y_true: np.ndarray, y_pred: np.ndarray, epsilon: float = 1e-6) -> float:
    """
    Calculate Mean Absolute Percentage Error (MAPE).
    Handles zero/near-zero actual values using epsilon protection.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    
    # Avoid zero division
    denominator = np.where(np.abs(y_true) < epsilon, epsilon, np.abs(y_true))
    absolute_percentage_error = np.abs((y_true - y_pred) / denominator)
    return float(np.mean(absolute_percentage_error) * 100.0)


def calculate_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculate Mean Absolute Error (MAE).
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_true - y_pred)))


def calculate_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculate Root Mean Squared Error (RMSE).
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def evaluate_forecast(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    Computes all standard forecast evaluation metrics.
    """
    return {
        "mape": round(calculate_mape(y_true, y_pred), 2),
        "mae": round(calculate_mae(y_true, y_pred), 2),
        "rmse": round(calculate_rmse(y_true, y_pred), 2)
    }
