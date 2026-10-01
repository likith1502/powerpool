"""Business logic that touches the DB: nudges, points, KPIs, DR, flex capacity."""
import os
from .db import get_conn, rows
from .config import (FEEDER_CAPACITY_KW, COMPLIANCE, CO2_PER_KWH, SLOTS_PER_DAY,
                     slot_to_time)
from .optimizer import Shift, greedy_schedule, projected_curve, net_load
from .translations import nudge_text

WEIGHT = {"accepted": 1.0, "pending": COMPLIANCE, "skipped": 0.0}


SCENARIO_DATES = {
    "sunny": "2026-10-01",
    "cloudy": "2026-10-02",
    "heatwave": "2026-10-03",
}


def resolve_date(date=None, scenario=None):
    """Resolve an effective date from (date, scenario).
    If scenario is provided, validate against SCENARIO_DATES and return the scenario date.
    If scenario is invalid, raise ValueError.
    If scenario is omitted, return date.
    """
    if scenario:
        sc_lower = str(scenario).strip().lower()
        if sc_lower in SCENARIO_DATES:
            return SCENARIO_DATES[sc_lower]
        raise ValueError(
            f"Unknown scenario '{scenario}'. Must be one of: {', '.join(SCENARIO_DATES.keys())}"
        )
    return date


# ---------- loading ----------
def load_forecast(date=None, scenario=None):
    date = resolve_date(date, scenario) or "2026-10-01"

    sql = "SELECT * FROM forecast"
    params = ()
    if date:
        sql += " WHERE timestamp LIKE ?"
        params = (f"{date}%",)
    data = rows(sql + " ORDER BY timestamp", params)[:SLOTS_PER_DAY]

    if len(data) < SLOTS_PER_DAY and date:
        try:
            from ml.pipeline import build_forecast_for_date
            sc = scenario or ("sunny" if "10-01" in str(date) else "cloudy" if "10-02" in str(date) else "heatwave")
            from . import db as _db_mod
            current_db = getattr(_db_mod, "DB_PATH", os.getenv("DB_PATH", "data/powerpool.db"))
            df = build_forecast_for_date(str(date), scenario=sc, db_path=current_db)
            data = df.to_dict(orient="records")[:SLOTS_PER_DAY]
        except Exception:
            pass

    if len(data) < SLOTS_PER_DAY:
        raise ValueError("Forecast table has fewer than 96 slots. Run seed or Member A's pipeline.")
    return data


def curves(date=None, scenario=None):
    f = load_forecast(date, scenario=scenario)
    return [r["demand_kw"] for r in f], [r["solar_kw"] for r in f]


def appliances():
    return rows("SELECT * FROM appliances WHERE flexible = 1")


def shifts_from_db():
    out = []
    for n in rows("SELECT n.*, a.power_kw, a.duration_slots FROM nudges n "
                  "JOIN appliances a ON a.id = n.appliance_id"):
        sh = Shift(str(n["household_id"]), n["appliance_id"], n["from_slot"], n["to_slot"],
                   n["duration_slots"], n["power_kw"])
        out.append((sh, WEIGHT[n["status"]]))
    return out


def normalize_household_id(household_id):
    if household_id is None:
        return ""
    s = str(household_id).strip()
    if s.isdigit():
        return f"HH{int(s):03d}"
    if s.lower().startswith("hh") and s[2:].isdigit():
        return f"HH{int(s[2:]):03d}"
    return s


def to_points(curve, solar_curve=None, capacity=FEEDER_CAPACITY_KW):
    pts = []
    cap = float(capacity)
    for i, v in enumerate(curve):
        d_kw = round(v, 2)
        s_kw = round(float(solar_curve[i]), 2) if solar_curve else 0.0
        gap = round(d_kw - cap, 2)
        pts.append({
            "slot": i,
            "time": slot_to_time(i),
            "demand_kw": d_kw,
            "capacity_kw": cap,
            "solar_kw": s_kw,
            "gap_kw": gap,
            "is_stress": bool(gap > 0)
        })
    return pts


