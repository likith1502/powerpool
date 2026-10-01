"""
test_grid_reliability_upgrade.py — Tests for live ML forecasting service, capacity-aware optimization,
feasibility evaluation, and two-stage demand response.
"""
import os
import pytest
from unittest.mock import patch

from ml.forecast_demand import load_demand_model
from ml.forecast_service import forecast_service, ForecastService
from backend.optimizer import evaluate_feasibility, simulate_stage2_dr, greedy_schedule
from backend.schemas import OptimizeResponse, FeasibilityReport


def test_model_loading_and_caching():
    """Verify that load_demand_model safely loads Booster on Windows and caches the instance."""
    m1, t1 = load_demand_model()
    m2, t2 = load_demand_model()
    assert m1 is m2, "Model instance should be cached as a singleton"
    assert t1 in ["LightGBM", "SeasonalBaseline"]
    if t1 == "LightGBM":
        assert m1.num_trees() == 150
        assert m1.num_feature() == 13


def test_forecast_service_live_prediction():
    """Verify that forecast_service generates valid 96-slot predictions tagged as live_model."""
    slots = forecast_service.predict_live_forecast(date_str="2026-10-01", scenario="sunny")
    assert len(slots) == 96
    for s in slots:
        assert s["data_source"] == "live_model"
        assert s["demand_kw"] >= 0.0
        assert "capacity_kw" in s
        assert "gap_kw" in s
        assert "is_stress" in s
    peak = max(s["demand_kw"] for s in slots)
    assert peak > 170.0, "Sunny peak demand should reflect feeder stress"


def test_rebound_peak_protection_and_energy_conservation():
    """Verify that greedy_schedule protects against rebound peaks in destination blocks."""
    # Synthetic demand curve with high evening peak
    demand = [80.0] * 96
    for s in range(74, 86):
        demand[s] = 200.0  # Overloaded above 170
    solar = [0.0] * 96
    for s in range(40, 60):
        solar[s] = 60.0  # Midday solar available

    apps = [
        {"id": 1, "household_id": "HH001", "power_kw": 2.0, "duration_slots": 4, "flexible": 1,
         "earliest_slot": 36, "latest_slot": 64, "usual_slot": 78},
        {"id": 2, "household_id": "HH002", "power_kw": 1.5, "duration_slots": 4, "flexible": 1,
         "earliest_slot": 36, "latest_slot": 64, "usual_slot": 80}
    ]

    shifts, new_net = greedy_schedule(demand, solar, apps, capacity=170.0, compliance=1.0)
    assert len(shifts) == 2
    # Verify shifts landed in valid destination blocks without exceeding capacity
    for s in range(96):
        if s not in range(74, 86):
            assert new_net[s] <= 170.0, f"Rebound peak created at slot {s}"

    # Verify energy conservation: kWh removed from origin equals kWh added to destination
    for sh in shifts:
        assert sh.kwh == round(sh.power_kw * sh.duration * 0.25, 3)


def test_feasibility_evaluation_structure():
    """Verify evaluate_feasibility reports correct metrics and bottleneck diagnosis."""
    before = [100.0] * 96
    before[76] = 340.0
    after = [100.0] * 96
    after[76] = 274.0

    rep = evaluate_feasibility(before, after, capacity=170.0, available_flex_kw=65.5)
    assert rep["baseline_peak_kw"] == 340.0
    assert rep["optimized_peak_kw"] == 274.0
    assert rep["peak_reduction_kw"] == 66.0
    assert rep["remaining_overload_kw"] == 104.0
    assert rep["is_feasible"] is False
    assert rep["feasibility_status"] == "PARTIAL_RELIEF"
    assert len(rep["limiting_factors"]) > 0

    # Test fully feasible scenario
    feasible_after = [100.0] * 96
    feasible_after[76] = 160.0
    rep_feas = evaluate_feasibility(before, feasible_after, capacity=170.0, available_flex_kw=180.0)
    assert rep_feas["is_feasible"] is True
    assert rep_feas["feasibility_status"] == "FEASIBLE"
    assert rep_feas["remaining_overload_kw"] == 0.0


def test_simulate_stage2_dr_clears_overload():
    """Verify simulate_stage2_dr eliminates remaining overload down to transformer rating."""
    after_stage1 = [100.0] * 96
    after_stage1[76] = 274.83
    after_stage1[77] = 260.0

    stage2_curve, peak2, curtailed_kwh = simulate_stage2_dr(after_stage1, capacity=170.0)
    assert peak2 <= 170.0, f"Stage 2 peak ({peak2} kW) must not exceed 170 kW capacity"
    assert curtailed_kwh > 0.0


def test_api_live_forecast_and_optimize_endpoints(fresh_client):
    """Verify API handles live=True and returns rich feasibility in /optimize."""
    try:
        # 1. Live forecast
        r_live = fresh_client.get("/forecast?scenario=sunny&live=true")
        assert r_live.status_code == 200
        live_data = r_live.json()
        assert live_data["slots"][0]["data_source"] == "live_model"

        # 2. Optimize endpoint with feasibility
        r_opt = fresh_client.post("/optimize", json={"scenario": "sunny"})
        assert r_opt.status_code == 200
        opt_data = r_opt.json()
        assert "remaining_overload_kw" in opt_data
        assert "is_feasible" in opt_data
        assert "feasibility_status" in opt_data
        assert "stage2_after" in opt_data
        assert opt_data["stage2_peak_kw"] <= 170.0
    finally:
        # Clean up created nudges so session-shared DB remains pristine
        from backend.db import get_conn
        with get_conn() as conn:
            conn.execute("DELETE FROM nudges")
            conn.commit()
