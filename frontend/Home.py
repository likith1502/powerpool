"""
PowerPool Main Streamlit Landing Page.
Provides overview of the neighbourhood load-flexibility platform with direct navigation.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

st.set_page_config(
    page_title="PowerPool — Smart Feeder Flexibility",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

from frontend.components.sidebar import render_sidebar
from frontend.components.traffic_light import render_traffic_light
from frontend.components.cards import render_kpi_card
from frontend.components.charts import render_forecast_chart
from frontend.api_client import api_client

# Render sidebar controls
config = render_sidebar()
scenario = config["scenario"]

# Title Banner
st.title("⚡ PowerPool")
st.markdown("### **Neighbourhood-Scale Load Flexibility Platform**")
st.markdown(
    """
    PowerPool shifts flexible household electricity loads into solar-rich peak hours to eliminate feeder transformer overload caused by renewable intermittency.
    """
)

# Fetch forecast and KPI data
forecast_res = api_client.get_forecast(scenario=scenario)
slots = forecast_res.get("slots", [])
kpis = api_client.get_kpis(scenario=scenario)
flex = api_client.get_flex_capacity(scenario=scenario)

st.markdown("---")

# Quick Navigation Buttons
col1, col2 = st.columns(2)
with col1:
    st.markdown(
        """
        <div style="background-color: #1E293B; padding: 20px; border-radius: 12px; border: 1px solid #3B82F6; text-align: center;">
            <h3 style="color: #60A5FA; margin-bottom: 8px;">📱 Resident Mobile Web App</h3>
            <p style="color: #94A3B8; font-size: 0.9rem;">View personalized smart energy nudges, earn reward points, and track personal savings.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("Open Resident App →", use_container_width=True, type="primary"):
        st.switch_page("pages/1_Resident.py")

with col2:
    st.markdown(
        """
        <div style="background-color: #1E293B; padding: 20px; border-radius: 12px; border: 1px solid #10B981; text-align: center;">
            <h3 style="color: #34D399; margin-bottom: 8px;">📊 DISCOM Command Center</h3>
            <p style="color: #94A3B8; font-size: 0.9rem;">Monitor feeder transformer stress, before/after load curves, and trigger Demand Response events.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("Open DISCOM Dashboard →", use_container_width=True, type="secondary"):
        st.switch_page("pages/2_DISCOM.py")

st.markdown("---")

# Grid Status Traffic Light
st.markdown("### **Today's Grid Status**")
render_traffic_light(slots)

# System Summary KPIs
st.markdown("### **System Overview**")
c1, c2, c3, c4 = st.columns(4)
with c1:
    render_kpi_card("Peak Reduction", f"{kpis.get('peak_reduction_pct', 19.1)}%", "Load shifted from peak", "⚡")
with c2:
    render_kpi_card("Energy Shifted", f"{kpis.get('kwh_shifted', 42.8)} kWh", "Solar-aligned energy", "🔋")
with c3:
    render_kpi_card("Solar Self-Use", f"{kpis.get('solar_self_use_pct', 72.4)}%", f"+{kpis.get('solar_self_use_change_pct', 14.2)}% improvement", "☀️")
with c4:
    render_kpi_card("Flex Capacity", f"{flex.get('available_kw', 42.0)} kW", f"{flex.get('households_available', 67)} participating homes", "🎛️")

# 24-Hour Feeder Chart
st.markdown("### **24-Hour Feeder Demand & Solar Forecast**")
if slots:
    fig = render_forecast_chart(slots)
    st.plotly_chart(fig, use_container_width=True)
