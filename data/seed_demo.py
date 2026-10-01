"""
Seed script for PowerPool demo data and SQLite database.
Generates scenario JSON files and populates data/powerpool.db.
"""

import os
import json
import sqlite3
from typing import Dict, Any

from data.weather import get_weather_data
from data.generator import generate_households, generate_feeder_baseline

DB_PATH = os.path.join(os.path.dirname(__file__), "powerpool.db")
SCENARIO_DIR = os.path.join(os.path.dirname(__file__), "scenarios")


def init_db(db_path: str = DB_PATH):
    """
    Creates SQLite tables for households, appliances, nudges, and forecast slots.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS households (
        household_id INTEGER PRIMARY KEY,
        name TEXT,
        phase TEXT,
        has_solar INTEGER,
        solar_capacity_kw REAL,
        points INTEGER,
        kwh_shifted_total REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS appliances (
        appliance_id TEXT PRIMARY KEY,
        household_id INTEGER,
        name TEXT,
        power_kw REAL,
        duration_slots INTEGER,
        default_start_slot INTEGER,
        flex_window_start INTEGER,
        flex_window_end INTEGER,
        FOREIGN KEY(household_id) REFERENCES households(household_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS nudges (
        nudge_id INTEGER PRIMARY KEY AUTOINCREMENT,
        household_id INTEGER,
        appliance_name TEXT,
        from_time TEXT,
        to_time TEXT,
        kwh_shifted REAL,
        points INTEGER,
        saving_rs REAL,
        message TEXT,
        status TEXT,
        FOREIGN KEY(household_id) REFERENCES households(household_id)
    )
    """)

    conn.commit()
    conn.close()


def generate_scenario_json(scenario_name: str) -> Dict[str, Any]:
    """
    Generates a full scenario payload for a given scenario name.
    """
    households = generate_households(100, seed=42)
    weather_slots = get_weather_data(scenario=scenario_name)
    feeder_data = generate_feeder_baseline(households, weather_slots)
    
    payload = {
        "scenario": scenario_name,
        "date": "2026-10-01",
        "households": households,
        "weather": weather_slots,
        "forecast": feeder_data["slots"],
        "total_solar_cap_kw": feeder_data["total_solar_cap_kw"],
    }
    return payload


def seed_all():
    """
    Seeds database and generates pre-computed JSON files for scenarios.
    """
    os.makedirs(SCENARIO_DIR, exist_ok=True)
    init_db(DB_PATH)

    scenarios = ["sunny", "cloudy", "heatwave"]
    for sc in scenarios:
        data = generate_scenario_json(sc)
        filepath = os.path.join(SCENARIO_DIR, f"{sc}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Generated scenario artifact: {filepath}")

    # Seed default households into SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM households")
    cursor.execute("DELETE FROM appliances")
    
    default_data = generate_scenario_json("sunny")
    for h in default_data["households"]:
        cursor.execute(
            "INSERT INTO households VALUES (?, ?, ?, ?, ?, ?, ?)",
            (h["household_id"], h["name"], h["phase"], int(h["has_solar"]), h["solar_capacity_kw"], h["points"], h["kwh_shifted_total"])
        )
        for app in h["appliances"]:
            cursor.execute(
                "INSERT INTO appliances VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (app["appliance_id"], h["household_id"], app["name"], app["power_kw"], app["duration_slots"], app["default_start_slot"], app["flex_window_start"], app["flex_window_end"])
            )
            
    conn.commit()
    conn.close()
    print("SQLite database seeded successfully.")


if __name__ == "__main__":
    seed_all()
