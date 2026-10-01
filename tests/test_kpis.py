"""
Unit tests for KPI calculations and optimization metrics.
"""

from backend.services.kpi_service import calculate_system_kpis


def test_kpi_formulas():
    before = [{"demand_kw": 200.0, "solar_kw": 50.0}]
    after = [{"demand_kw": 160.0, "solar_kw": 50.0}]
    kwh_shifted = 40.0

    kpis = calculate_system_kpis(before, after, kwh_shifted, num_households=100)

    assert kpis["peak_reduction_pct"] == 20.0  # (200-160)/200 * 100
    assert kpis["co2_kg"] == 28.0             # 40 * 0.7
    assert kpis["kwh_shifted"] == 40.0
    assert kpis["participants"] == 67
