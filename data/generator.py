"""
Synthetic Data Generator for PowerPool.
Generates households, appliances, and 30-day 15-minute load history into SQLite database data/powerpool.db.
Also exports data/sample_load.csv for Member B integration.
"""

import os
import sqlite3
import datetime
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "powerpool.db")
SAMPLE_CSV_PATH = os.path.join(os.path.dirname(__file__), "sample_load.csv")

# Required flexible appliance names matching Member B translation dictionary
REQUIRED_FLEXIBLE_APPLIANCES = [
    "Washing machine",
    "Water pump",
    "Inverter charging",
    "Geyser",
    "Iron",
    "E-rickshaw charging"
]

def init_db(db_path: str = DB_PATH):
    """
    Creates SQLite database tables and indexes if they do not exist.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS households (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT CHECK(type IN ('low', 'mid', 'shop')),
        block TEXT NOT NULL,
        language TEXT CHECK(language IN ('en', 'hi', 'te')),
        points INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS appliances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        household_id TEXT NOT NULL,
        name TEXT NOT NULL,
        power_kw REAL NOT NULL CHECK(power_kw > 0),
        duration_slots INTEGER NOT NULL CHECK(duration_slots > 0),
        flexible INTEGER NOT NULL CHECK(flexible IN (0, 1)),
        earliest_slot INTEGER NOT NULL CHECK(earliest_slot BETWEEN 0 AND 95),
        latest_slot INTEGER NOT NULL CHECK(latest_slot BETWEEN 0 AND 95),
        usual_slot INTEGER NOT NULL CHECK(usual_slot BETWEEN 0 AND 95),
        FOREIGN KEY (household_id) REFERENCES households(id)
    );

    CREATE TABLE IF NOT EXISTS load_history (
        household_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        kwh REAL NOT NULL CHECK(kwh >= 0),
        PRIMARY KEY (household_id, timestamp),
        FOREIGN KEY (household_id) REFERENCES households(id)
    );

    CREATE TABLE IF NOT EXISTS weather (
        timestamp TEXT PRIMARY KEY,
        temp_c REAL NOT NULL,
        cloud_cover REAL NOT NULL,
        irradiance_wm2 REAL NOT NULL CHECK(irradiance_wm2 >= 0)
    );

    CREATE TABLE IF NOT EXISTS forecast (
        timestamp TEXT PRIMARY KEY,
        demand_kw REAL NOT NULL CHECK(demand_kw >= 0),
        solar_kw REAL NOT NULL CHECK(solar_kw >= 0),
        capacity_kw REAL NOT NULL CHECK(capacity_kw > 0),
        gap_kw REAL NOT NULL,
        is_stress INTEGER NOT NULL CHECK(is_stress IN (0, 1))
    );

    CREATE TABLE IF NOT EXISTS nudges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        household_id TEXT NOT NULL,
        appliance_id INTEGER NOT NULL,
        from_slot INTEGER NOT NULL,
        to_slot INTEGER NOT NULL,
        kwh_shifted REAL NOT NULL,
        points INTEGER NOT NULL,
        saving_rs REAL NOT NULL,
        status TEXT CHECK(status IN ('pending', 'accepted', 'skipped')),
        FOREIGN KEY (household_id) REFERENCES households(id),
        FOREIGN KEY (appliance_id) REFERENCES appliances(id)
    );

    CREATE INDEX IF NOT EXISTS idx_load_history_timestamp ON load_history(timestamp);
    CREATE INDEX IF NOT EXISTS idx_load_history_household ON load_history(household_id);
    CREATE INDEX IF NOT EXISTS idx_appliances_household ON appliances(household_id);
    CREATE INDEX IF NOT EXISTS idx_forecast_timestamp ON forecast(timestamp);
    """)

    conn.commit()
    conn.close()
    logger.info(f"Database schema initialized at {db_path}")


def generate_households_and_appliances(num_households: int = 100, seed: int = 42):
    """
    Generates deterministic household profiles and appliance catalogs.
    Distribution: low (35%), mid (50%), shop (15%).
    Languages: en (40%), hi (30%), te (30%).
    Blocks: Block A, Block B, Block C, Block D.
    """
    rng = np.random.default_rng(seed)

    types = ["low", "mid", "shop"]
    type_probs = [0.35, 0.50, 0.15]
    
    languages = ["en", "hi", "te"]
    lang_probs = [0.40, 0.30, 0.30]

    blocks = ["Block A", "Block B", "Block C", "Block D"]

    households = []
    appliances = []

    # Keep track to ensure all required flexible appliances are distributed across households
    flex_app_queue = REQUIRED_FLEXIBLE_APPLIANCES.copy()

    for i in range(1, num_households + 1):
        hh_id = f"HH{i:03d}"
        hh_type = rng.choice(types, p=type_probs)
        hh_lang = rng.choice(languages, p=lang_probs)
        hh_block = rng.choice(blocks)
        hh_name = f"{hh_type.capitalize()} Household {i}" if hh_type != "shop" else f"Shop {i}"

        households.append({
            "id": hh_id,
            "name": hh_name,
            "type": hh_type,
            "block": hh_block,
            "language": hh_lang,
            "points": 0
        })

        # Generate Base Non-Flexible Appliances
        if hh_type == "low":
            base_apps = [
                {"name": "LED lights", "power_kw": 0.10, "duration_slots": 20, "flexible": 0, "earliest": 0, "latest": 95, "usual": 76},
                {"name": "Fan", "power_kw": 0.15, "duration_slots": 32, "flexible": 0, "earliest": 0, "latest": 95, "usual": 50},
                {"name": "TV", "power_kw": 0.12, "duration_slots": 12, "flexible": 0, "earliest": 70, "latest": 92, "usual": 78},
                {"name": "Refrigerator", "power_kw": 0.20, "duration_slots": 96, "flexible": 0, "earliest": 0, "latest": 95, "usual": 0},
            ]
        elif hh_type == "mid":
            base_apps = [
                {"name": "LED lights", "power_kw": 0.20, "duration_slots": 20, "flexible": 0, "earliest": 0, "latest": 95, "usual": 76},
                {"name": "Fans", "power_kw": 0.30, "duration_slots": 36, "flexible": 0, "earliest": 0, "latest": 95, "usual": 50},
                {"name": "TV", "power_kw": 0.18, "duration_slots": 16, "flexible": 0, "earliest": 68, "latest": 92, "usual": 76},
                {"name": "Refrigerator", "power_kw": 0.30, "duration_slots": 96, "flexible": 0, "earliest": 0, "latest": 95, "usual": 0},
                {"name": "Air Conditioner", "power_kw": 1.50, "duration_slots": 24, "flexible": 0, "earliest": 56, "latest": 92, "usual": 78},
            ]
        else: # shop
            base_apps = [
                {"name": "Commercial Lighting", "power_kw": 0.40, "duration_slots": 48, "flexible": 0, "earliest": 36, "latest": 84, "usual": 40},
                {"name": "Fans", "power_kw": 0.25, "duration_slots": 48, "flexible": 0, "earliest": 36, "latest": 84, "usual": 40},
                {"name": "Commercial Refrigerator", "power_kw": 0.60, "duration_slots": 96, "flexible": 0, "earliest": 0, "latest": 95, "usual": 0},
                {"name": "Display & POS", "power_kw": 0.30, "duration_slots": 48, "flexible": 0, "earliest": 36, "latest": 84, "usual": 40},
            ]

        # Add flexible appliances
        hh_flex_apps = []

        # If queue not empty, assign next required flexible appliance
        if flex_app_queue:
            app_name = flex_app_queue.pop(0)
            hh_flex_apps.append(app_name)

        # Randomly sample additional flexible appliances for realistic diversity
        possible_flex = [
            "Washing machine", "Water pump", "Inverter charging", "Geyser", "Iron", "E-rickshaw charging"
        ]
        num_additional = rng.integers(1, 3)
        for _ in range(num_additional):
            cand = rng.choice(possible_flex)
            if cand not in hh_flex_apps:
                hh_flex_apps.append(cand)

        for flex_name in hh_flex_apps:
            if flex_name == "Washing machine":
                app_dict = {"name": flex_name, "power_kw": 1.40, "duration_slots": 4, "flexible": 1, "earliest": 36, "latest": 88, "usual": 74}
            elif flex_name == "Water pump":
                app_dict = {"name": flex_name, "power_kw": 1.10, "duration_slots": 3, "flexible": 1, "earliest": 24, "latest": 84, "usual": 72}
            elif flex_name == "Inverter charging":
                app_dict = {"name": flex_name, "power_kw": 0.75, "duration_slots": 8, "flexible": 1, "earliest": 36, "latest": 92, "usual": 76}
            elif flex_name == "Geyser":
                app_dict = {"name": flex_name, "power_kw": 2.00, "duration_slots": 2, "flexible": 1, "earliest": 24, "latest": 84, "usual": 76}
            elif flex_name == "Iron":
                app_dict = {"name": flex_name, "power_kw": 1.00, "duration_slots": 2, "flexible": 1, "earliest": 32, "latest": 84, "usual": 74}
            else: # E-rickshaw charging
                app_dict = {"name": flex_name, "power_kw": 1.60, "duration_slots": 12, "flexible": 1, "earliest": 40, "latest": 95, "usual": 78}

            base_apps.append(app_dict)

        for app in base_apps:
            appliances.append({
                "household_id": hh_id,
                "name": app["name"],
                "power_kw": app["power_kw"],
                "duration_slots": app["duration_slots"],
                "flexible": app["flexible"],
                "earliest_slot": app["earliest"],
                "latest_slot": app["latest"],
                "usual_slot": app["usual"]
            })

    # Ensure any remaining required flexible appliances in queue are added to remaining households
    while flex_app_queue:
        req_name = flex_app_queue.pop(0)
        target_hh = households[rng.integers(0, num_households)]["id"]
        appliances.append({
            "household_id": target_hh,
            "name": req_name,
            "power_kw": 1.20,
            "duration_slots": 4,
            "flexible": 1,
            "earliest_slot": 36,
            "latest_slot": 88,
            "usual_slot": 74
        })

    return households, appliances


def generate_load_history(households: list, appliances: list, start_date: str = "2026-09-01", days: int = 30, seed: int = 42) -> pd.DataFrame:
    """
    Generates 15-minute load history for every household for 30 days (30 x 96 = 2880 slots).
    Ensures realistic diurnal pattern:
    - Morning peak (06:00-09:00, slots 24-36)
    - Midday moderate load (10:00-16:00, slots 40-64)
    - Evening stress peak (18:30-22:00, slots 74-88)
    Aggregate feeder load peak exceeds 170 kW.
    """
    rng = np.random.default_rng(seed)
    start_dt = pd.to_datetime(start_date)
    total_slots = days * 96
    timestamps = [start_dt + pd.Timedelta(minutes=15 * i) for i in range(total_slots)]

    hh_apps_map = {}
    for app in appliances:
        hh_id = app["household_id"]
        if hh_id not in hh_apps_map:
            hh_apps_map[hh_id] = []
        hh_apps_map[hh_id].append(app)

    records = []

    for d in range(days):
        day_date = start_dt + pd.Timedelta(days=d)
        is_weekend = day_date.weekday() >= 5
        day_noise = rng.uniform(0.92, 1.08)

        for slot in range(96):
            ts_str = (day_date + pd.Timedelta(minutes=15 * slot)).strftime("%Y-%m-%dT%H:%M:%S")

            for hh in households:
                hh_id = hh["id"]
                hh_type = hh["type"]
                apps = hh_apps_map.get(hh_id, [])

                slot_kw = 0.0

                for app in apps:
                    power = app["power_kw"]
                    usual = app["usual_slot"]
                    dur = app["duration_slots"]
                    is_flex = app["flexible"]

                    if app["name"] in ["Refrigerator", "Commercial Refrigerator"]:
                        # Continuous duty cycle ~35-50%
                        if rng.random() < 0.45:
                            slot_kw += power * rng.uniform(0.8, 1.0)
                    elif app["name"] in ["LED lights", "Commercial Lighting"]:
                        if 72 <= slot <= 94 or 24 <= slot <= 32: # evening / early morning
                            slot_kw += power * rng.uniform(0.85, 1.0)
                    elif app["name"] in ["Fan", "Fans"]:
                        if 0 <= slot <= 95:
                            slot_kw += power * rng.uniform(0.6, 0.95)
                    elif app["name"] == "Air Conditioner":
                        if 56 <= slot <= 92: # afternoon through night
                            slot_kw += power * rng.uniform(0.7, 1.0)
                    else:
                        # Event-based appliances (Washing machine, Geyser, Water pump, Inverter, Iron, E-rickshaw, TV, Display)
                        if usual <= slot < usual + dur:
                            slot_kw += power * rng.uniform(0.85, 1.05)
                        elif is_flex and (usual - 2 <= slot < usual + dur + 2) and rng.random() < 0.15:
                            # slight jitter in usual time across days
                            slot_kw += power * rng.uniform(0.8, 1.0)

                # Add baseline household consumption noise
                baseline = 0.05 if hh_type == "low" else (0.12 if hh_type == "mid" else 0.20)
                total_hh_kw = (slot_kw + baseline) * day_noise * rng.uniform(0.95, 1.05)

                # Extra evening boost to guarantee total feeder peak > 170 kW
                if 74 <= slot <= 88: # 18:30 to 22:00
                    total_hh_kw *= 1.35

                # 15-minute slot energy in kWh: kWh = kW * 0.25 hours
                kwh = max(0.0, total_hh_kw * 0.25)

                records.append({
                    "household_id": hh_id,
                    "timestamp": ts_str,
                    "kwh": round(kwh, 4)
                })

    df_load = pd.DataFrame(records)
    return df_load


