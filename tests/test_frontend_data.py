"""
Unit tests for PowerPool frontend API client and mock data fallback.
"""

from frontend.api_client import PowerPoolAPIClient


def test_api_client_fallback_forecast():
    client = PowerPoolAPIClient(base_url="http://localhost:9999")  # Offline URL
    res = client.get_forecast(scenario="sunny")
    assert "slots" in res
    assert len(res["slots"]) == 96


def test_api_client_fallback_optimize():
    client = PowerPoolAPIClient(base_url="http://localhost:9999")
    res = client.optimize(scenario="sunny")
    assert "peak_reduction_pct" in res
    assert res["peak_reduction_pct"] > 0


def test_api_client_fallback_nudges():
    client = PowerPoolAPIClient(base_url="http://localhost:9999")
    res = client.get_nudges(household_id=1, scenario="sunny")
    assert res["household_id"] == 1
    assert len(res["nudges"]) > 0


def test_api_client_fallback_dr():
    client = PowerPoolAPIClient(base_url="http://localhost:9999")
    res = client.trigger_dr_event()
    assert res["success"] is True
