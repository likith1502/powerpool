"""HOUR 1-2 ONLY: hard-coded JSON with the exact contract shape so Member C can
build the UI immediately. Run: uvicorn backend.mock_main:app --reload
Delete (or stop using) once backend/main.py works."""
import math
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="PowerPool MOCK API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
T = lambda s: f"{s * 15 // 60:02d}:{s * 15 % 60:02d}"
BEFORE = [round(75 + 121 * math.exp(-((s / 4 - 20) ** 2) / 3), 1) for s in range(96)]
AFTER = [round(v - (25 if 74 <= s <= 84 else 0) + (12 if 40 <= s <= 56 else 0), 1)
         for s, v in enumerate(BEFORE)]
NUDGE = {"id": 1, "household_id": 1, "appliance_id": 3, "appliance": "Washing machine",
         "from_slot": 78, "to_slot": 52, "from_time": "19:30", "to_time": "13:00",
         "kwh_shifted": 0.5, "points": 5, "saving_rs": 1.5, "status": "pending",
         "message": "Run your Washing machine at 13:00 today instead of 19:30. Earn 5 points and save about Rs 2."}


@app.get("/forecast")
def forecast(date: str = None):
    return [{"slot": s, "time": T(s), "demand_kw": BEFORE[s], "solar_kw": 0.0,
             "capacity_kw": 170.0, "gap_kw": BEFORE[s] - 170, "is_stress": BEFORE[s] > 170}
            for s in range(96)]


@app.post("/optimize")
def optimize(date: str = None):
    pts = lambda c: [{"slot": s, "time": T(s), "demand_kw": v} for s, v in enumerate(c)]
    return {"before": pts(BEFORE), "after": pts(AFTER), "nudges_created": 143,
            "peak_before_kw": max(BEFORE), "peak_after_kw": max(AFTER),
            "peak_reduction_pct": round(100 * (max(BEFORE) - max(AFTER)) / max(BEFORE), 1)}


@app.get("/households")
def households():
    return [{"id": 1, "name": "Reddy #1", "type": "low", "block": "Block B", "language": "te", "points": 0}]


@app.get("/nudges/{household_id}")
def nudges(household_id: int):
    return [NUDGE]


@app.post("/nudges/{nudge_id}/respond")
def respond(nudge_id: int, body: dict):
    return {"nudge_id": nudge_id, "status": "accepted" if body.get("accept") else "skipped",
            "household_points": 5 if body.get("accept") else 0}


@app.get("/kpis")
def kpis(date: str = None):
    return {"peak_before_kw": 196.0, "peak_after_kw": 163.0, "peak_reduction_pct": 16.8,
            "kwh_shifted": 99.0, "rs_saved": 297.0, "co2_kg": 70.3,
            "solar_self_use_pct_before": 78.0, "solar_self_use_pct": 92.0,
            "participants": 22, "total_households": 80, "transformer_risk": "MEDIUM"}


@app.get("/leaderboard")
def leaderboard(limit: int = 10):
    return [{"rank": i, "household_id": i, "name": f"House {i}", "block": "Block A",
             "points": 60 - 5 * i} for i in range(1, limit + 1)]


@app.post("/dr-event")
def dr_event(body: dict):
    return {"nudges_created": 21, "kw_reduced_expected": 8.0,
            "after": [{"slot": s, "time": T(s), "demand_kw": v} for s, v in enumerate(AFTER)]}


@app.get("/flex-capacity")
def flex():
    return [{"hour": h, "time": f"{h:02d}:00", "flexible_kw": 42.0 if 17 <= h <= 21 else 8.0}
            for h in range(24)]