def build_and_populate_dataset(num_households: int = 100, days: int = 30, seed: int = 42, db_path: str = DB_PATH):
    """
    Main builder to initialize database, populate households, appliances, load_history,
    and save sample_load.csv.
    """
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Clear existing data if any
    cursor.executescript("""
    DELETE FROM load_history;
    DELETE FROM appliances;
    DELETE FROM households;
    """)
    conn.commit()

    logger.info(f"Generating {num_households} households & appliance profiles (seed={seed})...")
    households, appliances = generate_households_and_appliances(num_households, seed)

    # Insert Households
    cursor.executemany("""
    INSERT INTO households (id, name, type, block, language, points)
    VALUES (:id, :name, :type, :block, :language, :points)
    """, households)

    # Insert Appliances
    cursor.executemany("""
    INSERT INTO appliances (household_id, name, power_kw, duration_slots, flexible, earliest_slot, latest_slot, usual_slot)
    VALUES (:household_id, :name, :power_kw, :duration_slots, :flexible, :earliest_slot, :latest_slot, :usual_slot)
    """, appliances)

    conn.commit()
    logger.info("Households and appliances successfully inserted.")

    logger.info(f"Generating {days}-day load history (15-min resolution)...")
    df_load = generate_load_history(households, appliances, start_date="2026-09-01", days=days, seed=seed)

    # Insert Load History
    df_load.to_sql("load_history", conn, if_exists="append", index=False)
    conn.commit()

    # Save sample_load.csv for Member B integration
    df_load.to_csv(SAMPLE_CSV_PATH, index=False)
    logger.info(f"Saved sample load CSV to {SAMPLE_CSV_PATH}")

    conn.close()
    logger.info("Dataset population complete.")
    return df_load
