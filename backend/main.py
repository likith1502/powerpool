"""PowerPool FastAPI app. Run:  uvicorn backend.main:app --reload
Docs at http://127.0.0.1:8000/docs

Route naming
------------
Internal names (original implementation):
  GET  /forecast          POST /optimize              GET  /kpis
  GET  /nudges/{id}       POST /nudges/{id}/respond   GET  /leaderboard
  POST /dr-event          GET  /flex-capacity          GET  /households

Planned external names (aliases — both paths work):
  POST /schedule/run      → same as POST /optimize
  GET  /schedule/{id}     → same as GET  /nudges/{household_id}
  GET  /metrics           → same as GET  /kpis

New endpoints (this file):
  POST /nudge/send        → assemble nudge text; no real Telegram calls in tests
"""
from contextlib import asynccontextmanager
from typing import List, Optional, Union
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from . import services as svc
from .config import slot_to_time, MOCK_DATA
from .db import init_db, rows
from .schemas import (ForecastSlot, ForecastResponse, OptimizeResponse, OptimizeRequest,
                      Nudge, NudgesResponse, RespondRequest, RespondResponse, KPIs,
                      LeaderRow, LeaderboardResponse, DREventRequest,
                      DREventResponse, FlexHour, FlexCapacityResponse, Household,
                      NudgeSendRequest, NudgeSendResponse)

@asynccontextmanager
async def lifespan(app):
    init_db()
    if not rows("SELECT 1 FROM forecast LIMIT 1"):   # empty DB on fresh deploy
        from .seed_mock import seed
        seed()
    yield


app = FastAPI(title="PowerPool API", version="1.1", lifespan=lifespan,
              description="Neighbourhood load flexibility backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])


def guard(fn, *a, **k):
    try:
        return fn(*a, **k)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "message": "PowerPool API", "mock_data": MOCK_DATA}


@app.get("/health")
def health():
    return {"status": "ok", "mock_data": MOCK_DATA}


# ── Forecast ──────────────────────────────────────────────────────────────────

@app.get("/forecast", response_model=Union[ForecastResponse, List[ForecastSlot]])
def forecast(date: Optional[str] = None, scenario: Optional[str] = None, format: Optional[str] = None):
    """96 × 15-minute slots.
    `data_source` = 'mock' when seeded data is in use; 'model' after Member A's
    pipeline writes real forecast rows and MOCK_DATA=false is set in .env.
    Supports ?scenario=sunny|cloudy|heatwave.
    """
    effective_date = guard(svc.resolve_date, date, scenario) or "2026-10-01"
    data = guard(svc.load_forecast, effective_date, scenario)
    source = "mock" if MOCK_DATA else "model"
    slots = [{**r, "slot": i, "time": slot_to_time(i), "timestamp": r.get("timestamp"),
              "is_stress": bool(r["is_stress"]), "data_source": source}
             for i, r in enumerate(data)]
    if format == "list":
        return slots
    return {"date": effective_date, "slots": slots}


# ── Schedule / Optimize ───────────────────────────────────────────────────────

@app.post("/optimize", response_model=OptimizeResponse, tags=["schedule"])
@app.post("/schedule/run", response_model=OptimizeResponse, tags=["schedule"],
          summary="Run scheduler (alias for /optimize)")
def optimize(body: Optional[OptimizeRequest] = None, date: Optional[str] = None, scenario: Optional[str] = None):
    """Clear all nudges and run the greedy load-shift scheduler.
    Also accessible as POST /schedule/run (planned external name).
    Supports JSON body (frontend) or query parameters (API callers/tests).
    """
    effective_date = (body.date if body and body.date else None) or date
    effective_scenario = (body.scenario if body and body.scenario else None) or scenario
    effective_compliance = body.compliance_rate if body else None
    return guard(svc.run_optimize, effective_date, effective_scenario, compliance=effective_compliance)


# ── Households ────────────────────────────────────────────────────────────────

@app.get("/households", response_model=List[Household])
def households():
    return rows("SELECT * FROM households ORDER BY id")


# ── Nudges / Per-household schedule ───────────────────────────────────────────

@app.get("/nudges/{household_id}", response_model=Union[NudgesResponse, List[Nudge]], tags=["nudges"])
@app.get("/schedule/{household_id}", response_model=Union[NudgesResponse, List[Nudge]], tags=["schedule"],
         summary="Household schedule (alias for /nudges/{household_id})")
def get_nudges(household_id: str, scenario: Optional[str] = None, format: Optional[str] = None):
    """All nudges (load-shift requests) for one household.
    Also accessible as GET /schedule/{household_id} (planned external name).
    """
    nudges = svc.nudges_for(household_id)
    if format == "list":
        return nudges
    return {"household_id": household_id, "nudges": nudges}


@app.post("/nudges/{nudge_id}/respond", response_model=RespondResponse)
def respond(nudge_id: int, body: RespondRequest):
    res = svc.respond(nudge_id, body.accept)
    if res is None:
        raise HTTPException(404, "Nudge not found")
    return res


# ── Nudge send ────────────────────────────────────────────────────────────────

@app.post("/nudge/send", response_model=NudgeSendResponse, tags=["nudges"])
def nudge_send(body: NudgeSendRequest):
    """Assemble and (optionally) push nudge text for a household."""
    import os
    all_nudges = svc.nudges_for(body.household_id)
    if body.nudge_id is not None:
        all_nudges = [n for n in all_nudges if n["id"] == body.nudge_id]
    pending = [n for n in all_nudges if n["status"] == "pending"]

    messages = [n["message"] for n in pending]

    token = os.getenv("TELEGRAM_TOKEN", "")
    delivered = False
    if token and getattr(body, "chat_id", None) and messages:
        from .telegram_service import send_telegram_message
        results = [send_telegram_message(str(body.chat_id), msg, token=token) for msg in messages]
        delivered = all(results) if results else False

    return {
        "household_id": body.household_id,
        "nudges_queued": len(pending),
        "channel": "api_only" if not token else "telegram",
        "delivered": delivered,
        "messages": messages,
    }


# ── KPIs / Metrics ────────────────────────────────────────────────────────────

@app.get("/kpis", response_model=KPIs, tags=["metrics"])
@app.get("/metrics", response_model=KPIs, tags=["metrics"],
         summary="Impact metrics (alias for /kpis)")
def kpis(date: Optional[str] = None, scenario: Optional[str] = None):
    """Aggregate dashboard KPIs.
    Also accessible as GET /metrics (planned external name).
    """
    return guard(svc.kpis, date=date, scenario=scenario)


# ── Leaderboard ───────────────────────────────────────────────────────────────

@app.get("/leaderboard", response_model=Union[LeaderboardResponse, List[LeaderRow]])
def leaderboard(limit: int = 10, scenario: Optional[str] = None, format: Optional[str] = None):
    data = svc.leaderboard(limit)
    if format == "list":
        return data
    return {"leaderboard": data}


# ── Demand-response event ─────────────────────────────────────────────────────

@app.post("/dr-event", response_model=DREventResponse)
def dr_event(body: DREventRequest, date: Optional[str] = None, scenario: Optional[str] = None):
    effective_date = body.date or date
    effective_scenario = body.scenario or scenario
    return guard(svc.run_dr_event, body.start_slot, body.end_slot, body.target_kw,
                 date=effective_date, scenario=effective_scenario)


# ── Flex capacity ─────────────────────────────────────────────────────────────

@app.get("/flex-capacity", response_model=Union[FlexCapacityResponse, List[FlexHour]])
def flex_capacity(scenario: Optional[str] = None, format: Optional[str] = None):
    if format == "hourly":
        return svc.flex_capacity_hourly()
    return svc.flex_capacity_summary()



# ── Demo helpers ──────────────────────────────────────────────────────────────

@app.post("/demo/simulate-responses")
def simulate_responses(rate: float = Query(0.65, ge=0.0, le=1.0), seed: int = 7):
    """Demo helper: randomly accept ~rate of pending nudges (compliance simulation)."""
    import random
    rnd = random.Random(seed)
    pending = rows("SELECT id FROM nudges WHERE status = 'pending'")
    acc = 0
    for n in pending:
        ok = rnd.random() < rate
        svc.respond(n["id"], ok)
        acc += ok
    return {"processed": len(pending), "accepted": acc}


@app.post("/demo/reseed")
def reseed():
    """Demo helper: wipe and re-seed the database with fresh mock data.
    Never call on production. Useful for live demos and CI reset.
    """
    from .seed_mock import seed as do_seed
    do_seed()
    return {"status": "reseeded"}
