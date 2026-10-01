"""
Solar forecasting engine for PowerPool.
Implements physics-based solar generation formula + derating model.
"""

from typing import List, Dict, Any


def forecast_solar_generation(
    weather_slots: List[Dict[str, Any]],
    total_solar_cap_kw: float = 65.0
) -> List[float]:
    """
    Forecasts solar power (kW) for 96 15-minute slots based on irradiance and temperature.
    """
    solar_forecast = []
    
    for slot in weather_slots:
        irr = slot.get("irradiance_wm2", 0.0)
        temp = slot.get("temperature_c", 25.0)
        cloud = slot.get("cloud_cover_pct", 0.0)
        
        if irr <= 0.0 or total_solar_cap_kw <= 0.0:
            solar_forecast.append(0.0)
            continue
            
        # Physics formula: Solar_kW = (Irr / 1000) * Capacity * panel_efficiency_factor * temp_derating
        temp_derating = max(0.80, 1.0 - 0.004 * (temp - 25.0))
        cloud_factor = max(0.20, 1.0 - 0.6 * (cloud / 100.0))
        
        solar_kw = (irr / 1000.0) * total_solar_cap_kw * 0.88 * temp_derating * cloud_factor
        solar_forecast.append(round(max(0.0, solar_kw), 1))
        
    return solar_forecast
