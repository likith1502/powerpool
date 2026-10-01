"""
test_member_c_contract.py — Comprehensive contract verification for Member C's Streamlit frontend.

Tests all requirements specified in PowerPool_Member2_Integration_Handoff.md:
- 96 forecast slots with 15-minute resolution and timestamp
- Sunny, Cloudy, and Heatwave real scenario contrasts
- Optimization calculations and kwh_shifted
- String household IDs in nudges and schedule
- Nudge accept/skip persistence and duplicate click reward protection
- KPI calculations and exact Member C field names
- Leaderboard envelope and kwh_shifted tracking
- Flex capacity summary and hourly breakdown
- Demand-response event response fields
"""

import pytest


def test_forecast_envelope_and_96_slots(client):
    """Verify GET /forecast?date=YYYY-MM-DD returns envelope with 96 slots at 15-min intervals."""
    resp = client.get("/forecast?date=2026-10-01")
    assert resp.status_code == 200
    data = resp.json()
    assert "date" in data
    assert data["date"] == "2026-10-01"
    assert "slots" in data
    slots = data["slots"]
    assert len(slots) == 96

    # Verify 15-minute resolution and all required fields
    for i, slot in enumerate(slots):
        assert slot["slot"] == i
        hour = (i * 15) // 60
        minute = (i * 15) % 60
        assert slot["time"] == f"{hour:02d}:{minute:02d}"
        assert "timestamp" in slot
        assert "demand_kw" in slot and isinstance(slot["demand_kw"], (int, float))
        assert "solar_kw" in slot and isinstance(slot["solar_kw"], (int, float))
        assert "capacity_kw" in slot and slot["capacity_kw"] == 170.0
        assert "gap_kw" in slot and isinstance(slot["gap_kw"], (int, float))
        assert "is_stress" in slot and isinstance(slot["is_stress"], bool)


def test_scenarios_produce_different_outputs(client):
    """Verify Sunny, Cloudy, and Heatwave scenarios alter real forecast data."""
    res_sunny = client.get("/forecast?scenario=sunny").json()
    res_cloudy = client.get("/forecast?scenario=cloudy").json()
    res_heatwave = client.get("/forecast?scenario=heatwave").json()

    slots_sunny = res_sunny["slots"]
    slots_cloudy = res_cloudy["slots"]
    slots_heatwave = res_heatwave["slots"]

    # Midday solar in sunny must be significantly higher than cloudy
    midday_sunny_solar = max(s["solar_kw"] for s in slots_sunny[40:60])
    midday_cloudy_solar = max(s["solar_kw"] for s in slots_cloudy[40:60])
    assert midday_sunny_solar > midday_cloudy_solar * 2.0, (
        f"Sunny solar ({midday_sunny_solar}) must exceed cloudy ({midday_cloudy_solar})"
    )

    # Peak demand in heatwave scenario must be higher than cloudy scenario
    peak_heatwave_demand = max(s["demand_kw"] for s in slots_heatwave)
    peak_cloudy_demand = max(s["demand_kw"] for s in slots_cloudy)
    assert peak_heatwave_demand > peak_cloudy_demand, (
        f"Heatwave peak ({peak_heatwave_demand}) must exceed cloudy ({peak_cloudy_demand})"
    )


def test_optimize_response_contract(fresh_client):
    """Verify POST /optimize returns all Member C required fields including kwh_shifted."""
    resp = fresh_client.post("/optimize")
    assert resp.status_code == 200
    data = resp.json()

    for key in ("before", "after", "nudges_created", "peak_before_kw",
                "peak_after_kw", "peak_reduction_pct", "kwh_shifted"):
        assert key in data, f"Missing key in /optimize response: {key}"

    assert len(data["before"]) == 96
    assert len(data["after"]) == 96
    assert data["nudges_created"] > 0
    assert data["peak_after_kw"] < data["peak_before_kw"]
    assert data["peak_reduction_pct"] > 0.0
    assert data["kwh_shifted"] > 0.0


def test_nudges_envelope_and_string_household(fresh_client):
    """Verify GET /nudges/{household_id} returns Member C envelope with string IDs."""
    fresh_client.post("/optimize")
    households = fresh_client.get("/households").json()
    assert len(households) > 0
    target_hh = str(households[0]["id"])

    resp = fresh_client.get(f"/nudges/{target_hh}")
    assert resp.status_code == 200
    data = resp.json()
    assert "household_id" in data
    assert str(data["household_id"]) == target_hh
    assert "nudges" in data
    assert isinstance(data["nudges"], list)

    # Find household with nudges
    if not data["nudges"]:
        for hh in households:
            cand_resp = fresh_client.get(f"/nudges/{hh['id']}").json()
            if cand_resp["nudges"]:
                data = cand_resp
                break

    assert len(data["nudges"]) > 0
    nudge = data["nudges"][0]
    for field in ("id", "appliance", "from_time", "to_time", "kwh_shifted",
                  "points", "saving_rs", "message", "status"):
        assert field in nudge, f"Missing field in nudge: {field}"
    assert nudge["status"] in ("pending", "accepted", "skipped")


def test_nudge_accept_skip_and_duplicate_prevention(fresh_client):
    """Verify nudge response status updates, point awards, and duplicate click protection."""
    fresh_client.post("/optimize")
    households = fresh_client.get("/households").json()
    target_hh = None
    target_nudge = None

    for hh in households:
        res = fresh_client.get(f"/nudges/{hh['id']}").json()
        pending = [n for n in res["nudges"] if n["status"] == "pending"]
        if pending:
            target_hh = hh["id"]
            target_nudge = pending[0]
            break

    assert target_nudge is not None
    nid = target_nudge["id"]
    pts = target_nudge["points"]

    # 1. Accept nudge
    resp1 = fresh_client.post(f"/nudges/{nid}/respond", json={"accept": True})
    assert resp1.status_code == 200
    d1 = resp1.json()
    assert d1["status"] == "accepted"
    assert d1["points_added"] == pts
    assert d1["saving_rs"] == target_nudge["saving_rs"]
    initial_hh_pts = d1["household_points"]
    assert initial_hh_pts >= pts

    # 2. Duplicate click protection (clicking accept again should NOT award points twice)
    resp2 = fresh_client.post(f"/nudges/{nid}/respond", json={"accept": True})
    assert resp2.status_code == 200
    d2 = resp2.json()
    assert d2["status"] == "accepted"
    assert d2["points_added"] == 0, "Duplicate accept must award 0 points"
    assert d2["household_points"] == initial_hh_pts, "Household points must not double-count"

    # 3. Skip nudge
    resp3 = fresh_client.post(f"/nudges/{nid}/respond", json={"accept": False})
    assert resp3.status_code == 200
    d3 = resp3.json()
    assert d3["status"] == "skipped"
    assert d3["points_added"] == 0


def test_kpis_contract_and_calculations(fresh_client):
    """Verify GET /kpis returns exact Member C field names with calculated metrics."""
    fresh_client.post("/optimize")
    resp = fresh_client.get("/kpis")
    assert resp.status_code == 200
    k = resp.json()

    required_fields = (
        "peak_reduction_pct", "kwh_shifted", "solar_self_use_pct",
        "solar_self_use_change_pct", "co2_kg", "participants", "households"
    )
    for field in required_fields:
        assert field in k, f"Missing required KPI field: {field}"
        assert isinstance(k[field], (int, float)), f"Field {field} must be numeric"

    assert k["households"] > 0
    assert k["peak_reduction_pct"] > 0.0
    assert k["kwh_shifted"] > 0.0


def test_leaderboard_envelope_and_updates(fresh_client):
    """Verify GET /leaderboard returns envelope with ranking, points, and kwh_shifted."""
    fresh_client.post("/optimize")
    # Accept a nudge so a household earns points and shifted kWh
    households = fresh_client.get("/households").json()
    for hh in households:
        res = fresh_client.get(f"/nudges/{hh['id']}").json()
        if res["nudges"]:
            fresh_client.post(f"/nudges/{res['nudges'][0]['id']}/respond", json={"accept": True})
            break

    resp = fresh_client.get("/leaderboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "leaderboard" in data
    lb = data["leaderboard"]
    assert len(lb) > 0
    first = lb[0]
    for key in ("rank", "household_id", "name", "points", "kwh_shifted"):
        assert key in first, f"Missing key in leaderboard row: {key}"
    assert first["rank"] == 1
    assert first["points"] > 0
    assert first["kwh_shifted"] > 0.0


def test_flex_capacity_summary_and_hourly(client):
    """Verify GET /flex-capacity returns summary card fields and hourly breakdown."""
    resp = client.get("/flex-capacity")
    assert resp.status_code == 200
    data = resp.json()
    assert data["window"] == "next_hour"
    assert "available_kw" in data and isinstance(data["available_kw"], (int, float))
    assert "households_available" in data and isinstance(data["households_available"], int)
    assert "hourly" in data and len(data["hourly"]) == 24

    # Also test format=hourly query param
    resp_hourly = client.get("/flex-capacity?format=hourly")
    assert resp_hourly.status_code == 200
    hourly = resp_hourly.json()
    assert isinstance(hourly, list)
    assert len(hourly) == 24


def test_dr_event_contract(client):
    """Verify POST /dr-event accepts window parameters and returns Member C fields."""
    payload = {"start_slot": 76, "end_slot": 88, "target_kw": 170.0}
    resp = client.post("/dr-event", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    for field in ("success", "nudges_created", "target_kw", "available_flexible_kw", "peak_after_kw"):
        assert field in data, f"Missing field in DR response: {field}"

    assert data["success"] is True
    assert data["target_kw"] == 170.0
    assert data["available_flexible_kw"] >= 0.0
    assert data["peak_after_kw"] > 0.0
