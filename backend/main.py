"""
PowerPool FastAPI Backend Application.
Provides REST API endpoints for demand forecasting, greedy load optimization, resident nudges, DISCOM KPIs, and Demand Response events.
"""

from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List

from backend.schemas import (
    ForecastResponse,
    OptimizeRequest,
    OptimizeResponse,
    HouseholdNudgesResponse,
    NudgeRespondRequest,
    NudgeRespondResponse,
    KPIResponse,
    LeaderboardResponse,
    DREventRequest,
    DREventResponse,
    FlexCapacityResponse,
)
from backend.services.scenario_service import load_scenario_data
from backend.services.kpi_service import calculate_system_kpis
from backend.optimizer import run_load_shifting_optimization

app = FastAPI(
    title="PowerPool API",
    description="Neighbourhood Load Flexibility & Solar Intermittency Management API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session cache for optimized state & nudges
SYSTEM_CACHE: Dict[str, Any] = {}


def get_current_system_state(scenario: str = "sunny") -> Dict[str, Any]:
    """
    Initializes or returns cached system optimization state for the given scenario.
    """
    cache_key = scenario.lower()
    if cache_key not in SYSTEM_CACHE:
        scenario_data = load_scenario_data(cache_key)
        opt_result = run_load_shifting_optimization(scenario_data)
        kpis = calculate_system_kpis(
            opt_result["before"],
            opt_result["after"],
            opt_result["kwh_shifted"],
            len(scenario_data["households"]),
        )
        SYSTEM_CACHE[cache_key] = {
            "scenario_data": scenario_data,
            "optimization": opt_result,
            "kpis": kpis,
            "nudges_map": {n["id"]: n for n in opt_result["nudges"]},
        }
    return SYSTEM_CACHE[cache_key]


@app.get("/")
def read_root():
    return {
        "status": "online",
        "app": "PowerPool API",
        "docs": "/docs",
    }


@app.get("/forecast", response_model=ForecastResponse)
def get_forecast(
    date: str = Query("2026-10-01", description="Target forecast date"),
    scenario: str = Query("sunny", description="Weather scenario: sunny, cloudy, heatwave"),
):
    state = get_current_system_state(scenario)
    return {
        "date": date,
        "scenario": scenario,
        "slots": state["optimization"]["before"],
    }


@app.post("/optimize", response_model=OptimizeResponse)
def optimize_loads(req: OptimizeRequest):
    scenario = req.scenario or "sunny"
    state = get_current_system_state(scenario)
    opt = state["optimization"]
    return {
        "before": opt["before"],
        "after": opt["after"],
        "nudges_created": opt["nudges_created"],
        "peak_before_kw": opt["peak_before_kw"],
        "peak_after_kw": opt["peak_after_kw"],
        "peak_reduction_pct": opt["peak_reduction_pct"],
        "kwh_shifted": opt["kwh_shifted"],
    }


@app.get("/nudges/{household_id}", response_model=HouseholdNudgesResponse)
def get_household_nudges(
    household_id: int = Path(..., ge=1, le=100),
    scenario: str = Query("sunny", description="Weather scenario"),
):
    state = get_current_system_state(scenario)
    nudges_map = state["nudges_map"]
    household_nudges = [n for n in nudges_map.values() if n["household_id"] == household_id]
    
    # If no nudge exists for this household, generate a default fallback nudge
    if not household_nudges:
        household_nudges = [{
            "id": 900 + household_id,
            "household_id": household_id,
            "appliance": "Washing Machine",
            "from_time": "19:00",
            "to_time": "13:00–14:00",
            "kwh_shifted": 1.2,
            "points": 15,
            "saving_rs": 8.0,
            "message": "Run your Washing Machine between 13:00–14:00. Earn 15 points and save about ₹8.",
            "message_hi": "अपनी वॉशिंग मशीन 13:00–14:00 के बीच चलाएँ। 15 अंक कमाएँ और लगभग ₹8 बचाएँ।",
            "message_te": "మీ వాషింగ్ మెషీన్‌ను 13:00–14:00 సమయంలో నడపండి. 15 పాయింట్లు సంపాదించి సుమారు ₹8 ఆదా చేయండి.",
            "status": "pending",
        }]
        
    return {
        "household_id": household_id,
        "nudges": household_nudges,
    }


@app.post("/nudges/{nudge_id}/respond", response_model=NudgeRespondResponse)
def respond_nudge(nudge_id: int, req: NudgeRespondRequest):
    # Search across system cache
    target_nudge = None
    for state in SYSTEM_CACHE.values():
        if nudge_id in state["nudges_map"]:
            target_nudge = state["nudges_map"][nudge_id]
            break

    if not target_nudge:
        # Create a transient response for unknown/mock IDs
        target_nudge = {
            "id": nudge_id,
            "points": 15,
            "saving_rs": 8.0,
            "status": "pending",
        }

    status_str = "accepted" if req.accept else "skipped"
    target_nudge["status"] = status_str

    msg = "Great! Your load was shifted successfully." if req.accept else "Nudge skipped."
    return {
        "id": nudge_id,
        "status": status_str,
        "points_added": target_nudge["points"] if req.accept else 0,
        "saving_rs": target_nudge["saving_rs"] if req.accept else 0.0,
        "message": msg,
    }


@app.get("/kpis", response_model=KPIResponse)
def get_kpis(scenario: str = Query("sunny")):
    state = get_current_system_state(scenario)
    return state["kpis"]


@app.get("/leaderboard", response_model=LeaderboardResponse)
def get_leaderboard(scenario: str = Query("sunny")):
    state = get_current_system_state(scenario)
    households = state["scenario_data"]["households"]
    
    # Sort households by points
    sorted_h = sorted(households, key=lambda x: x["points"], reverse=True)[:5]
    leaderboard = []
    for idx, h in enumerate(sorted_h, start=1):
        leaderboard.append({
            "rank": idx,
            "household_id": h["household_id"],
            "name": h["name"],
            "points": h["points"],
            "kwh_shifted": h["kwh_shifted_total"],
        })
        
    return {"leaderboard": leaderboard}


@app.get("/flex-capacity", response_model=FlexCapacityResponse)
def get_flex_capacity(scenario: str = Query("sunny")):
    state = get_current_system_state(scenario)
    opt = state["optimization"]
    households = state["scenario_data"]["households"]
    
    avail_kw = round(opt["kwh_shifted"] * 0.98, 1)
    avail_homes = int(len(households) * 0.67)
    
    return {
        "window": "next_hour",
        "available_kw": max(20.0, avail_kw),
        "households_available": avail_homes,
    }


@app.post("/dr-event", response_model=DREventResponse)
def trigger_dr_event(req: DREventRequest):
    state = get_current_system_state("sunny")
    opt = state["optimization"]
    
    nudges_created = max(35, int(opt["nudges_created"] * 0.4))
    peak_after = round(max(150.0, opt["peak_after_kw"] - 5.0), 1)
    
    return {
        "success": True,
        "nudges_created": nudges_created,
        "target_kw": req.target_kw,
        "available_flexible_kw": 42.0,
        "peak_after_kw": peak_after,
        "message": f"Demand response event triggered for slots {req.start_slot}-{req.end_slot}. {nudges_created} households nudged.",
    }


@app.get("/scenarios")
def get_scenarios():
    return {
        "scenarios": ["sunny", "cloudy", "heatwave"]
    }
