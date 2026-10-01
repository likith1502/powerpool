"""
Tests for string household ID support (e.g. 'HH001', 'HH002').
Verifies Pydantic schema representations, API route lookups, nudge operations,
and points updates for string household IDs.
"""
import pytest
from backend.schemas import (
    Household,
    Nudge,
    LeaderRow,
    NudgeSendRequest,
    NudgeSendResponse,
)
from backend import services as svc
from backend.optimizer import Shift


def test_schemas_accept_string_household_ids():
    """Verify that all relevant schemas accept string household IDs."""
    h = Household(
        id="HH001",
        name="Household 1",
        type="mid",
        block="Block A",
        language="en",
        points=100,
    )
    assert h.id == "HH001"

    n = Nudge(
        id=1,
        household_id="HH001",
        appliance_id=10,
        appliance="Washing machine",
        from_slot=76,
        to_slot=44,
        from_time="19:00",
        to_time="11:00",
        kwh_shifted=1.5,
        points=50,
        saving_rs=12.0,
        status="pending",
        message="Shift appliance",
    )
    assert n.household_id == "HH001"

    lr = LeaderRow(
        rank=1,
        household_id="HH001",
        name="Household 1",
        block="Block A",
        points=100,
    )
    assert lr.household_id == "HH001"

    ns_req = NudgeSendRequest(household_id="HH001")
    assert ns_req.household_id == "HH001"

    ns_resp = NudgeSendResponse(
        household_id="HH001",
        nudges_queued=1,
        channel="api_only",
        delivered=False,
        messages=["Test nudge"],
    )
    assert ns_resp.household_id == "HH001"


def test_household_lookup_accepts_string_id(client):
    """Verify GET /nudges/{household_id} and /schedule/{household_id} accept string IDs."""
    # Look up with string ID "HH001"
    r = client.get("/nudges/HH001")
    assert r.status_code == 200
    res = r.json()
    nudges = res["nudges"] if isinstance(res, dict) else res
    assert isinstance(nudges, list)

    # Alias /schedule/HH001
    r_alias = client.get("/schedule/HH001")
    assert r_alias.status_code == 200
    res_alias = r_alias.json()
    nudges_alias = res_alias["nudges"] if isinstance(res_alias, dict) else res_alias
    assert isinstance(nudges_alias, list)


def test_nudge_operations_preserve_string_id(fresh_client):
    """Verify scheduler and nudge creation/response preserve string household IDs."""
    # Run optimize to generate nudges
    opt_resp = fresh_client.post("/optimize")
    assert opt_resp.status_code == 200

    # Retrieve households to get a valid string ID
    households = fresh_client.get("/households").json()
    assert len(households) > 0
    target_hh = households[0]["id"]
    assert isinstance(target_hh, str)

    # Retrieve nudges for target household
    res = fresh_client.get(f"/nudges/{target_hh}").json()
    nudges = res["nudges"] if isinstance(res, dict) else res
    if not nudges:
        # Check other households if household 0 had no shiftable appliances
        for h in households:
            res = fresh_client.get(f"/nudges/{h['id']}").json()
            nudges = res["nudges"] if isinstance(res, dict) else res
            if nudges:
                target_hh = h["id"]
                break

    assert len(nudges) > 0
    assert nudges[0]["household_id"] == target_hh

    # Respond to nudge and check points update
    nudge_id = nudges[0]["id"]
    resp = fresh_client.post(f"/nudges/{nudge_id}/respond", json={"accept": True})

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["household_points"] > 0

    # Test /nudge/send with string ID
    send_resp = fresh_client.post("/nudge/send", json={"household_id": target_hh})
    assert send_resp.status_code == 200
    assert send_resp.json()["household_id"] == target_hh


def test_shift_dataclass_accepts_string_id():
    """Verify Shift dataclass accepts string household_id."""
    sh = Shift("HH001", 101, 76, 44, 2, 2.0)
    assert sh.household_id == "HH001"
    assert sh.kwh == 1.0
