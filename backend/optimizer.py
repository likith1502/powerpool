"""Greedy load-shifting scheduler (Section 5 core algorithm).
Pure functions: no DB, no FastAPI -> easy to unit test."""
import math
from dataclasses import dataclass
from typing import Union
from .config import (FEEDER_CAPACITY_KW, PEAK_TARIFF, OFFPEAK_TARIFF,
                     POINTS_PER_KWH, SLOTS_PER_DAY)


@dataclass
class Shift:
    household_id: Union[str, int]
    appliance_id: int
    from_slot: int
    to_slot: int
    duration: int
    power_kw: float

    @property
    def kwh(self) -> float:
        return round(self.power_kw * self.duration * 0.25, 3)

    @property
    def points(self) -> int:
        return max(1, round(self.kwh * POINTS_PER_KWH))

    @property
    def saving_rs(self) -> float:
        return round(self.kwh * (PEAK_TARIFF - OFFPEAK_TARIFF), 2)


def net_load(demand, solar):
    return [d - s for d, s in zip(demand, solar)]


def stress_slots(net, capacity=FEEDER_CAPACITY_KW):
    return {i for i, v in enumerate(net) if v > capacity}


def apply_shift(curve, sh: Shift, weight=1.0):
    """Remove the appliance from its usual block and add it to the new block."""
    for k in range(sh.duration):
        curve[(sh.from_slot + k) % SLOTS_PER_DAY] -= sh.power_kw * weight
        curve[(sh.to_slot + k) % SLOTS_PER_DAY] += sh.power_kw * weight


def greedy_schedule(demand, solar, appliances, capacity=FEEDER_CAPACITY_KW,
                    target_slots=None, target_kw=None, exclude_ids=(), compliance=1.0):
    """
    demand, solar: 96 floats (kW). appliances: dicts with id, household_id, power_kw,
    duration_slots, flexible, earliest_slot, latest_slot, usual_slot.
    target_slots: restrict to a DR window. target_kw: reduce each window slot by this much.
    compliance: expected acceptance rate; we over-book by 1/compliance so that the
    realistic curve (after ~65% accept) still lands under the limit.
    Returns (list[Shift], new_net_curve).
    """
    if compliance is None or isinstance(compliance, bool) or not isinstance(compliance, (int, float)):
        raise TypeError(f"compliance must be a numeric value, got {type(compliance).__name__}")
    if not math.isfinite(compliance):
        raise ValueError(f"compliance must be a finite number, got {compliance}")
    if compliance <= 0.0 or compliance > 1.0:
        raise ValueError(f"compliance must be in the range (0.0, 1.0], got {compliance}")
    compliance = float(compliance)

    net = net_load(demand, solar)
    stress = set(target_slots) if target_slots else stress_slots(net, capacity)
    need = {s: (target_kw if target_kw else net[s] - capacity) / compliance for s in stress}
    limit = {s: net[s] - need[s] for s in stress}
    used, shifts = set(exclude_ids), []

    for slot in sorted(stress, key=lambda s: net[s] - limit[s], reverse=True):
        if net[slot] <= limit[slot]:
            continue
        running = [a for a in appliances
                   if a["flexible"] and a["id"] not in used
                   and a["usual_slot"] <= slot < a["usual_slot"] + a["duration_slots"]]
        running.sort(key=lambda a: a["power_kw"], reverse=True)  # biggest wins first
        for a in running:
            dur = a["duration_slots"]
            best = None
            for t in range(a["earliest_slot"], a["latest_slot"] - dur + 2):
                block = [(t + k) % SLOTS_PER_DAY for k in range(dur)]
                if any(b in stress for b in block):
                    continue
                if any(net[b] + a["power_kw"] > capacity for b in block):
                    continue
                surplus = sum(solar[b] - demand[b] for b in block)
                key = (-surplus, t)
                if best is None or key < best[0]:
                    best = (key, t)
            if best is None:
                continue
            sh = Shift(a["household_id"], a["id"], a["usual_slot"], best[1], dur, a["power_kw"])
            apply_shift(net, sh)
            shifts.append(sh)
            used.add(a["id"])
            if net[slot] <= limit[slot]:
                break
    return shifts, net


def projected_curve(demand, solar, shifts_with_weight):
    """shifts_with_weight: list of (Shift, weight) with weight 1=accepted,
    COMPLIANCE=pending, 0=skipped. Gives the realistic 'after' curve."""
    net = net_load(demand, solar)
    for sh, w in shifts_with_weight:
        apply_shift(net, sh, w)
    return net
