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

# ── Optimization: only re-run when scenario changes or button pressed ──────────
# Root-cause fix: auto-running optimize on EVERY page load was wiping resident
# reward history via the (now-removed) "UPDATE households SET points = 0" in
# run_optimize, AND was triggering a full re-optimisation on every navigation
# click which reset nudge state. Optimization now runs only on explicit request.

_OPT_KEY = "discom_opt_result"
_OPT_SCENARIO_KEY = "discom_opt_scenario"

# Detect scenario change → clear cached result so the user sees fresh state
if st.session_state.get(_OPT_SCENARIO_KEY) != scenario:
    st.session_state.pop(_OPT_KEY, None)
    st.session_state[_OPT_SCENARIO_KEY] = scenario

# Fetch forecast and current KPIs (read-only — no optimize call here)
kpis = api_client.get_kpis(scenario=scenario)
flex = api_client.get_flex_capacity(scenario=scenario)
forecast_res = api_client.get_forecast(scenario=scenario)
forecast_slots = forecast_res.get("slots", [])

st.markdown("---")

# 1. Six Key Metric Cards
st.markdown("#### **Feeder Impact KPIs**")
k1, k2, k3, k4, k5, k6 = st.columns(6)

# Calculate participation rate from actual data (not hardcoded)
participants = kpis.get("participants", 0)
total_hh = kpis.get("households", 100)
participation_pct = round(100 * participants / total_hh, 0) if total_hh > 0 else 0

with k1:
    render_kpi_card("Peak Reduction", f"{kpis.get('peak_reduction_pct', 0.0)}%", "Feeder load peak shift", "📉")
with k2:
    render_kpi_card("Energy Shifted", f"{kpis.get('kwh_shifted', 0.0)} kWh", "Solar-aligned load", "🔋")
with k3:
    render_kpi_card("Solar Self-Use", f"{kpis.get('solar_self_use_pct', 0.0)}%",
                    f"+{kpis.get('solar_self_use_change_pct', 0.0)}% vs baseline", "☀️")
with k4:
    render_kpi_card("CO₂ Avoided", f"{kpis.get('co2_kg', 0.0)} kg", "Grid carbon reduction", "🌱")
with k5:
    render_kpi_card(
        "Active Homes",
        f"{participants} / {total_hh}",
        f"Participation rate {int(participation_pct)}%",
        "🏠"
    )
with k6:
    render_kpi_card("Flex Capacity", f"{flex.get('available_kw', 0.0)} kW",
                    f"{flex.get('households_available', 0)} homes with pending nudges", "🎛️")

st.markdown("---")

# 2. Optimizer Section
st.markdown("#### **Central Feeder Load Curve — Before vs After PowerPool**")

opt_col, _ = st.columns([3, 1])
with opt_col:
    run_btn = st.button(
        "▶ Run Load-Shift Optimizer",
        type="primary",
        use_container_width=True,
        help="Clears and re-generates load-shift nudges using the greedy scheduler. "
             "Scenario: " + scenario.capitalize()
    )
    if run_btn:
        with st.spinner("Running greedy load-shift optimizer…"):
            result = api_client.optimize(scenario=scenario)
            st.session_state[_OPT_KEY] = result
            st.session_state[_OPT_SCENARIO_KEY] = scenario
        st.success(
            f"✅ Optimizer complete — {result.get('nudges_created', 0)} nudges created. "
            f"Peak: {result.get('peak_before_kw', 0):.1f} kW → {result.get('peak_after_kw', 0):.1f} kW "
            f"({result.get('peak_reduction_pct', 0):.1f}% reduction)"
        )
        # Refresh KPIs and flex after optimization
        kpis = api_client.get_kpis(scenario=scenario)
        flex = api_client.get_flex_capacity(scenario=scenario)
        st.rerun()

opt_res = st.session_state.get(_OPT_KEY)

if opt_res:
    before_slots = opt_res.get("before", [])
    after_slots = opt_res.get("after", [])
    if before_slots and after_slots:
        fig_ba = render_before_after_chart(
            before_slots,
            after_slots,
            peak_reduction_pct=opt_res.get("peak_reduction_pct", kpis.get("peak_reduction_pct", 0.0))
        )
        st.plotly_chart(fig_ba, use_container_width=True)
    else:
        st.info("No optimization result available yet. Click 'Run Load-Shift Optimizer' above.")
