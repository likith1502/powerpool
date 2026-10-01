"""
Grid status traffic light widget for PowerPool.
"""

import streamlit as st
from typing import Dict, Any


def render_traffic_light(forecast_slots: list) -> Dict[str, Any]:
    """
    Computes and displays the Grid Stress Traffic Light (GREEN, AMBER, RED).
    """
    max_gap = max((s["gap_kw"] for s in forecast_slots), default=0.0)
    
    if max_gap <= 0:
        status = "GREEN"
        color = "#22C55E"
        bg_color = "#052E16"
        border_color = "#15803D"
        label = "Solar-Rich / Low Grid Stress"
        description = "Surplus renewable energy available. Great time to run heavy appliances!"
    elif max_gap < 20.0:
        status = "AMBER"
        color = "#F59E0B"
        bg_color = "#451A03"
        border_color = "#B45309"
        label = "Moderate Grid Load"
        description = "Grid approaches transformer threshold. Moderate load shifting recommended."
    else:
        status = "RED"
        color = "#EF4444"
        bg_color = "#450A0A"
        border_color = "#B91C1C"
        label = "Peak Demand / Feeder Stress"
        description = "Feeder overload window detected! Shift non-essential loads immediately to earn rewards."

    st.markdown(
        f"""
        <div style="background-color: {bg_color}; border: 2px solid {border_color}; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px;">
            <div style="display: flex; justify-content: center; align-items: center; gap: 12px; margin-bottom: 8px;">
                <span style="height: 18px; width: 18px; background-color: {color}; border-radius: 50%; display: inline-block; box-shadow: 0 0 12px {color};"></span>
                <span style="color: {color}; font-size: 1.6rem; font-weight: 800; letter-spacing: 1px;">{status}</span>
            </div>
            <div style="color: #F8FAFC; font-size: 1.1rem; font-weight: 600; margin-bottom: 4px;">{label}</div>
            <div style="color: #94A3B8; font-size: 0.85rem;">{description}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    return {"status": status, "color": color, "max_gap": max_gap}
