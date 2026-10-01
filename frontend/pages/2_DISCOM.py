"""
PowerPool DISCOM / Community Feeder Flexibility Command Center.
Member C Core Deliverable.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

st.set_page_config(
    page_title="PowerPool — DISCOM Command Center",
    page_icon="📊",
    layout="wide",
)

from frontend.components.sidebar import render_sidebar
from frontend.components.cards import render_kpi_card
from frontend.components.charts import render_before_after_chart, render_gap_chart
from frontend.api_client import api_client

# Sidebar configuration
config = render_sidebar()
scenario = config["scenario"]

st.title("📊 DISCOM Feeder Flexibility Command Center")
st.caption("Hyderabad Neighbourhood Substation • 100 Residential Households • Feeder #HYD-17B")

# Fetch optimization, forecast, KPI, and flex capacity data
opt_res = api_client.optimize(scenario=scenario)
kpis = api_client.get_kpis(scenario=scenario)
flex = api_client.get_flex_capacity(scenario=scenario)

before_slots = opt_res.get("before", [])
after_slots = opt_res.get("after", [])

st.markdown("---")

# 1. Six Key Metric Cards
st.markdown("#### **Feeder Impact KPIs**")
k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:
    render_kpi_card("Peak Reduction", f"{kpis.get('peak_reduction_pct', 19.1)}%", "Feeder load peak shift", "📉")
with k2:
    render_kpi_card("Energy Shifted", f"{kpis.get('kwh_shifted', 42.8)} kWh", "Solar-aligned load", "🔋")
with k3:
    render_kpi_card("Solar Self-Use", f"{kpis.get('solar_self_use_pct', 72.4)}%", f"+{kpis.get('solar_self_use_change_pct', 14.2)}% vs baseline", "☀️")
with k4:
    render_kpi_card("CO₂ Avoided", f"{kpis.get('co2_kg', 30.0)} kg", "Grid carbon reduction", "🌱")
with k5:
    render_kpi_card("Active Homes", f"{kpis.get('participants', 67)} / {kpis.get('households', 100)}", "Participation rate 67%", "🏠")
with k6:
    render_kpi_card("Flex Capacity", f"{flex.get('available_kw', 42.0)} kW", "Available for DR dispatch", "🎛️")

st.markdown("---")

# 2. Main Central Before / After Load Curve Visual
st.markdown("#### **Central Feeder Load Curve — Before vs After PowerPool**")
if before_slots and after_slots:
    fig_ba = render_before_after_chart(
        before_slots,
        after_slots,
        peak_reduction_pct=kpis.get("peak_reduction_pct", 19.1)
    )
    st.plotly_chart(fig_ba, use_container_width=True)

st.markdown("---")

# 3. Demand Response Control & Transformer Risk Indicator
c_left, c_right = st.columns([2, 1])

with c_left:
    st.markdown("#### **🎛️ Automated Demand Response (DR) Trigger**")
    st.markdown("Dispatch automated load-shifting nudges to all participating households during critical grid stress windows.")
    
    col_dr1, col_dr2 = st.columns(2)
    with col_dr1:
        dr_start = st.selectbox("DR Start Slot / Time", options=[74, 76, 78, 80], format_func=lambda s: f"Slot {s} ({s//4:02d}:{(s%4)*15:02d})", index=0)
    with col_dr2:
        dr_end = st.selectbox("DR End Slot / Time", options=[84, 86, 88, 90], format_func=lambda s: f"Slot {s} ({s//4:02d}:{(s%4)*15:02d})", index=2)
        
    if st.button("🚀 Trigger Instant Demand Response Event", type="primary", use_container_width=True):
        dr_resp = api_client.trigger_dr_event(start_slot=dr_start, end_slot=dr_end, target_kw=170.0)
        st.success(f"✅ {dr_resp.get('message')}")
        st.balloons()

with c_right:
    st.markdown("#### **⚠️ Transformer Risk Status**")
    peak_after = opt_res.get("peak_after_kw", 158.7)
    capacity = 170.0
    risk_ratio = peak_after / capacity
    
    if risk_ratio < 0.85:
        risk_level = "LOW"
        risk_color = "#22C55E"
        risk_bg = "#052E16"
    elif risk_ratio <= 1.00:
        risk_level = "MEDIUM"
        risk_color = "#F59E0B"
        risk_bg = "#451A03"
    else:
        risk_level = "HIGH"
        risk_color = "#EF4444"
        risk_bg = "#450A0A"

    st.markdown(
        f"""
        <div style="background-color: {risk_bg}; border: 2px solid {risk_color}; border-radius: 12px; padding: 20px; text-align: center;">
            <div style="color: #94A3B8; font-size: 0.85rem; margin-bottom: 6px;">TRANSFORMER OVERLOAD RISK</div>
            <div style="color: {risk_color}; font-size: 2.2rem; font-weight: 800;">{risk_level}</div>
            <div style="color: #CBD5E1; font-size: 0.85rem; margin-top: 6px;">Peak Load: {peak_after} kW / {capacity} kW</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")

# 4. Secondary Demand Gap Chart & Stress Windows
g_left, g_right = st.columns([2, 1])

with g_left:
    st.markdown("#### **Feeder Capacity Margin / Overload Gap**")
    if after_slots:
        fig_gap = render_gap_chart(after_slots)
        st.plotly_chart(fig_gap, use_container_width=True)

with g_right:
    st.markdown("#### **Critical Feeder Stress Windows**")
    stress_slots = [s for s in before_slots if s.get("is_stress")]
    if stress_slots:
        for s in stress_slots[::4]:
            t_str = s["time"]
            gap = s["gap_kw"]
            st.markdown(
                f"""
                <div style="display: flex; justify-content: space-between; background-color: #1E293B; padding: 10px; border-radius: 6px; margin-bottom: 6px; border-left: 4px solid #EF4444;">
                    <span>🕒 {t_str}</span>
                    <span style="color: #EF4444; font-weight: 700;">+{gap} kW Overload</span>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.success("No critical transformer overload stress windows detected today!")
