"""
PowerPool Resident Mobile Web Application.
Member C Core Deliverable.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

st.set_page_config(
    page_title="PowerPool — Resident App",
    page_icon="📱",
    layout="wide",
)

from frontend.components.sidebar import render_sidebar
from frontend.components.traffic_light import render_traffic_light
from frontend.components.cards import render_kpi_card
from frontend.components.charts import render_forecast_chart
from frontend.components.nudge_card import render_nudge_card
from frontend.api_client import api_client

# Sidebar configuration
config = render_sidebar()
scenario = config["scenario"]
lang = config["language"]
household_id = int(config["household_id"])

# Fetch nudges for current household & scenario
nudges_res = api_client.get_nudges(household_id=household_id, scenario=scenario)
nudges = nudges_res.get("nudges", [])

# Session state initialization per household
if "nudge_statuses" not in st.session_state:
    st.session_state["nudge_statuses"] = {}

h_key = f"h_{household_id}_{scenario}"
if h_key not in st.session_state:
    st.session_state[h_key] = {
        "points": nudges_res.get("points", 245),
        "savings": nudges_res.get("savings_rs", 86.0),
        "kwh": nudges_res.get("kwh_shifted", 12.4),
    }

st.session_state["resident_points"] = st.session_state[h_key]["points"]
st.session_state["resident_savings"] = st.session_state[h_key]["savings"]
st.session_state["resident_kwh"] = st.session_state[h_key]["kwh"]

st.title(f"📱 Resident Portal — Household {household_id:02d}")
st.caption("Smart Energy Assistant for your Neighbourhood Grid")

st.markdown("---")

# 1. Grid Status Traffic Light
st.markdown("#### **Today's Neighbourhood Grid Status**")
forecast_res = api_client.get_forecast(scenario=scenario)
slots = forecast_res.get("slots", [])
render_traffic_light(slots)

# 2. Points Wallet & Impact Summary
st.markdown("#### **Your Wallet & Energy Rewards**")
w1, w2, w3 = st.columns(3)
with w1:
    render_kpi_card("Reward Points", f"{st.session_state['resident_points']} pts", "Redeemable for power bill discounts", "🏆")
with w2:
    render_kpi_card("Estimated Savings", f"₹{int(st.session_state['resident_savings'])}", "Saved by off-peak load shifting", "💰")
with w3:
    render_kpi_card("Energy Shifted", f"{st.session_state['resident_kwh']:.1f} kWh", "Shifted to solar-rich hours", "🌱")

st.markdown("---")

# 3. Recommended Smart Energy Actions (Nudges)
st.markdown("#### **⚡ Recommended Smart Actions**")

# Sync nudge status from session state
for n in nudges:
    nid = n["id"]
    if nid in st.session_state["nudge_statuses"]:
        n["status"] = st.session_state["nudge_statuses"][nid]


def handle_nudge_response(nudge_id: int, accept: bool):
    resp = api_client.respond_to_nudge(nudge_id, accept)
    status_str = "accepted" if accept else "skipped"
    st.session_state["nudge_statuses"][nudge_id] = status_str
    
    if accept:
        pts_add = resp.get("points_added", 15)
        save_add = resp.get("saving_rs", 8.0)
        n_match = next((n for n in nudges if n["id"] == nudge_id), {})
        kwh_add = n_match.get("kwh_shifted", 1.2)
        
        st.session_state[h_key]["points"] += pts_add
        st.session_state[h_key]["savings"] += save_add
        st.session_state[h_key]["kwh"] += kwh_add

        st.session_state["resident_points"] = st.session_state[h_key]["points"]
        st.session_state["resident_savings"] = st.session_state[h_key]["savings"]
        st.session_state["resident_kwh"] = st.session_state[h_key]["kwh"]
        st.success(f"🎉 {resp.get('message', 'Nudge Accepted!')} Earned +{pts_add} points!")
    else:
        st.info("Nudge skipped.")


if nudges:
    for nudge in nudges:
        render_nudge_card(nudge, lang=lang, on_respond_callback=handle_nudge_response)
else:
    st.info("No active load shift recommendations right now. Check back during evening peak hours!")

st.markdown("---")

# 4. Today's Feeder Curve
st.markdown("#### **Feeder Load & Solar Curve**")
if slots:
    fig = render_forecast_chart(slots)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# 5. Leaderboard & Personal Impact
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### **🏆 Neighbourhood Leaderboard**")
    board_res = api_client.get_leaderboard(scenario=scenario)
    board = board_res.get("leaderboard", [])
    
    for item in board:
        rank = item["rank"]
        name = item["name"]
        pts = item["points"]
        kwh = item["kwh_shifted"]
        
        medal = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else f"#{rank}"))
        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; background-color: #1E293B; padding: 10px 16px; border-radius: 8px; margin-bottom: 8px; border-left: 4px solid #38BDF8;">
                <div><span style="font-size: 1.1rem; margin-right: 8px;">{medal}</span> <strong>{name}</strong></div>
                <div><span style="color: #FBBF24; font-weight: 700;">{pts} pts</span> <span style="color: #64748B; font-size: 0.8rem;">({kwh} kWh)</span></div>
            </div>
            """,
            unsafe_allow_html=True
        )

with col_right:
    st.markdown("#### **🌱 Your Personal Environmental Impact**")
    co2_saved = round(st.session_state["resident_kwh"] * 0.7, 1)
    st.markdown(
        f"""
        <div style="background-color: #1E293B; padding: 20px; border-radius: 12px; border: 1px solid #10B981;">
            <div style="font-size: 1.1rem; font-weight: 600; color: #34D399; margin-bottom: 10px;">
                Total Impact to Date
            </div>
            <ul style="color: #CBD5E1; line-height: 1.8; margin-bottom: 0;">
                <li><strong>{st.session_state['resident_kwh']:.1f} kWh</strong> clean solar energy used</li>
                <li><strong>{co2_saved} kg CO₂</strong> avoided from coal grid generation</li>
                <li><strong>₹{int(st.session_state['resident_savings'])}</strong> total power bill savings</li>
                <li><strong>{st.session_state['resident_points']}</strong> total community points earned</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )
