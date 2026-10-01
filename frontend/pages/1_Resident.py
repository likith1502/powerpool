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
from frontend.ui_strings import t

# Sidebar configuration
config = render_sidebar()
scenario = config["scenario"]
lang = config["language"]
household_id = int(config["household_id"])

# ── Wallet: load from API, reset when household changes ───────────────────────
# Root-cause fix: the wallet was initialized to a hardcoded 245 pts that never
# reflected the actual database state. Now we load from the /households endpoint
# and reset when the selected household changes.
_WALLET_HH_KEY = "wallet_household_id"
_WALLET_PTS_KEY = "resident_points"
_WALLET_SAV_KEY = "resident_savings"
_WALLET_KWH_KEY = "resident_kwh"

def _refresh_wallet(hh_id: int):
    """Load wallet data from the API for the given household."""
    hh_norm = f"HH{hh_id:03d}"
    households = api_client.get_forecast(scenario=scenario)  # warm up connection
    # Fetch all households and find the matching one
    try:
        import os
        import requests
        from frontend.api_client import API_URL, TIMEOUT_SEC
        resp = requests.get(f"{API_URL}/households", timeout=TIMEOUT_SEC)
        if resp.status_code == 200:
            hh_list = resp.json()
            for hh in hh_list:
                if str(hh.get("id", "")) == hh_norm:
                    pts = int(hh.get("points", 0))
                    # savings and kwh_shifted are derived from accepted nudges
                    # fetch the household's accepted nudges for accurate totals
                    nudge_resp = requests.get(
                        f"{API_URL}/nudges/{hh_norm}", timeout=TIMEOUT_SEC
                    )
                    accepted = []
                    if nudge_resp.status_code == 200:
                        nd = nudge_resp.json()
                        accepted = [n for n in nd.get("nudges", []) if n["status"] == "accepted"]
                    sav = round(sum(n.get("saving_rs", 0.0) for n in accepted), 2)
                    kwh = round(sum(n.get("kwh_shifted", 0.0) for n in accepted), 2)
                    return pts, sav, kwh
    except Exception:
        pass
    # Fallback: 0 points, no prior activity (never fabricate values)
    return 0, 0.0, 0.0


# Reset session wallet when household changes
if st.session_state.get(_WALLET_HH_KEY) != household_id:
    pts, sav, kwh = _refresh_wallet(household_id)
    st.session_state[_WALLET_PTS_KEY] = pts
    st.session_state[_WALLET_SAV_KEY] = sav
    st.session_state[_WALLET_KWH_KEY] = kwh
    st.session_state[_WALLET_HH_KEY] = household_id
    st.session_state["nudge_statuses"] = {}

if "nudge_statuses" not in st.session_state:
    st.session_state["nudge_statuses"] = {}

# Page title (translated)
st.title(f"{t('resident_page_title', lang)} — Household {household_id:02d}")
st.caption(t("resident_page_subtitle", lang))

st.markdown("---")

# 1. Grid Status Traffic Light
st.markdown(t("resident_grid_status_heading", lang))
forecast_res = api_client.get_forecast(scenario=scenario)
slots = forecast_res.get("slots", [])
render_traffic_light(slots)

# 2. Points Wallet & Impact Summary
st.markdown(t("resident_wallet_heading", lang))
w1, w2, w3 = st.columns(3)
with w1:
    render_kpi_card(
        t("resident_wallet_points_title", lang),
        f"{st.session_state[_WALLET_PTS_KEY]} pts",
        t("resident_wallet_points_subtitle", lang),
        "🏆"
    )
with w2:
    render_kpi_card(
        t("resident_wallet_savings_title", lang),
        f"₹{int(st.session_state[_WALLET_SAV_KEY])}",
        t("resident_wallet_savings_subtitle", lang),
        "💰"
    )
with w3:
    render_kpi_card(
        t("resident_wallet_kwh_title", lang),
        f"{st.session_state[_WALLET_KWH_KEY]:.1f} kWh",
        t("resident_wallet_kwh_subtitle", lang),
        "🌱"
    )

st.markdown("---")

# 3. Recommended Smart Energy Actions (Nudges)
st.markdown(t("resident_smart_actions_heading", lang))
nudges_res = api_client.get_nudges(household_id=household_id, scenario=scenario)
nudges = nudges_res.get("nudges", [])

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
        pts_added = resp.get("points_added", 0)
        saving_added = resp.get("saving_rs", 0.0)
        # Find the kwh for this nudge from the current nudge list
        kwh_added = next(
            (n.get("kwh_shifted", 0.0) for n in nudges if n["id"] == nudge_id), 0.0
        )
        st.session_state[_WALLET_PTS_KEY] += pts_added
        st.session_state[_WALLET_SAV_KEY] = round(
            st.session_state[_WALLET_SAV_KEY] + saving_added, 2
        )
        st.session_state[_WALLET_KWH_KEY] = round(
            st.session_state[_WALLET_KWH_KEY] + kwh_added, 2
        )
        accept_msg = resp.get("message", "Nudge Accepted!")
        full_msg = t("nudge_accept_success", lang).format(msg=accept_msg, pts=pts_added)
        st.success(full_msg)
    else:
        st.info(t("nudge_skip_info", lang))


if nudges:
    for nudge in nudges:
        render_nudge_card(nudge, lang=lang, on_respond_callback=handle_nudge_response)
else:
    st.info(t("resident_no_nudges_msg", lang))

st.markdown("---")

# 4. Today's Feeder Curve
st.markdown(t("resident_feeder_curve_heading", lang))
if slots:
    # Show data source badge
    data_src = slots[0].get("data_source", "mock") if slots else "mock"
    src_label = t("data_source_model", lang) if data_src == "model" else t("data_source_mock", lang)
    st.caption(f"Scenario: **{scenario.capitalize()}** | {src_label}")
    fig = render_forecast_chart(slots)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# 5. Leaderboard & Personal Impact
col_left, col_right = st.columns(2)

with col_left:
    st.markdown(t("resident_leaderboard_heading", lang))
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
    st.markdown(t("resident_impact_heading", lang))
    co2_saved = round(st.session_state[_WALLET_KWH_KEY] * 0.71, 1)  # CO2 factor: 0.71 kg/kWh (CEA)
    total_label = t("resident_impact_total_label", lang)
    solar_label = t("resident_impact_solar_kwh", lang)
    co2_label = t("resident_impact_co2", lang)
    savings_label = t("resident_impact_savings", lang)
    points_label = t("resident_impact_points", lang)
    st.markdown(
        f"""
        <div style="background-color: #1E293B; padding: 20px; border-radius: 12px; border: 1px solid #10B981;">
            <div style="font-size: 1.1rem; font-weight: 600; color: #34D399; margin-bottom: 10px;">
                {total_label}
            </div>
            <ul style="color: #CBD5E1; line-height: 1.8; margin-bottom: 0;">
                <li><strong>{st.session_state[_WALLET_KWH_KEY]:.1f} kWh</strong> {solar_label}</li>
                <li><strong>{co2_saved} kg CO₂</strong> {co2_label}</li>
                <li><strong>₹{int(st.session_state[_WALLET_SAV_KEY])}</strong> {savings_label}</li>
                <li><strong>{st.session_state[_WALLET_PTS_KEY]}</strong> {points_label}</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )
