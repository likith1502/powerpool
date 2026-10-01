"""
test_phase2_integration.py — Phase 2 Backend-Frontend Integration Tests.

Validates all 10 verification requirements from Phase 2:
1. GET / returns HTTP 200
2. GET /health still works
3. POST /optimize accepts frontend's JSON body
4. Optimization responses contain all fields required by frontend charts
5. Numeric household IDs resolve correctly (1 -> HH001)
6. Existing string household IDs still work (HH001)
7. Hindi and Telugu nudge fields are present when expected
8. Existing duplicate-response protection remains intact
9. Existing scenario behavior and ML/optimizer logic remain intact
10. The frontend imports successfully and its API client can connect to the backend
"""

import pytest
from frontend.api_client import PowerPoolAPIClient, _build_fallback_mock_state


def test_root_endpoint_and_health(client):
    """1. GET / returns HTTP 200 and 2. GET /health still works."""
    r_root = client.get("/")
    assert r_root.status_code == 200
    d_root = r_root.json()
    assert d_root["status"] == "ok"
    assert "message" in d_root

    r_health = client.get("/health")
    assert r_health.status_code == 200
    d_health = r_health.json()
    assert d_health["status"] == "ok"
    assert "mock_data" in d_health


def test_optimize_accepts_json_body_and_returns_chart_fields(fresh_client):
    """3. POST /optimize accepts JSON body and 4. returns all chart fields in before/after."""
    payload = {
        "date": "2026-10-01",
        "scenario": "sunny",
        "compliance_rate": 0.65
    }
    resp = fresh_client.post("/optimize", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    for key in ("before", "after", "nudges_created", "peak_before_kw",
                "peak_after_kw", "peak_reduction_pct", "kwh_shifted"):
        assert key in data, f"Missing key in /optimize response: {key}"

    assert len(data["before"]) == 96
    assert len(data["after"]) == 96

    # Verify chart fields accessed by render_before_after_chart and render_gap_chart
    chart_fields = ("slot", "time", "demand_kw", "capacity_kw", "solar_kw", "gap_kw", "is_stress")
    for slot in (data["before"][0], data["before"][76], data["after"][0], data["after"][76]):
        for field in chart_fields:
            assert field in slot, f"Missing chart field: {field}"
            assert slot[field] is not None

    # Check math validity of gap and stress flag
    sample = data["before"][76]
    assert sample["capacity_kw"] == 170.0
    assert sample["gap_kw"] == round(sample["demand_kw"] - sample["capacity_kw"], 2)
    assert sample["is_stress"] == (sample["gap_kw"] > 0)


def test_numeric_and_string_household_ids_and_translations(fresh_client):
    """5. Numeric household IDs resolve, 6. string IDs work, 7. multilingual messages present."""
    fresh_client.post("/optimize")

    # 5. Numeric lookup "1"
    r_num = fresh_client.get("/nudges/1")
    assert r_num.status_code == 200
    data_num = r_num.json()
    nudges_num = data_num["nudges"] if isinstance(data_num, dict) else data_num

    # 6. String lookup "HH001"
    r_str = fresh_client.get("/nudges/HH001")
    assert r_str.status_code == 200
    data_str = r_str.json()
    nudges_str = data_str["nudges"] if isinstance(data_str, dict) else data_str

    # Both lookups must match
    assert len(nudges_num) == len(nudges_str)
    if nudges_num:
        n = nudges_num[0]
        # 7. Check multilingual fields
        assert "message" in n
        assert "message_hi" in n and n["message_hi"] is not None
        assert "message_te" in n and n["message_te"] is not None
        assert len(n["message_hi"]) > 0
        assert len(n["message_te"]) > 0


def test_duplicate_response_protection(fresh_client):
    """8. Duplicate click response protection remains intact."""
    fresh_client.post("/optimize")
    households = fresh_client.get("/households").json()

    target_nudge = None
    for hh in households:
        res = fresh_client.get(f"/nudges/{hh['id']}").json()
        pending = [n for n in res["nudges"] if n["status"] == "pending"]
        if pending:
            target_nudge = pending[0]
            break

    assert target_nudge is not None
    nid = target_nudge["id"]

    # First accept
    r1 = fresh_client.post(f"/nudges/{nid}/respond", json={"accept": True}).json()
    assert r1["status"] == "accepted"
    pts1 = r1["points_added"]
    total1 = r1["household_points"]
    assert pts1 > 0

    # Second accept: points_added must be 0
    r2 = fresh_client.post(f"/nudges/{nid}/respond", json={"accept": True}).json()
    assert r2["status"] == "accepted"
    assert r2["points_added"] == 0
    assert r2["household_points"] == total1


def test_scenario_contrasts_preserved(client):
    """9. Existing scenario behavior and ML/optimizer logic remain intact."""
    res_sunny = client.get("/forecast?scenario=sunny").json()
    res_cloudy = client.get("/forecast?scenario=cloudy").json()
    res_heatwave = client.get("/forecast?scenario=heatwave").json()

    slots_s = res_sunny["slots"]
    slots_c = res_cloudy["slots"]
    slots_h = res_heatwave["slots"]

    # Solar contrast
    assert max(s["solar_kw"] for s in slots_s) > max(s["solar_kw"] for s in slots_c) * 2.0
    # Demand peak contrast
    assert max(s["demand_kw"] for s in slots_h) > max(s["demand_kw"] for s in slots_c)


def test_frontend_api_client_and_fallback():
    """10. Frontend imports successfully and fallback works deterministically."""
    # Test client initialization
    client = PowerPoolAPIClient(base_url="http://127.0.0.1:8000")
    assert client.base_url == "http://127.0.0.1:8000"

    # Test self-contained mock fallback
    mock_sunny = _build_fallback_mock_state("sunny")
    assert len(mock_sunny["optimization"]["before"]) == 96
    assert len(mock_sunny["optimization"]["after"]) == 96
    assert mock_sunny["optimization"]["peak_reduction_pct"] > 0
    assert "message_hi" in mock_sunny["optimization"]["nudges"][0]
    assert "message_te" in mock_sunny["optimization"]["nudges"][0]

    # Test fallback retrieval through client
    forecast = client.get_forecast(scenario="sunny")
    assert len(forecast["slots"]) == 96

    opt = client.optimize(scenario="sunny")
    assert len(opt["before"]) == 96
    assert "gap_kw" in opt["before"][0]

    nudges = client.get_nudges(household_id=1, scenario="sunny")
    assert len(nudges["nudges"]) > 0

    kpis = client.get_kpis(scenario="sunny")
    assert kpis["peak_reduction_pct"] > 0
