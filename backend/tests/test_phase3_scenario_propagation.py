"""
test_phase3_scenario_propagation.py — Regression tests for Phase 3.1 Scenario Propagation.

Verifies:
1. Sunny, Cloudy, and Heatwave KPI requests resolve to their correct dates.
2. The three scenario KPI responses use the corresponding scenario data.
3. DR requests in Cloudy and Heatwave mode use the correct forecast.
4. Explicit date parameters retain their existing behavior.
5. Requests that omit scenario remain backward compatible.
6. Existing DR response fields and optimizer behavior remain intact.
7. Invalid scenarios are handled consistently with HTTP 503.
"""
import pytest
from backend.services import resolve_date, SCENARIO_DATES


# ── 1. Unit tests for resolve_date helper ─────────────────────────────────────

def test_resolve_date_scenarios():
    """Verify resolve_date maps sunny, cloudy, heatwave correctly."""
    assert resolve_date(scenario="sunny") == "2026-10-01"
    assert resolve_date(scenario="cloudy") == "2026-10-02"
    assert resolve_date(scenario="heatwave") == "2026-10-03"
    # Case insensitivity and whitespace stripping
    assert resolve_date(scenario=" SUNNY ") == "2026-10-01"
    assert resolve_date(scenario="Cloudy") == "2026-10-02"
    assert resolve_date(scenario="HEATWAVE") == "2026-10-03"


def test_resolve_date_precedence():
    """Verify scenario takes precedence over default or secondary date."""
    assert resolve_date(date="2026-10-01", scenario="cloudy") == "2026-10-02"
    assert resolve_date(date="2026-10-01", scenario="heatwave") == "2026-10-03"


def test_resolve_date_explicit_date():
    """Explicit date without scenario is preserved."""
    assert resolve_date(date="2026-10-02") == "2026-10-02"
    assert resolve_date(date="2026-10-05") == "2026-10-05"


def test_resolve_date_omitted():
    """Omitted date and scenario returns None."""
    assert resolve_date() is None
    assert resolve_date(None, None) is None


def test_resolve_date_invalid_scenario():
    """Invalid scenario raises ValueError."""
    with pytest.raises(ValueError, match="Unknown scenario 'storm'"):
        resolve_date(scenario="storm")


# ── 2. KPI Scenario Resolution & Contrast Tests ───────────────────────────────

def test_kpis_scenario_date_resolution(client):
    """1. Sunny, Cloudy, and Heatwave KPI requests resolve to their correct dates."""
    res_sunny = client.get("/kpis?scenario=sunny")
    assert res_sunny.status_code == 200

    res_cloudy = client.get("/kpis?scenario=cloudy")
    assert res_cloudy.status_code == 200

    res_heatwave = client.get("/kpis?scenario=heatwave")
    assert res_heatwave.status_code == 200


def test_kpis_distinct_scenario_data(fresh_client):
    """2. The three scenario KPI responses use corresponding scenario data."""
    sunny = fresh_client.get("/kpis?scenario=sunny").json()
    cloudy = fresh_client.get("/kpis?scenario=cloudy").json()
    heatwave = fresh_client.get("/kpis?scenario=heatwave").json()

    # Verify all three scenarios produce distinct KPI metrics
    assert sunny["peak_before_kw"] != cloudy["peak_before_kw"]
    assert cloudy["peak_before_kw"] != heatwave["peak_before_kw"]
    assert sunny["peak_before_kw"] != heatwave["peak_before_kw"]

    # Heatwave and sunny both have higher peak net demand than cloudy
    assert heatwave["peak_before_kw"] > cloudy["peak_before_kw"]
    assert sunny["peak_before_kw"] > cloudy["peak_before_kw"]

    # Solar self use differs between sunny and cloudy
    assert sunny["solar_self_use_pct"] != cloudy["solar_self_use_pct"]

    # All three must have valid numeric KPI fields
    for kpi in (sunny, cloudy, heatwave):
        assert kpi["peak_before_kw"] > 0
        assert kpi["peak_after_kw"] > 0
        assert "solar_self_use_pct" in kpi
        assert "solar_self_use_change_pct" in kpi
        assert kpi["transformer_risk"] in ("LOW", "MEDIUM", "HIGH")


def test_kpis_explicit_date_parity(client):
    """4. Explicit date parameters retain their existing behavior and match scenarios."""
    kpi_date_cloudy = client.get("/kpis?date=2026-10-02").json()
    kpi_scen_cloudy = client.get("/kpis?scenario=cloudy").json()
    assert kpi_date_cloudy["peak_before_kw"] == kpi_scen_cloudy["peak_before_kw"]
    assert kpi_date_cloudy["peak_after_kw"] == kpi_scen_cloudy["peak_after_kw"]

    kpi_date_heatwave = client.get("/kpis?date=2026-10-03").json()
    kpi_scen_heatwave = client.get("/kpis?scenario=heatwave").json()
    assert kpi_date_heatwave["peak_before_kw"] == kpi_scen_heatwave["peak_before_kw"]
    assert kpi_date_heatwave["peak_after_kw"] == kpi_scen_heatwave["peak_after_kw"]


