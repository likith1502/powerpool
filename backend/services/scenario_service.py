"""
Scenario loader service for PowerPool.
"""

import os
import json
import sqlite3
from typing import Dict, Any

SCENARIO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "scenarios")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "powerpool.db")


def load_scenario_data(scenario_name: str = "sunny") -> Dict[str, Any]:
    """
    Loads JSON scenario dataset from data/scenarios/{scenario}.json.
    """
    filepath = os.path.join(SCENARIO_DIR, f"{scenario_name.lower()}.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
            
    # Fallback to sunny
    fallback_path = os.path.join(SCENARIO_DIR, "sunny.json")
    if os.path.exists(fallback_path):
        with open(fallback_path, "r", encoding="utf-8") as f:
            return json.load(f)
            
    raise FileNotFoundError(f"Scenario files not found in {SCENARIO_DIR}")