def after_curve(date=None, scenario=None):
    d, s = curves(date, scenario=scenario)
    return net_load(d, s), projected_curve(d, s, shifts_from_db())


# ---------- writing nudges ----------
def save_shifts(shifts, source="optimize"):
    with get_conn() as c:
        for sh in shifts:
            c.execute("INSERT INTO nudges(household_id, appliance_id, from_slot, to_slot,"
                      " kwh_shifted, points, saving_rs, status, source)"
                      " VALUES (?,?,?,?,?,?,?,'pending',?)",
                      (str(sh.household_id), sh.appliance_id, sh.from_slot, sh.to_slot,
                       sh.kwh, sh.points, sh.saving_rs, source))


def run_optimize(date=None, scenario=None, compliance=None):
    with get_conn() as c:
        c.execute("DELETE FROM nudges")
        # NOTE: household points are NOT reset here.
        # Points are only awarded/revoked via respond() so that prior resident
        # acceptances survive an optimizer re-run on the DISCOM dashboard.
    effective_date = resolve_date(date, scenario) or "2026-10-01"
    d, s = curves(effective_date)
    comp = compliance if compliance is not None else COMPLIANCE
    shifts, _ = greedy_schedule(d, s, appliances(), compliance=comp)
    save_shifts(shifts)
    before, after = after_curve(effective_date)
    pb, pa = max(before), max(after)
    kwh = sum(sh.kwh for sh in shifts)

    from .optimizer import evaluate_feasibility, simulate_stage2_dr
    flex_apps = appliances()
    total_flex_kw = sum(a["power_kw"] for a in flex_apps)
    feasibility = evaluate_feasibility(before, after, capacity=FEEDER_CAPACITY_KW, available_flex_kw=total_flex_kw)
    stage2_curve, stage2_peak, stage2_curtailed = simulate_stage2_dr(after, capacity=FEEDER_CAPACITY_KW)

    return {
        "before": to_points(before, solar_curve=s),
        "after": to_points(after, solar_curve=s),
        "nudges_created": len(shifts),
        "peak_before_kw": round(pb, 2),
        "peak_after_kw": round(pa, 2),
        "peak_reduction_pct": round(100 * (pb - pa) / pb, 1) if pb else 0.0,
        "kwh_shifted": round(kwh, 2),
        "capacity_kw": float(FEEDER_CAPACITY_KW),
        "remaining_overload_kw": feasibility["remaining_overload_kw"],
        "is_feasible": feasibility["is_feasible"],
        "feasibility_status": feasibility["feasibility_status"],
        "feasibility": feasibility,
        "stage2_after": to_points(stage2_curve, solar_curve=s),
        "stage2_peak_kw": stage2_peak
    }


def run_dr_event(start, end, target_kw, date=None, scenario=None):
    effective_date = resolve_date(date, scenario) or "2026-10-01"
    d, s = curves(effective_date)
    window = list(range(start, end + 1)) if start <= end else \
        list(range(start, 96)) + list(range(0, end + 1))
    _, current = after_curve(effective_date)
    already = {n["appliance_id"] for n in rows("SELECT appliance_id FROM nudges")}

    # Calculate available flexible capacity in the target window
    avail_in_window = [a for a in appliances() if a["id"] not in already and
                       any(start <= (a["usual_slot"] + k) % 96 <= end for k in range(a["duration_slots"]))]
    avail_kw = round(sum(a["power_kw"] for a in avail_in_window), 1)

    solar_adj = [di - ci for di, ci in zip(d, current)]
    shifts, _ = greedy_schedule(d, solar_adj, appliances(), target_slots=window,
                                target_kw=target_kw, exclude_ids=already,
                                compliance=COMPLIANCE)
    save_shifts(shifts, source="dr")
    _, after = after_curve(effective_date)
    reduced = max(current[w] for w in window) - max(after[w] for w in window)
    peak_after = max(after)

    return {
        "success": True,
        "nudges_created": len(shifts),
        "target_kw": float(target_kw),
        "available_flexible_kw": avail_kw,
        "peak_after_kw": round(peak_after, 2),
        "kw_reduced_expected": round(reduced, 2),
        "after": to_points(after, solar_curve=s)
    }


