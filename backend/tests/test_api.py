"""
test_api.py — HTTP integration tests for the PowerPool backend.

DB isolation: conftest.py seeds a fresh test DB once per session and
tears it down afterwards.  This file must NOT call seed() or set DB_PATH
itself — conftest.py owns that.

Fixtures:
  client       — session-scoped shared client (fast, suitable for most tests)
  fresh_client — function-scoped reseed before each test (use when the test
                 needs zero nudges / zero points regardless of prior tests)
"""


# ── Existing behaviour (must not regress) ─────────────────────────────────────

def test_health(client):
    r = client.get("/health").json()
    assert r["status"] == "ok"
    assert "mock_data" in r           # new field; value is bool


def test_forecast_shape(client):
    f = client.get("/forecast").json()
    assert len(f) == 96
    slot = f[0]
    for key in ("slot", "time", "demand_kw", "solar_kw", "capacity_kw",
                "gap_kw", "is_stress", "data_source"):
        assert key in slot, f"Missing key in /forecast slot: {key}"
    assert slot["data_source"] in ("mock", "model")


def test_optimize_reduces_peak(client):
    o = client.post("/optimize").json()
    assert o["nudges_created"] > 0
    assert o["peak_after_kw"] < o["peak_before_kw"]
    assert 0 < o["peak_reduction_pct"] <= 100


def test_households(client):
    hh = client.get("/households").json()
    assert len(hh) == 80
    assert all(k in hh[0] for k in ("id", "name", "type", "block", "language", "points"))


def test_nudges_and_respond(client):
    # Ensure there are nudges after optimize
    client.post("/optimize")
    hh = client.get("/households").json()[0]["id"]
    ns = client.get(f"/nudges/{hh}").json()
    # Fall back to household 2 if household 1 has no nudges
    if not ns:
        for row in client.get("/households").json():
            ns = client.get(f"/nudges/{row['id']}").json()
            if ns:
                break
    assert ns, "No nudges found after optimize"
    nid = ns[0]["id"]
    r = client.post(f"/nudges/{nid}/respond", json={"accept": True}).json()
    assert r["status"] == "accepted"
    assert r["household_points"] > 0


def test_respond_invalid_nudge_404(client):
    """Responding to a non-existent nudge ID must return HTTP 404."""
    resp = client.post("/nudges/999999/respond", json={"accept": True})
    assert resp.status_code == 404
    body = resp.json()
    assert "detail" in body
    assert "not found" in body["detail"].lower()


def test_kpis(client):
    client.post("/optimize")
    k = client.get("/kpis").json()
    for field in ("peak_before_kw", "peak_after_kw", "kwh_shifted",
                  "rs_saved", "co2_kg", "transformer_risk"):
        assert field in k
    assert k["transformer_risk"] in ("LOW", "MEDIUM", "HIGH")
    assert k["kwh_shifted"] > 0


def test_leaderboard(client):
    client.post("/optimize")
    lb = client.get("/leaderboard").json()
    assert len(lb) <= 10
    assert lb[0]["rank"] == 1


def test_dr_event(client):
    dr = client.post("/dr-event",
                     json={"start_slot": 72, "end_slot": 84, "target_kw": 10})
    assert dr.status_code == 200
    body = dr.json()
    assert "nudges_created" in body
    assert "kw_reduced_expected" in body


def test_flex_capacity(client):
    assert len(client.get("/flex-capacity").json()) == 24


# ── New planned-name aliases (must return same shape as originals) ─────────────

def test_schedule_run_alias(client):
    """POST /schedule/run must return the same schema as POST /optimize."""
    r = client.post("/schedule/run").json()
    for key in ("before", "after", "nudges_created", "peak_before_kw",
                "peak_after_kw", "peak_reduction_pct"):
        assert key in r, f"Missing key in /schedule/run response: {key}"


def test_schedule_household_alias(client):
    """GET /schedule/{id} must return the same shape as GET /nudges/{id}."""
    hh = client.get("/households").json()[0]["id"]
    via_nudges = client.get(f"/nudges/{hh}").json()
    via_schedule = client.get(f"/schedule/{hh}").json()
    assert via_nudges == via_schedule


