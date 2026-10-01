"""
Evaluation metrics for PowerPool ML forecasting models.
"""

import numpy as np
from typing import Dict


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Computes MAE, RMSE, and MAPE.
    """
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)
    
    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    
    # Avoid division by zero in MAPE
    mask = y_true > 1.0
    if np.sum(mask) > 0:
        mape = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)
    else:
        mape = 0.0
        
    return {
        "MAE": round(mae, 2),
        "RMSE": round(rmse, 2),
        "MAPE": round(mape, 2),
    }