# ---------- residents ----------
def nudges_for(household_id):
    hh_id = normalize_household_id(household_id)
    hh = rows("SELECT language FROM households WHERE id = ?", (hh_id,))
    lang = hh[0]["language"] if hh else "en"
    out = []
    for n in rows("SELECT n.*, a.name AS appliance FROM nudges n JOIN appliances a "
                  "ON a.id = n.appliance_id WHERE n.household_id = ? ORDER BY n.to_slot",
                  (hh_id,)):
        n["from_time"], n["to_time"] = slot_to_time(n["from_slot"]), slot_to_time(n["to_slot"])
        n["message"] = nudge_text(n["appliance"], n["from_slot"], n["to_slot"],
                                  n["points"], n["saving_rs"], lang)
        n["message_hi"] = nudge_text(n["appliance"], n["from_slot"], n["to_slot"],
                                     n["points"], n["saving_rs"], "hi")
        n["message_te"] = nudge_text(n["appliance"], n["from_slot"], n["to_slot"],
                                     n["points"], n["saving_rs"], "te")
        out.append(n)
    return out


def respond(nudge_id, accept):
    with get_conn() as c:
        n = c.execute("SELECT * FROM nudges WHERE id = ?", (nudge_id,)).fetchone()
        if n is None:
            return None
        new = "accepted" if accept else "skipped"
        hh_id = str(n["household_id"])
        points_added = 0
        saving_rs = 0.0

        # Duplicate protection: only award points if not previously accepted
        if n["status"] != "accepted" and new == "accepted":
            points_added = int(n["points"])
            saving_rs = float(n["saving_rs"])
            c.execute("UPDATE households SET points = points + ? WHERE id = ?",
                      (points_added, hh_id))
        elif n["status"] == "accepted" and new == "skipped":
            # Reversing acceptance if user skipped after accepting
            c.execute("UPDATE households SET points = MAX(0, points - ?) WHERE id = ?",
                      (n["points"], hh_id))
            points_added = 0

        c.execute("UPDATE nudges SET status = ? WHERE id = ?", (new, nudge_id))
        pts = c.execute("SELECT points FROM households WHERE id = ?",
                        (hh_id,)).fetchone()["points"]

    msg = ("Great! Your load was shifted successfully." if new == "accepted"
           else "Nudge skipped. No points awarded.")
    return {
        "id": nudge_id,
        "nudge_id": nudge_id,
        "status": new,
        "points_added": points_added,
        "saving_rs": saving_rs if new == "accepted" else 0.0,
        "household_points": pts,
        "message": msg
    }


def leaderboard(limit=10):
    data = rows("SELECT id AS household_id, name, block, points FROM households "
                "ORDER BY points DESC, id LIMIT ?", (limit,))

    # Calculate kwh_shifted for accepted nudges per household
    shifted_by_hh = {}
    for r in rows("SELECT household_id, SUM(kwh_shifted) as total_kwh FROM nudges WHERE status = 'accepted' GROUP BY household_id"):
        shifted_by_hh[str(r["household_id"])] = round(float(r["total_kwh"]), 1)

    for i, r in enumerate(data, 1):
        r["rank"] = i
        r["kwh_shifted"] = shifted_by_hh.get(str(r["household_id"]), 0.0)
    return data


# ---------- DISCOM ----------
def solar_self_use(demand_net, solar):
    """% of solar consumed locally. gross = net + solar; used = min(gross, solar)."""
    total = sum(solar)
    if total == 0:
        return 0.0
    used = sum(min(n + s, s) for n, s in zip(demand_net, solar))
    return round(100 * used / total, 1)


def kpis(date=None, scenario=None):
    effective_date = resolve_date(date, scenario) or "2026-10-01"
    _, s = curves(effective_date)
    before, after = after_curve(effective_date)
    weighted = shifts_from_db()
    kwh = sum(sh.kwh * w for sh, w in weighted)
    rs = sum(sh.saving_rs * w for sh, w in weighted)
    pb, pa = max(before), max(after)
    participants = rows("SELECT COUNT(DISTINCT household_id) c FROM nudges "
                        "WHERE status = 'accepted'")[0]["c"]
    total = rows("SELECT COUNT(*) c FROM households")[0]["c"]
    load_ratio = pa / FEEDER_CAPACITY_KW
    risk = "HIGH" if load_ratio > 1.05 else "MEDIUM" if load_ratio > 0.95 else "LOW"

    before_self = solar_self_use(before, s)
    after_self = solar_self_use(after, s)
    change_self = round(after_self - before_self, 1)

    return {
        "peak_before_kw": round(pb, 2),
        "peak_after_kw": round(pa, 2),
        "peak_reduction_pct": round(100 * (pb - pa) / pb, 1) if pb else 0.0,
        "kwh_shifted": round(kwh, 2),
        "rs_saved": round(rs, 2),
        "co2_kg": round(kwh * CO2_PER_KWH, 2),
        "solar_self_use_pct_before": before_self,
        "solar_self_use_pct": after_self,
        "solar_self_use_change_pct": change_self,
        "participants": participants,
        "total_households": total,
        "households": total,
        "transformer_risk": risk
    }


def flex_capacity_hourly():
    """kW that could still be moved, per hour, from appliances not yet nudged."""
    nudged = {n["appliance_id"] for n in rows("SELECT appliance_id FROM nudges")}
    per_hour = [0.0] * 24
    for a in appliances():
        if a["id"] in nudged:
            continue
        for k in range(a["duration_slots"]):
            h = ((a["usual_slot"] + k) % 96) // 4
            per_hour[h] += a["power_kw"] / 4  # average kW over the hour
    return [{"hour": h, "time": f"{h:02d}:00", "flexible_kw": round(v, 1)}
            for h, v in enumerate(per_hour)]


def flex_capacity_summary():
    """Summary of flexible capacity available for DR dispatch.

    'Available' means power that can still be shifted:
    - PENDING nudges: scheduled but not yet accepted → still dispatchable
    - SKIPPED / ACCEPTED nudges: excluded (opted-out or already committed)
    - Appliances with NO nudge: not yet scheduled → also counted

    After running the optimizer, pending-nudge capacity is the primary source.
    """
    # Pending nudges: dispatchable (resident has not yet responded)
    pending_rows = rows(
        "SELECT n.household_id, a.power_kw "
        "FROM nudges n JOIN appliances a ON a.id = n.appliance_id "
        "WHERE n.status = 'pending'"
    )
    pending_kw = round(sum(r["power_kw"] for r in pending_rows), 1)
    pending_hh = {str(r["household_id"]) for r in pending_rows}

    # Appliances with no nudge at all (un-optimized remainder)
    nudged_ids = {n["appliance_id"] for n in rows("SELECT appliance_id FROM nudges")}
    unnudged_apps = [a for a in appliances() if a["id"] not in nudged_ids]
    unnudged_kw = round(sum(a["power_kw"] for a in unnudged_apps), 1)
    unnudged_hh = {str(a["household_id"]) for a in unnudged_apps}

    available_kw = round(pending_kw + unnudged_kw, 1)
    households_avail = len(pending_hh | unnudged_hh)

    hourly = flex_capacity_hourly()
    return {
        "window": "next_hour",
        "available_kw": available_kw,
        "households_available": households_avail,
        "hourly": hourly,
    }


def flex_capacity():
    return flex_capacity_hourly()