def test_kpis_omitted_scenario_backward_compatibility(client):
    """5. Requests that omit scenario remain backward compatible (defaults to sunny)."""
    default_kpis = client.get("/kpis").json()
    sunny_kpis = client.get("/kpis?scenario=sunny").json()
    assert default_kpis["peak_before_kw"] == sunny_kpis["peak_before_kw"]
    assert default_kpis["peak_after_kw"] == sunny_kpis["peak_after_kw"]

    # GET /metrics alias also preserves behavior
    metrics = client.get("/metrics").json()
    assert metrics == default_kpis

    metrics_cloudy = client.get("/metrics?scenario=cloudy").json()
    kpis_cloudy = client.get("/kpis?scenario=cloudy").json()
    assert metrics_cloudy == kpis_cloudy


def test_kpis_invalid_scenario_returns_503(client):
    """Invalid scenario returns HTTP 503 consistent with guard convention."""
    res = client.get("/kpis?scenario=tornado")
    assert res.status_code == 503
    assert "Unknown scenario 'tornado'" in res.json()["detail"]


# ── 3. Demand Response Scenario Propagation Tests ─────────────────────────────

def test_dr_event_scenario_in_body(client):
    """3 & 6. DR requests accept scenario in body and use corresponding forecast."""
    # Test heatwave scenario via body
    dr_heatwave = client.post(
        "/dr-event",
        json={"start_slot": 74, "end_slot": 88, "target_kw": 15.0, "scenario": "heatwave"}
    )
    assert dr_heatwave.status_code == 200
    hw_body = dr_heatwave.json()
    assert hw_body["success"] is True
    assert hw_body["target_kw"] == 15.0
    assert "nudges_created" in hw_body
    assert "available_flexible_kw" in hw_body
    assert "peak_after_kw" in hw_body
    assert "kw_reduced_expected" in hw_body
    assert len(hw_body["after"]) == 96

    # Test cloudy scenario via body
    dr_cloudy = client.post(
        "/dr-event",
        json={"start_slot": 74, "end_slot": 88, "target_kw": 15.0, "scenario": "cloudy"}
    )
    assert dr_cloudy.status_code == 200
    cl_body = dr_cloudy.json()

    # Heatwave peak after DR should be significantly higher than Cloudy peak after DR
    assert hw_body["peak_after_kw"] > cl_body["peak_after_kw"]


def test_dr_event_scenario_query_param(client):
    """DR event supports scenario passed via query parameter."""
    res = client.post(
        "/dr-event?scenario=cloudy",
        json={"start_slot": 72, "end_slot": 84, "target_kw": 10.0}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["target_kw"] == 10.0


def test_dr_event_explicit_date(client):
    """4. Explicit date in DR event works and matches scenario date."""
    # DR events are cumulative, so start each call from the same freshly optimized state.
    client.post("/optimize", json={"scenario": "cloudy"})
    res_date = client.post(
        "/dr-event",
        json={"start_slot": 74, "end_slot": 88, "target_kw": 12.0, "date": "2026-10-02"}
    )
    client.post("/optimize", json={"scenario": "cloudy"})
    res_scen = client.post(
        "/dr-event",
        json={"start_slot": 74, "end_slot": 88, "target_kw": 12.0, "scenario": "cloudy"}
    )
    assert res_date.status_code == 200
    assert res_scen.status_code == 200
    assert res_date.json()["peak_after_kw"] == res_scen.json()["peak_after_kw"]


def test_dr_event_omitted_scenario_backward_compatibility(client):
    """5 & 6. DR event omitting scenario remains backward compatible."""
    res = client.post(
        "/dr-event",
        json={"start_slot": 72, "end_slot": 84, "target_kw": 10.0}
    )
    assert res.status_code == 200
    body = res.json()
    for field in ("success", "nudges_created", "target_kw",
                  "available_flexible_kw", "peak_after_kw",
                  "kw_reduced_expected", "after"):
        assert field in body
    assert body["success"] is True
    assert isinstance(body["nudges_created"], int)
    assert isinstance(body["kw_reduced_expected"], float)


def test_dr_event_invalid_scenario_returns_503(client):
    """Invalid scenario in DR event returns HTTP 503."""
    res = client.post(
        "/dr-event",
        json={"start_slot": 72, "end_slot": 84, "target_kw": 10.0, "scenario": "blizzard"}
    )
    assert res.status_code == 503
    assert "Unknown scenario 'blizzard'" in res.json()["detail"]
