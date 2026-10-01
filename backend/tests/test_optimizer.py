import pytest
from backend.optimizer import greedy_schedule, stress_slots, net_load

def make_case():
    demand = [100.0] * 96
    for s in range(76, 80):          # 19:00-21:00 peak
        demand[s] = 180.0
    solar = [0.0] * 96
    for s in range(40, 60):          # 10:00-15:00 sun
        solar[s] = 60.0
    apps = [{"id": i, "household_id": i, "power_kw": 2.0, "duration_slots": 2,
             "flexible": 1, "earliest_slot": 36, "latest_slot": 68,
             "usual_slot": 76 + 2 * (i % 2)} for i in range(1, 11)]
    return demand, solar, apps

def test_peak_reduced():
    d, s, a = make_case()
    shifts, after = greedy_schedule(d, s, a, capacity=170)
    assert shifts
    assert max(after) < max(net_load(d, s))

def test_no_move_into_stress_or_outside_window():
    d, s, a = make_case()
    stress = stress_slots(net_load(d, s), 170)
    shifts, _ = greedy_schedule(d, s, a, capacity=170)
    for sh in shifts:
        assert 36 <= sh.to_slot <= 68 - sh.duration + 1
        assert all((sh.to_slot + k) not in stress for k in range(sh.duration))

def test_each_appliance_once():
    d, s, a = make_case()
    shifts, _ = greedy_schedule(d, s, a, capacity=170)
    ids = [x.appliance_id for x in shifts]
    assert len(ids) == len(set(ids))

def test_prefers_solar_slots():
    d, s, a = make_case()
    shifts, _ = greedy_schedule(d, s, a, capacity=170)
    assert all(40 <= sh.to_slot < 60 for sh in shifts)


@pytest.mark.parametrize("zero_val", [0, 0.0])
def test_zero_compliance_raises_value_error(zero_val):
    d, s, a = make_case()
    with pytest.raises(ValueError, match="compliance"):
        greedy_schedule(d, s, a, compliance=zero_val)


@pytest.mark.parametrize("invalid_val", [-0.5, -1.0, 1.01, 2.0, float("nan"), float("inf"), float("-inf")])
def test_out_of_range_and_non_finite_compliance_raises_value_error(invalid_val):
    d, s, a = make_case()
    with pytest.raises(ValueError, match="compliance"):
        greedy_schedule(d, s, a, compliance=invalid_val)


@pytest.mark.parametrize("invalid_type", [None, "high", [0.5], True, False])
def test_invalid_type_compliance_raises_error(invalid_type):
    d, s, a = make_case()
    with pytest.raises((ValueError, TypeError)):
        greedy_schedule(d, s, a, compliance=invalid_type)


@pytest.mark.parametrize("valid_val", [0.1, 0.5, 0.65, 1.0])
def test_valid_compliance_values(valid_val):
    d, s, a = make_case()
    shifts, after = greedy_schedule(d, s, a, compliance=valid_val)
    assert shifts
    assert max(after) < max(net_load(d, s))


def test_config_compliance_validation():
    """Verify backend.config validates 0.0 < COMPLIANCE <= 1.0 at import/reload."""
    import importlib
    import os
    import backend.config as cfg

    orig = os.environ.get("COMPLIANCE")
    try:
        os.environ["COMPLIANCE"] = "0.0"
        with pytest.raises(ValueError, match="COMPLIANCE"):
            importlib.reload(cfg)

        os.environ["COMPLIANCE"] = "-0.5"
        with pytest.raises(ValueError, match="COMPLIANCE"):
            importlib.reload(cfg)

        os.environ["COMPLIANCE"] = "1.5"
        with pytest.raises(ValueError, match="COMPLIANCE"):
            importlib.reload(cfg)
    finally:
        if orig is not None:
            os.environ["COMPLIANCE"] = orig
        else:
            os.environ.pop("COMPLIANCE", None)
        importlib.reload(cfg)

