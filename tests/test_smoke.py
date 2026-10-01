"""
End-to-End Smoke Test Suite for PowerPool.
"""

from data.seed_demo import generate_scenario_json
from backend.optimizer import run_load_shifting_optimization
from backend.services.kpi_service import calculate_system_kpis


def test_end_to_end_pipeline():
    # 1. Load scenario data
    sunny = generate_scenario_json("sunny")
    assert len(sunny["forecast"]) == 96
    assert len(sunny["households"]) == 100

    # 2. Run greedy optimizer
    opt = run_load_shifting_optimization(sunny)
    assert opt["peak_reduction_pct"] > 0
    assert opt["nudges_created"] > 0

    # 3. Compute system KPIs
    kpis = calculate_system_kpis(opt["before"], opt["after"], opt["kwh_shifted"], 100)
    assert kpis["peak_reduction_pct"] == opt["peak_reduction_pct"]
    assert kpis["co2_kg"] > 0
