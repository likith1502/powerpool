"""Regression tests for UI/deploy fixes found in the Oct 2026 browser walkthrough."""
from pathlib import Path
import pytest


def test_forecast_live_route_runs_live_model(client):
    pytest.importorskip("lightgbm")
    r = client.get("/forecast/live", params={"scenario": "sunny", "format": "list"})
    assert r.status_code == 200
    assert r.json()[0]["data_source"] == "live_model"


def test_plain_forecast_is_not_live(client):
    r = client.get("/forecast", params={"scenario": "sunny", "format": "list"})
    assert r.status_code == 200
    assert r.json()[0]["data_source"] != "live_model"


def test_ui_does_not_mix_100_household_stress_profile():
    for p in ["frontend/components/sidebar.py", "frontend/pages/2_DISCOM.py"]:
        src = Path(p).read_text(encoding="utf-8")
        assert "1-100" not in src and "100 Residential" not in src and "max_value=100" not in src


def test_render_installs_ml_dependencies():
    assert "pip install -r requirements.txt" in Path("render.yaml").read_text()
    req = Path("requirements.txt").read_text().lower()
    for pkg in ("lightgbm", "pandas", "numpy"):
        assert pkg in req


def test_rerunning_optimizer_does_not_double_pay_points(client):
    from backend.db import rows
    client.post("/optimize", json={"scenario": "sunny"})
    n = rows("SELECT id, household_id, appliance_id FROM nudges WHERE scenario_date = '2026-10-01' "
             "AND status = 'pending' LIMIT 1")[0]
    hh = n["household_id"]
    pts = lambda: rows("SELECT points FROM households WHERE id = ?", (hh,))[0]["points"]
    start = pts()
    client.post(f"/nudges/{n['id']}/respond", json={"accept": True})
    once = pts()
    client.post("/optimize", json={"scenario": "sunny"})
    same = rows("SELECT id FROM nudges WHERE appliance_id = ? AND scenario_date = '2026-10-01'",
                (n["appliance_id"],))
    assert len(same) == 1 and same[0]["id"] == n["id"]   # kept, not re-created
    for m in same:
        client.post(f"/nudges/{m['id']}/respond", json={"accept": True})
    assert once > start and pts() == once


def test_nudge_text_and_card_use_same_rupee_rounding():
    from backend.translations import nudge_text
    assert "Rs 13.5" in nudge_text("E-rickshaw charging", 75, 43, 45, 13.5, lang="en")


def test_english_message_available_for_non_english_household(client):
    from backend.db import rows, get_conn
    client.post("/optimize", json={"scenario": "sunny"})
    hh = rows("SELECT household_id FROM nudges LIMIT 1")[0]["household_id"]
    with get_conn() as c:
        c.execute("UPDATE households SET language = 'te' WHERE id = ?", (hh,))
    nudges = client.get(f"/nudges/{hh}", params={"format": "list"}).json()
    n = nudges[0] if isinstance(nudges, list) else nudges["nudges"][0]
    assert n["message_en"].startswith("Run your")
    assert n["message_en"] != n["message_te"]


def test_scenario_switch_does_not_leak_or_double_pay(client):
    from backend.db import rows
    client.post("/optimize", json={"scenario": "sunny"})
    cloudy = client.get("/kpis", params={"scenario": "cloudy"}).json()
    assert cloudy["peak_after_kw"] <= cloudy["peak_before_kw"]
    n = rows("SELECT id, household_id FROM nudges WHERE scenario_date = '2026-10-01' "
             "AND status = 'pending' LIMIT 1")[0]
    hh = n["household_id"]
    client.post(f"/nudges/{n['id']}/respond", json={"accept": True})
    pts = rows("SELECT points FROM households WHERE id = ?", (hh,))[0]["points"]
    for sc in ("cloudy", "heatwave", "sunny"):
        client.post("/optimize", json={"scenario": sc})
    for m in rows("SELECT id FROM nudges WHERE household_id = ? AND scenario_date = '2026-10-01'", (hh,)):
        client.post(f"/nudges/{m['id']}/respond", json={"accept": True})
    assert rows("SELECT points FROM households WHERE id = ?", (hh,))[0]["points"] == pts
    assert rows("SELECT status FROM nudges WHERE id = ?", (n["id"],))[0]["status"] == "accepted"


def test_feasibility_reasons_are_only_stated_when_true():
    from backend.optimizer import evaluate_feasibility
    r = evaluate_feasibility([200.0] * 4, [180.0] * 4, capacity=170.0, available_flex_kw=261.5)
    text = " ".join(r["limiting_factors"])
    assert "less than peak overload" not in text      # 261.5 kW pool is NOT less than a 30 kW overload
    assert "represents -" not in text                 # never a negative baseload


def test_leaderboard_limit_is_validated(client):
    assert client.get("/leaderboard", params={"limit": -1}).status_code == 422
    assert client.get("/leaderboard", params={"limit": 5, "format": "list"}).status_code == 200
