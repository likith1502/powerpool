"""
Solar Forecasting Module for PowerPool.
Calculates community solar output (kW) based on weather irradiance, cloud cover, and demo scenarios.
"""

import pandas as pd
import numpy as np

def forecast_solar(weather_df: pd.DataFrame, scenario: str = "sunny", peak_community_solar_kw: float = 55.0) -> pd.DataFrame:
    """
    Computes 15-minute solar power generation (kW) for the community based on weather inputs
    and scenario configurations.
    
    Physics logic:
    solar_kw = (irradiance_wm2 / 1000.0) * peak_community_solar_kw * cloud_modifier * scenario_modifier
    
    Scenarios:
    - 'sunny': minimal cloud attenuation, full solar generation (~50-55 kW peak)
    - 'cloudy': heavy cloud cover attenuation (~15-22 kW peak)
    - 'heatwave': high temperature, normal/strong solar generation (~48-52 kW peak)
    """
    df = weather_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Determine slot (0-95)
    df["slot"] = (df["timestamp"].dt.hour * 4) + (df["timestamp"].dt.minute // 15)

    solar_kw_list = []

    for _, row in df.iterrows():
        slot = int(row["slot"])
        irradiance = float(row.get("irradiance_wm2", 0.0))
        cloud = float(row.get("cloud_cover", 0.0))

        # Solar output only during daylight (06:00 to 18:00, slots 24 to 72)
        if 24 <= slot <= 72:
            # Baseline efficiency from irradiance (1000 W/m² = 1.0)
            base_ratio = min(1.0, max(0.0, irradiance / 1000.0))
            
            # Additional curve weighting if irradiance missing
            if base_ratio == 0.0:
                solar_rad = (slot - 24) / 48.0 * np.pi
                base_ratio = max(0.0, np.sin(solar_rad))

            if scenario == "cloudy":
                # Cloudy scenario significantly reduces solar yield (30-40% of clear sky)
                cloud_attenuation = max(0.25, 1.0 - (max(cloud, 65.0) / 100.0) * 0.75)
                scenario_factor = 0.40
            elif scenario == "heatwave":
                # High ambient temp slightly degrades panel efficiency (~5% thermal loss)
                cloud_attenuation = max(0.80, 1.0 - (cloud / 100.0) * 0.20)
                scenario_factor = 0.92
            else: # sunny
                cloud_attenuation = max(0.85, 1.0 - (cloud / 100.0) * 0.15)
                scenario_factor = 1.00

            solar_kw = base_ratio * peak_community_solar_kw * cloud_attenuation * scenario_factor
            solar_kw = max(0.0, round(float(solar_kw), 2))
        else:
            solar_kw = 0.0

        solar_kw_list.append(solar_kw)

    df["solar_kw"] = solar_kw_list
    return df
