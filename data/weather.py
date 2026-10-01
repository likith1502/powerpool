"""
Weather service module for PowerPool.
Fetches hourly/15-min weather data from Open-Meteo or generates deterministic weather scenarios for Hyderabad.
"""

import math
import requests
from typing import Dict, List, Any

# Default Hyderabad coordinates
HYDERABAD_LAT = 17.3850
HYDERABAD_LON = 78.4867

SCENARIO_PROFILES = {
    "sunny": {
        "temp_min": 24.0,
        "temp_max": 34.0,
        "peak_irradiance": 850.0,
        "cloud_cover_pct": 10.0,
    },
    "cloudy": {
        "temp_min": 22.0,
        "temp_max": 28.0,
        "peak_irradiance": 420.0,
        "cloud_cover_pct": 75.0,
    },
    "heatwave": {
        "temp_min": 28.0,
        "temp_max": 41.0,
        "peak_irradiance": 920.0,
        "cloud_cover_pct": 5.0,
    },
}


def generate_synthetic_weather(scenario: str = "sunny") -> List[Dict[str, Any]]:
    """
    Generates 96 fifteen-minute slots (24 hours) of synthetic weather.
    """
    profile = SCENARIO_PROFILES.get(scenario.lower(), SCENARIO_PROFILES["sunny"])
    slots = []
    
    temp_min = profile["temp_min"]
    temp_max = profile["temp_max"]
    peak_irr = profile["peak_irradiance"]
    cloud_pct = profile["cloud_cover_pct"]
    
    for slot in range(96):
        hour = slot / 4.0
        time_str = f"{int(hour):02d}:{int((slot % 4) * 15):02d}"
        
        # Temperature curve: minimum at 05:00 (slot 20), maximum at 14:30 (slot 58)
        temp_factor = 0.5 * (1 + math.sin((hour - 9) * math.pi / 12))
        temperature = round(temp_min + temp_factor * (temp_max - temp_min), 1)
        
        # Irradiance curve: zero before 06:00 (slot 24) and after 18:30 (slot 74)
        if 6.0 <= hour <= 18.5:
            # Solar peak around 12:30 (slot 50)
            solar_factor = math.sin((hour - 6.0) * math.pi / 12.5)
            irradiance = round(max(0.0, peak_irr * solar_factor * (1.0 - 0.5 * (cloud_pct / 100.0))), 1)
        else:
            irradiance = 0.0
            
        slots.append({
            "slot": slot,
            "time": time_str,
            "temperature_c": temperature,
            "irradiance_wm2": irradiance,
            "cloud_cover_pct": cloud_pct,
        })
        
    return slots


def get_weather_data(scenario: str = "sunny", use_live_api: bool = False) -> List[Dict[str, Any]]:
    """
    Attempts to fetch live weather from Open-Meteo; falls back to synthetic scenario.
    """
    if not use_live_api:
        return generate_synthetic_weather(scenario)
        
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={HYDERABAD_LAT}&longitude={HYDERABAD_LON}&hourly=temperature_2m,direct_normal_irradiance,cloudcover&timezone=Asia%2FKolkata"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            hourly_temp = data.get("hourly", {}).get("temperature_2m", [])[:24]
            hourly_irr = data.get("hourly", {}).get("direct_normal_irradiance", [])[:24]
            hourly_cloud = data.get("hourly", {}).get("cloudcover", [])[:24]
            
            # Interpolate 24 hours to 96 15-minute slots
            slots = []
            for slot in range(96):
                h = slot // 4
                frac = (slot % 4) / 4.0
                next_h = min(h + 1, 23)
                
                temp = hourly_temp[h] + frac * (hourly_temp[next_h] - hourly_temp[h])
                irr = hourly_irr[h] + frac * (hourly_irr[next_h] - hourly_irr[h])
                cloud = hourly_cloud[h] + frac * (hourly_cloud[next_h] - hourly_cloud[h])
                
                time_str = f"{slot//4:02d}:{ (slot%4)*15:02d}"
                slots.append({
                    "slot": slot,
                    "time": time_str,
                    "temperature_c": round(temp, 1),
                    "irradiance_wm2": round(max(0.0, irr), 1),
                    "cloud_cover_pct": round(cloud, 1)
                })
            return slots
    except Exception:
        pass
        
    return generate_synthetic_weather(scenario)