else:
    # Show forecast-only view before first optimize run
    if forecast_slots:
        st.info(
            "📋 **Forecast only** — Run the optimizer to see the before/after load curve comparison. "
            f"Data source: `{forecast_slots[0].get('data_source', 'mock')}` "
            f"| Scenario: **{scenario.capitalize()}**"
        )
        from frontend.components.charts import render_forecast_chart
        fig_fc = render_forecast_chart(forecast_slots)
        st.plotly_chart(fig_fc, use_container_width=True)
    else:
        st.warning("⚠️ Forecast data unavailable. Check that the backend is running.")

st.markdown("---")

# 3. Demand Response Control & Transformer Risk Indicator
c_left, c_right = st.columns([2, 1])

with c_left:
    st.markdown("#### **🎛️ Automated Demand Response (DR) Trigger**")
    st.markdown("Dispatch automated load-shifting nudges to all participating households during critical grid stress windows.")

    col_dr1, col_dr2 = st.columns(2)
    with col_dr1:
        dr_start = st.selectbox("DR Start Slot / Time", options=[74, 76, 78, 80],
                                format_func=lambda s: f"Slot {s} ({s//4:02d}:{(s%4)*15:02d})", index=0)
    with col_dr2:
        dr_end = st.selectbox("DR End Slot / Time", options=[84, 86, 88, 90],
                              format_func=lambda s: f"Slot {s} ({s//4:02d}:{(s%4)*15:02d})", index=2)

    if st.button("🚀 Trigger Instant Demand Response Event", type="primary", use_container_width=True):
        dr_resp = api_client.trigger_dr_event(
            start_slot=dr_start, end_slot=dr_end, target_kw=170.0, scenario=scenario
        )
        nudges_created = dr_resp.get("nudges_created", 0)
        peak_after = dr_resp.get("peak_after_kw", 0)
        kw_reduced = dr_resp.get("kw_reduced_expected", 0)
        st.success(
            f"✅ DR event dispatched — {nudges_created} additional nudges created. "
            f"Expected reduction: {kw_reduced:.1f} kW. Peak after DR: {peak_after:.1f} kW"
        )
        st.balloons()
        # Update opt_res with DR after-curve if available
        if dr_resp.get("after"):
            if opt_res:
                opt_res["after"] = dr_resp["after"]
                opt_res["peak_after_kw"] = peak_after
            st.session_state[_OPT_KEY] = opt_res
        # Refresh KPIs
        kpis = api_client.get_kpis(scenario=scenario)
        flex = api_client.get_flex_capacity(scenario=scenario)

with c_right:
    st.markdown("#### **⚠️ Transformer Risk Status**")
    # Use post-optimization peak if available, otherwise use pre-optimization peak
    if opt_res:
        peak_display = opt_res.get("peak_after_kw", kpis.get("peak_after_kw", 0.0))
    else:
        peak_display = kpis.get("peak_before_kw", 0.0)
    capacity = 170.0
    risk_ratio = peak_display / capacity if capacity > 0 else 0

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

    peak_label = "After Optimization" if opt_res else "Before Optimization"
    st.markdown(
        f"""
        <div style="background-color: {risk_bg}; border: 2px solid {risk_color}; border-radius: 12px; padding: 20px; text-align: center;">
            <div style="color: #94A3B8; font-size: 0.85rem; margin-bottom: 6px;">TRANSFORMER OVERLOAD RISK</div>
            <div style="color: {risk_color}; font-size: 2.2rem; font-weight: 800;">{risk_level}</div>
            <div style="color: #CBD5E1; font-size: 0.85rem; margin-top: 6px;">{peak_label}: {peak_display:.1f} kW / {capacity:.0f} kW</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")

# 4. Secondary Demand Gap Chart & Stress Windows
g_left, g_right = st.columns([2, 1])

with g_left:
    st.markdown("#### **Feeder Capacity Margin / Overload Gap**")
    slots_for_gap = (opt_res.get("after", []) if opt_res else forecast_slots)
    if slots_for_gap:
        fig_gap = render_gap_chart(slots_for_gap)
        st.plotly_chart(fig_gap, use_container_width=True)

with g_right:
    st.markdown("#### **Critical Feeder Stress Windows**")
    slots_for_stress = (opt_res.get("before", []) if opt_res else forecast_slots)
    stress_slots_list = [s for s in slots_for_stress if s.get("is_stress")]
    if stress_slots_list:
        for s in stress_slots_list[::4]:
            t_str = s["time"]
            gap = s.get("gap_kw", 0)
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
        if opt_res:
            st.success("✅ No critical transformer overload stress windows after optimization!")
        else:
            st.info("Run the optimizer to identify and eliminate stress windows.")
