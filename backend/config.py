"""Central settings. Values come from .env so nothing is hard-coded."""
import math
import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "data/powerpool.db")
FEEDER_CAPACITY_KW = float(os.getenv("FEEDER_CAPACITY_KW", "170"))
COMPLIANCE = float(os.getenv("COMPLIANCE", "0.65"))       # share of nudges residents accept
if not math.isfinite(COMPLIANCE) or not (0.0 < COMPLIANCE <= 1.0):
    raise ValueError(f"COMPLIANCE configuration must be a finite number in range (0.0, 1.0], got {COMPLIANCE}")
PEAK_TARIFF = float(os.getenv("PEAK_TARIFF", os.getenv("PEAK_TARIFF_RS_PER_KWH", "9.0")))      # Rs/kWh in stress slots
OFFPEAK_TARIFF = float(os.getenv("OFFPEAK_TARIFF", os.getenv("OFFPEAK_TARIFF_RS_PER_KWH", "6.0")))  # Rs/kWh elsewhere
CO2_PER_KWH = float(os.getenv("CO2_PER_KWH", os.getenv("CO2_FACTOR_KG_PER_KWH", "0.71")))     # kg/kWh, verify latest CEA value
POINTS_PER_KWH = 10
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
SLOTS_PER_DAY = 96  # 15-minute slots
# Forecast data source resolution:
# - If MOCK_DATA is explicitly set ('true'/'false'/'1'/'0'), honor it.
# - If unset: auto-detect from active database. If forecast table has >= 288 slots
#   (Member A's 3-scenario pipeline output), MOCK_DATA is False ('model').
#   If empty or populated by seed_mock (< 288 slots), MOCK_DATA is True ('mock').
def is_mock_data() -> bool:
    raw = os.getenv("MOCK_DATA")
    if raw is not None and raw.strip() != "":
        clean = raw.strip().lower()
        if clean in ("false", "0", "no"):
            return False
        if clean in ("true", "1", "yes"):
            return True
    try:
        db_file = os.getenv("DB_PATH", DB_PATH)
        if os.path.exists(db_file):
            import sqlite3
            conn = sqlite3.connect(db_file)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM forecast")
            count = cur.fetchone()[0]
            conn.close()
            return count < 288
    except Exception:
        pass
    return False


class _MockDataProxy:
    """Dynamic proxy for MOCK_DATA so module-level imports reflect runtime changes."""
    def __bool__(self) -> bool:
        return is_mock_data()

    def __repr__(self) -> str:
        return str(bool(self))

    def __eq__(self, other) -> bool:
        return bool(self) == other


MOCK_DATA = _MockDataProxy()


def slot_to_time(slot: int) -> str:
    m = slot * 15
    return f"{m // 60:02d}:{m % 60:02d}"