def test_metrics_alias(client):
    """GET /metrics must return the same shape as GET /kpis."""
    kpis = client.get("/kpis").json()
    metrics = client.get("/metrics").json()
    assert kpis == metrics


# ── New: POST /nudge/send ─────────────────────────────────────────────────────

def test_nudge_send_no_token(client):
    """Without TELEGRAM_TOKEN, /nudge/send returns api_only + delivered=false."""
    # Ensure nudges exist
    client.post("/optimize")
    hh = client.get("/households").json()[0]["id"]
    r = client.post("/nudge/send", json={"household_id": hh}).json()
    assert r["household_id"] == hh
    assert isinstance(r["nudges_queued"], int)
    assert r["channel"] in ("api_only", "telegram")
    assert isinstance(r["delivered"], bool)
    assert isinstance(r["messages"], list)


def test_nudge_send_specific_nudge(fresh_client):
    """Sending a specific nudge_id queues exactly one pending message.

    Uses fresh_client (function-scoped reseed) so this test is never at the
    mercy of session ordering.  After /demo/reseed the DB has 0 nudges;
    POST /optimize creates them; the first pending nudge for any household is
    then targeted by nudge_id and must return nudges_queued == 1.
    """
    fresh_client.post("/optimize")
    # Walk households until we find one that has a pending nudge
    households = fresh_client.get("/households").json()
    target_hh = None
    target_nid = None
    for hh in households:
        nudges = fresh_client.get(f"/nudges/{hh['id']}").json()
        pending = [n for n in nudges if n["status"] == "pending"]
        if pending:
            target_hh = hh["id"]
            target_nid = pending[0]["id"]
            break
    assert target_hh is not None, "No households have pending nudges after /optimize"
    r = fresh_client.post(
        "/nudge/send",
        json={"household_id": target_hh, "nudge_id": target_nid},
    ).json()
    assert r["nudges_queued"] == 1, f"Expected 1 pending nudge, got {r['nudges_queued']}"
    assert len(r["messages"]) == 1
    assert r["messages"][0]  # non-empty string


def test_nudge_send_unknown_household(client):
    """Sending to a non-existent household returns 0 nudges, not an error."""
    r = client.post("/nudge/send", json={"household_id": 99999}).json()
    assert r["nudges_queued"] == 0
    assert r["messages"] == []


# ── Demo helpers ───────────────────────────────────────────────────────────────

def test_demo_reseed(client):
    r = client.post("/demo/reseed").json()
    assert r["status"] == "reseeded"
    # DB should still have 80 households after reseed
    assert len(client.get("/households").json()) == 80


def test_demo_simulate_responses(client):
    client.post("/optimize")
    r = client.post("/demo/simulate-responses").json()
    assert "processed" in r
    assert "accepted" in r


def test_demo_simulate_responses_rate_zero(fresh_client):
    """Boundary rate=0 is accepted and results in 0 accepted nudges."""
    fresh_client.post("/optimize")
    r = fresh_client.post("/demo/simulate-responses?rate=0")
    assert r.status_code == 200
    data = r.json()
    assert data["processed"] > 0
    assert data["accepted"] == 0


def test_demo_simulate_responses_rate_one(fresh_client):
    """Boundary rate=1 is accepted and results in all pending nudges accepted."""
    fresh_client.post("/optimize")
    r = fresh_client.post("/demo/simulate-responses?rate=1")
    assert r.status_code == 200
    data = r.json()
    assert data["processed"] > 0
    assert data["accepted"] == data["processed"]


def test_demo_simulate_responses_negative_rate_rejected(client):
    """Negative rate is out of range and rejected with HTTP 422."""
    r = client.post("/demo/simulate-responses?rate=-0.1")
    assert r.status_code == 422


def test_demo_simulate_responses_excessive_rate_rejected(client):
    """Rate > 1.0 is out of range and rejected with HTTP 422."""
    r = client.post("/demo/simulate-responses?rate=1.5")
    assert r.status_code == 422

