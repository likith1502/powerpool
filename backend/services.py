"""Business logic that touches the DB: nudges, points, KPIs, DR, flex capacity."""
from .db import get_conn, rows
from .config import (FEEDER_CAPACITY_KW, COMPLIANCE, CO2_PER_KWH, SLOTS_PER_DAY,
                     slot_to_time)
from .optimizer import Shift, greedy_schedule, projected_curve, net_load
from .translations import nudge_text

WEIGHT = {"accepted": 1.0, "pending": COMPLIANCE, "skipped": 0.0}


# ---------- loading ----------
def load_forecast(date=None):
    sql = "SELECT * FROM forecast"
    params = ()
    if date:
        sql += " WHERE timestamp LIKE ?"
        params = (f"{date}%",)
    data = rows(sql + " ORDER BY timestamp", params)[:SLOTS_PER_DAY]
    if len(data) < SLOTS_PER_DAY:
        raise ValueError("Forecast table has fewer than 96 slots. Run seed or Member A's pipeline.")
    return data


def curves(date=None):
    f = load_forecast(date)
    return [r["demand_kw"] for r in f], [r["solar_kw"] for r in f]


def appliances():
    return rows("SELECT * FROM appliances WHERE flexible = 1")


def shifts_from_db():
    out = []
    for n in rows("SELECT n.*, a.power_kw, a.duration_slots FROM nudges n "
                  "JOIN appliances a ON a.id = n.appliance_id"):
        sh = Shift(n["household_id"], n["appliance_id"], n["from_slot"], n["to_slot"],
                   n["duration_slots"], n["power_kw"])
        out.append((sh, WEIGHT[n["status"]]))
    return out


def to_points(curve):
    return [{"slot": i, "time": slot_to_time(i), "demand_kw": round(v, 2)}
            for i, v in enumerate(curve)]


def after_curve(date=None):
    d, s = curves(date)
    return net_load(d, s), projected_curve(d, s, shifts_from_db())


# ---------- writing nudges ----------
def save_shifts(shifts, source="optimize"):
    with get_conn() as c:
        for sh in shifts:
            c.execute("INSERT INTO nudges(household_id, appliance_id, from_slot, to_slot,"
                      " kwh_shifted, points, saving_rs, status, source)"
                      " VALUES (?,?,?,?,?,?,?,'pending',?)",
                      (sh.household_id, sh.appliance_id, sh.from_slot, sh.to_slot,
                       sh.kwh, sh.points, sh.saving_rs, source))


def run_optimize(date=None):
    with get_conn() as c:
        c.execute("DELETE FROM nudges")
        c.execute("UPDATE households SET points = 0")
    d, s = curves(date)
    shifts, _ = greedy_schedule(d, s, appliances(), compliance=COMPLIANCE)
    save_shifts(shifts)
    before, after = after_curve(date)
    pb, pa = max(before), max(after)
    return {"before": to_points(before), "after": to_points(after),
            "nudges_created": len(shifts), "peak_before_kw": round(pb, 2),
            "peak_after_kw": round(pa, 2),
            "peak_reduction_pct": round(100 * (pb - pa) / pb, 1) if pb else 0.0}


def run_dr_event(start, end, target_kw, date=None):
    d, s = curves(date)
    window = list(range(start, end + 1)) if start <= end else \
        list(range(start, 96)) + list(range(0, end + 1))
    _, current = after_curve(date)
    already = {n["appliance_id"] for n in rows("SELECT appliance_id FROM nudges")}
    # schedule against the CURRENT curve so DR adds on top of earlier nudges
    solar_adj = [di - ci for di, ci in zip(d, current)]  # so that d - solar_adj = current
    shifts, _ = greedy_schedule(d, solar_adj, appliances(), target_slots=window,
                                target_kw=target_kw, exclude_ids=already,
                                compliance=COMPLIANCE)
    save_shifts(shifts, source="dr")
    _, after = after_curve(date)
    reduced = max(current[w] for w in window) - max(after[w] for w in window)
    return {"nudges_created": len(shifts), "kw_reduced_expected": round(reduced, 2),
            "after": to_points(after)}


# ---------- residents ----------
def nudges_for(household_id):
    hh = rows("SELECT language FROM households WHERE id = ?", (household_id,))
    lang = hh[0]["language"] if hh else "en"
    out = []
    for n in rows("SELECT n.*, a.name AS appliance FROM nudges n JOIN appliances a "
                  "ON a.id = n.appliance_id WHERE n.household_id = ? ORDER BY n.to_slot",
                  (household_id,)):
        n["from_time"], n["to_time"] = slot_to_time(n["from_slot"]), slot_to_time(n["to_slot"])
        n["message"] = nudge_text(n["appliance"], n["from_slot"], n["to_slot"],
                                  n["points"], n["saving_rs"], lang)
        out.append(n)
    return out


def respond(nudge_id, accept):
    with get_conn() as c:
        n = c.execute("SELECT * FROM nudges WHERE id = ?", (nudge_id,)).fetchone()
        if n is None:
            return None
        new = "accepted" if accept else "skipped"
        if n["status"] != "accepted" and new == "accepted":
            c.execute("UPDATE households SET points = points + ? WHERE id = ?",
                      (n["points"], n["household_id"]))
        if n["status"] == "accepted" and new == "skipped":
            c.execute("UPDATE households SET points = points - ? WHERE id = ?",
                      (n["points"], n["household_id"]))
        c.execute("UPDATE nudges SET status = ? WHERE id = ?", (new, nudge_id))
        pts = c.execute("SELECT points FROM households WHERE id = ?",
                        (n["household_id"],)).fetchone()["points"]
    return {"nudge_id": nudge_id, "status": new, "household_points": pts}


def leaderboard(limit=10):
    data = rows("SELECT id AS household_id, name, block, points FROM households "
                "ORDER BY points DESC, id LIMIT ?", (limit,))
    for i, r in enumerate(data, 1):
        r["rank"] = i
    return data


# ---------- DISCOM ----------
def solar_self_use(demand_net, solar):
    """% of solar consumed locally. gross = net + solar; used = min(gross, solar)."""
    total = sum(solar)
    if total == 0:
        return 0.0
    used = sum(min(n + s, s) for n, s in zip(demand_net, solar))
    return round(100 * used / total, 1)


def kpis(date=None):
    _, s = curves(date)
    before, after = after_curve(date)
    weighted = shifts_from_db()
    kwh = sum(sh.kwh * w for sh, w in weighted)
    rs = sum(sh.saving_rs * w for sh, w in weighted)
    pb, pa = max(before), max(after)
    participants = rows("SELECT COUNT(DISTINCT household_id) c FROM nudges "
                        "WHERE status = 'accepted'")[0]["c"]
    total = rows("SELECT COUNT(*) c FROM households")[0]["c"]
    load_ratio = pa / FEEDER_CAPACITY_KW
    risk = "HIGH" if load_ratio > 1.05 else "MEDIUM" if load_ratio > 0.95 else "LOW"
    return {"peak_before_kw": round(pb, 2), "peak_after_kw": round(pa, 2),
            "peak_reduction_pct": round(100 * (pb - pa) / pb, 1) if pb else 0.0,
            "kwh_shifted": round(kwh, 2), "rs_saved": round(rs, 2),
            "co2_kg": round(kwh * CO2_PER_KWH, 2),
            "solar_self_use_pct_before": solar_self_use(before, s),
            "solar_self_use_pct": solar_self_use(after, s),
            "participants": participants, "total_households": total,
            "transformer_risk": risk}


def flex_capacity():
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
