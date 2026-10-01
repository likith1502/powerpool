"""
Greedy load-shifting optimization algorithm for PowerPool.
Shifts peak demand from stress slots to solar-rich hours based on household appliance flex windows.
"""

from typing import Dict, List, Any
from backend.nudges import build_multilingual_messages, calculate_nudge_rewards


def run_load_shifting_optimization(
    scenario_data: Dict[str, Any],
    compliance_rate: float = 0.65
) -> Dict[str, Any]:
    """
    Executes greedy load shifting from peak stress slots into solar surplus slots.
    """
    forecast = scenario_data["forecast"]
    households = scenario_data["households"]
    
    # Deep copy original demand curve
    before_slots = [dict(s) for s in forecast]
    after_demand = [s["demand_kw"] for s in before_slots]
    solar_kw = [s["solar_kw"] for s in before_slots]
    capacity_kw = before_slots[0]["capacity_kw"]
    
    # Collect all flexible appliance shifts
    nudge_list = []
    nudge_counter = 101
    total_kwh_shifted = 0.0
    
    # Identify stress slots sorted by highest demand gap
    stress_slots = sorted(
        [s for s in before_slots if s["gap_kw"] > 0],
        key=lambda x: x["gap_kw"],
        reverse=True
    )
    
    # Map households appliances for easy access
    for h in households:
        hid = h["household_id"]
        for app in h["appliances"]:
            start_slot = app["default_start_slot"]
            dur = app["duration_slots"]
            pwr = app["power_kw"]
            
            # Check if this appliance runs in a stress slot
            runs_in_stress = any(
                start_slot <= s["slot"] < start_slot + dur
                for s in stress_slots
            )
            
            if runs_in_stress:
                # Find optimal candidate window during solar surplus hours (11:00 - 15:30 -> slots 44 to 62)
                best_target_slot = app["flex_window_start"]
                min_target_demand = 9999.0
                
                for candidate in range(app["flex_window_start"], app["flex_window_end"]):
                    cand_load = after_demand[candidate] - solar_kw[candidate]
                    if cand_load < min_target_demand:
                        min_target_demand = cand_load
                        best_target_slot = candidate
                        
                # Compute load shift amount (kWh)
                app_kwh = round(pwr * (dur * 15 / 60.0), 2)
                
                # Apply simulated compliance rate filter
                # (Only ~65% of households accept nudge)
                if (hid + nudge_counter) % 100 < (compliance_rate * 100):
                    # Reduce demand at peak stress slots
                    for s in range(start_slot, min(96, start_slot + dur)):
                        after_demand[s] = max(0.0, after_demand[s] - pwr)
                    # Add demand at solar surplus target slots
                    for s in range(best_target_slot, min(96, best_target_slot + dur)):
                        after_demand[s] += pwr
                        
                    total_kwh_shifted += app_kwh
                    
                    from_time = f"{start_slot//4:02d}:{(start_slot%4)*15:02d}"
                    end_target = best_target_slot + dur
                    to_time = f"{best_target_slot//4:02d}:{(best_target_slot%4)*15:02d}–{end_target//4:02d}:{(end_target%4)*15:02d}"
                    
                    rewards = calculate_nudge_rewards(app_kwh)
                    msgs = build_multilingual_messages(app["name"], from_time, to_time, rewards["points"], rewards["saving_rs"])
                    
                    nudge_list.append({
                        "id": nudge_counter,
                        "household_id": hid,
                        "appliance": app["name"],
                        "from_time": from_time,
                        "to_time": to_time,
                        "kwh_shifted": app_kwh,
                        "points": rewards["points"],
                        "saving_rs": rewards["saving_rs"],
                        "message": msgs["en"],
                        "message_hi": msgs["hi"],
                        "message_te": msgs["te"],
                        "status": "pending",
                    })
                    nudge_counter += 1

    # Reconstruct after slots
    after_slots = []
    for s in range(96):
        d_kw = round(after_demand[s], 1)
        s_kw = solar_kw[s]
        gap_kw = round(d_kw - capacity_kw, 1)
        after_slots.append({
            "slot": s,
            "time": before_slots[s]["time"],
            "demand_kw": d_kw,
            "solar_kw": s_kw,
            "capacity_kw": capacity_kw,
            "gap_kw": gap_kw,
            "is_stress": gap_kw > 0,
        })

    peak_before = max(s["demand_kw"] for s in before_slots)
    peak_after = max(s["demand_kw"] for s in after_slots)
    peak_reduction_pct = round(((peak_before - peak_after) / peak_before) * 100.0, 1) if peak_before > 0 else 0.0
    
    return {
        "before": before_slots,
        "after": after_slots,
        "nudges": nudge_list,
        "nudges_created": len(nudge_list),
        "peak_before_kw": peak_before,
        "peak_after_kw": peak_after,
        "peak_reduction_pct": peak_reduction_pct,
        "kwh_shifted": round(total_kwh_shifted, 1),
    }
