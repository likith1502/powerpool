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
# Set MOCK_DATA=false in .env once Member A's real pipeline is writing to the DB.
# The /forecast endpoint exposes this so Member C can show a data-freshness badge.
MOCK_DATA: bool = os.getenv("MOCK_DATA", "true").lower() not in ("false", "0", "no")


def slot_to_time(slot: int) -> str:
    m = slot * 15
    return f"{m // 60:02d}:{m % 60:02d}"
