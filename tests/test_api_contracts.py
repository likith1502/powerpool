"""
Unit tests for PowerPool FastAPI API contracts.
"""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["app"] == "PowerPool API"


def test_forecast_endpoint():
    response = client.get("/forecast?scenario=sunny")
    assert response.status_code == 200
    data = response.json()
    assert "slots" in data
    assert len(data["slots"]) == 96


def test_optimize_endpoint():
    response = client.post("/optimize", json={"scenario": "sunny"})
    assert response.status_code == 200
    data = response.json()
    assert "before" in data
    assert "after" in data
    assert data["peak_reduction_pct"] >= 0.0


def test_nudges_endpoint():
    response = client.get("/nudges/1?scenario=sunny")
    assert response.status_code == 200
    data = response.json()
    assert data["household_id"] == 1
    assert "nudges" in data


def test_nudge_respond():
    response = client.post("/nudges/101/respond", json={"accept": True})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["points_added"] > 0


def test_kpis_endpoint():
    response = client.get("/kpis?scenario=sunny")
    assert response.status_code == 200
    data = response.json()
    assert "peak_reduction_pct" in data
    assert "co2_kg" in data


def test_leaderboard_endpoint():
    response = client.get("/leaderboard?scenario=sunny")
    assert response.status_code == 200
    data = response.json()
    assert "leaderboard" in data
    assert len(data["leaderboard"]) <= 5


def test_dr_event_endpoint():
    response = client.post("/dr-event", json={"start_slot": 74, "end_slot": 88, "target_kw": 170.0})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["nudges_created"] > 0
