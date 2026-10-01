"""SQLite access. Creates the agreed tables (Section 5) if they don't exist."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS households(
  id INTEGER PRIMARY KEY, name TEXT, type TEXT, block TEXT,
  language TEXT DEFAULT 'en', points INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS appliances(
  id INTEGER PRIMARY KEY, household_id INTEGER, name TEXT, power_kw REAL,
  duration_slots INTEGER, flexible INTEGER, earliest_slot INTEGER,
  latest_slot INTEGER, usual_slot INTEGER);
CREATE TABLE IF NOT EXISTS load_history(
  household_id INTEGER, timestamp TEXT, kwh REAL);
CREATE TABLE IF NOT EXISTS weather(
  timestamp TEXT, temp_c REAL, cloud_cover REAL, irradiance_wm2 REAL);
CREATE TABLE IF NOT EXISTS forecast(
  timestamp TEXT, demand_kw REAL, solar_kw REAL, capacity_kw REAL,
  gap_kw REAL, is_stress INTEGER);
CREATE TABLE IF NOT EXISTS nudges(
  id INTEGER PRIMARY KEY AUTOINCREMENT, household_id INTEGER, appliance_id INTEGER,
  from_slot INTEGER, to_slot INTEGER, kwh_shifted REAL, points INTEGER,
  saving_rs REAL, status TEXT DEFAULT 'pending', source TEXT DEFAULT 'optimize');
"""


@contextmanager
def get_conn():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as c:
        c.executescript(SCHEMA)


def rows(sql, params=()):
    with get_conn() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]
