"""
Dataset Build Script for Member A.
Builds SQLite database data/powerpool.db, generates 100 households, appliances, 30-day load history,
and exports data/sample_load.csv and data/cached_weather.csv.
"""

import os
import sys
import logging

# Ensure root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.generator import build_and_populate_dataset, DB_PATH
from data.weather import get_weather_with_fallback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("build_dataset")

def main():
    logger.info("--- Starting PowerPool Member A Dataset Generation ---")

    num_households = int(os.getenv("POWERPOOL_NUM_HOUSEHOLDS", "100"))
    days = int(os.getenv("POWERPOOL_DAYS", "30"))
    seed = int(os.getenv("RANDOM_SEED", "42"))

    # Populate households, appliances, load_history, sample_load.csv
    logger.info(f"Generating {num_households} households, appliances, and {days} days of load data...")
    build_and_populate_dataset(num_households=num_households, days=days, seed=seed, db_path=DB_PATH)

    # Fetch and cache weather
    logger.info("Fetching and caching Open-Meteo weather data...")
    weather_df = get_weather_with_fallback("2026-09-01", days=days)

    # Populate weather table in database
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM weather")
    cursor.executemany("""
    INSERT INTO weather (timestamp, temp_c, cloud_cover, irradiance_wm2)
    VALUES (:timestamp, :temp_c, :cloud_cover, :irradiance_wm2)
    """, weather_df.to_dict(orient="records"))
    conn.commit()
    conn.close()

    logger.info("--- Member A Dataset Build Successfully Completed ---")

if __name__ == "__main__":
    main()
