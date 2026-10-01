"""
Synthetic household and appliance data generator for PowerPool.
Generates realistic baseline load profiles, rooftop solar capacity, and shiftable appliances for 100 households.
"""

import random
import math
from typing import Dict, List, Any

# Appliance flexibility templates
APPLIANCE_TEMPLATES = [
    {
        "type": "Washing Machine",
        "power_kw": 1.5,
        "duration_slots": 4,  # 1 hour
        "default_start_slot": 76,  # 19:00
        "flex_window_start": 44,   # 11:00
        "flex_window_end": 64,     # 16:00
        "probability": 0.60,
    },
    {
        "type": "EV Charger",
        "power_kw": 3.3,
        "duration_slots": 8,  # 2 hours
        "default_start_slot": 80,  # 20:00
        "flex_window_start": 48,   # 12:00
        "flex_window_end": 68,     # 17:00
        "probability": 0.25,
    },
    {
        "type": "Water Heater (Geyser)",
        "power_kw": 2.0,
        "duration_slots": 3,  # 45 mins
        "default_start_slot": 74,  # 18:30
        "flex_window_start": 40,   # 10:00
        "flex_window_end": 60,     # 15:00
        "probability": 0.50,
    },
    {
        "type": "Dishwasher",
        "power_kw": 1.2,
        "duration_slots": 4,  # 1 hour
        "default_start_slot": 82,  # 20:30
        "flex_window_start": 52,   # 13:00
        "flex_window_end": 68,     # 17:00
        "probability": 0.40,
    },
]


def generate_households(num_households: int = 100, seed: int = 42) -> List[Dict[str, Any]]:
    """
    Generates household metadata including solar installation and appliances.
    """
    random.seed(seed)
    households = []
    
    for hid in range(1, num_households + 1):
        has_solar = random.random() < 0.35  # 35% rooftop solar adoption
        solar_capacity_kw = round(random.uniform(2.5, 5.0), 1) if has_solar else 0.0
        
        appliances = []
        for app in APPLIANCE_TEMPLATES:
            if random.random() < app["probability"]:
                appliances.append({
                    "appliance_id": f"H{hid}_{app['type'].replace(' ', '_')}",
                    "name": app["type"],
                    "power_kw": app["power_kw"],
                    "duration_slots": app["duration_slots"],
                    "default_start_slot": app["default_start_slot"] + random.randint(-2, 2),
                    "flex_window_start": app["flex_window_start"],
                    "flex_window_end": app["flex_window_end"],
                })
                
        households.append({
            "household_id": hid,
            "name": f"Household {hid:02d}",
            "phase": f"Phase {(hid % 3) + 1}",
            "has_solar": has_solar,
            "solar_capacity_kw": solar_capacity_kw,
            "appliances": appliances,
            "points": random.randint(150, 450),
            "kwh_shifted_total": round(random.uniform(8.0, 35.0), 1),
        })
        
    return households


def generate_feeder_baseline(households: List[Dict[str, Any]], weather_slots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes baseline demand, solar generation, and feeder capacity across 96 slots.
    """
    num_households = len(households)
    total_solar_cap = sum(h["solar_capacity_kw"] for h in households)
    
    demand_curve = [0.0] * 96
    solar_curve = [0.0] * 96
    
    # 1. Base load pattern (lighting, refrigeration, background load)
    for slot in range(96):
        hour = slot / 4.0
        temp = weather_slots[slot]["temperature_c"]
        irr = weather_slots[slot]["irradiance_wm2"]
        
        # Base household background (~0.4 - 0.7 kW per household)
        base = 0.45 * num_households
        
        # Morning peak (07:00 - 09:30)
        morning_peak = 35.0 * math.exp(-((hour - 8.25) ** 2) / 2.5)
        
        # Evening peak (18:00 - 22:30)
        evening_peak = 75.0 * math.exp(-((hour - 20.0) ** 2) / 4.0)
        
        # Cooling load (dependent on temperature above 25C)
        cooling_load = max(0.0, (temp - 25.0) * 4.2)
        
        demand_curve[slot] = round(base + morning_peak + evening_peak + cooling_load, 1)
        
        # Solar generation curve (physics formula based on irradiance & panel area)
        if irr > 0 and total_solar_cap > 0:
            # Efficiency ~18%, temperature derating factor
            temp_derating = max(0.85, 1.0 - 0.004 * (temp - 25.0))
            solar_kw = (irr / 1000.0) * total_solar_cap * 0.85 * temp_derating
            solar_curve[slot] = round(max(0.0, solar_kw), 1)
        else:
            solar_curve[slot] = 0.0

    # 2. Superimpose default appliance loads onto evening slots
    appliance_loads = [0.0] * 96
    for h in households:
        for app in h["appliances"]:
            start = app["default_start_slot"]
            dur = app["duration_slots"]
            pwr = app["power_kw"]
            for s in range(start, min(96, start + dur)):
                appliance_loads[s] += pwr

    final_demand = [round(demand_curve[s] + appliance_loads[s], 1) for s in range(96)]
    
    capacity_kw = 170.0  # Feeder capacity rating threshold
    
    result_slots = []
    for s in range(96):
        d_kw = final_demand[s]
        s_kw = solar_curve[s]
        gap_kw = round(d_kw - capacity_kw, 1)
        is_stress = gap_kw > 0
        
        result_slots.append({
            "slot": s,
            "time": weather_slots[s]["time"],
            "demand_kw": d_kw,
            "solar_kw": s_kw,
            "capacity_kw": capacity_kw,
            "gap_kw": gap_kw,
            "is_stress": is_stress,
        })
        
    return {
        "slots": result_slots,
        "total_solar_cap_kw": total_solar_cap,
    }
