"""
Sidebar configuration and state navigation component.
"""

import streamlit as st
from frontend.components.status_badge import render_status_badge


def render_sidebar():
    """
    Renders global sidebar controls for scenario, language, and household selection.
    """
    st.sidebar.image("https://img.icons8.com/color/96/000000/lightning-bolt.png", width=64)
    st.sidebar.title("PowerPool")
    st.sidebar.caption("Neighbourhood Load Flexibility")

    # Backend / Demo status badge
    with st.sidebar:
        render_status_badge()

    st.sidebar.markdown("---")

    # Scenario Selector
    scenario = st.sidebar.selectbox(
        "Weather Scenario",
        options=["sunny", "cloudy", "heatwave"],
        format_func=lambda x: f"☀️ {x.capitalize()}" if x == "sunny" else (f"☁️ {x.capitalize()}" if x == "cloudy" else f"🔥 {x.capitalize()}"),
        index=0,
        key="global_scenario",
    )

    # Language Selector
    lang_display = {
        "en": "🇬🇧 English",
        "hi": "🇮🇳 हिन्दी (Hindi)",
        "te": "🇮🇳 తెలుగు (Telugu)",
    }
    lang_code = st.sidebar.selectbox(
        "Language",
        options=["en", "hi", "te"],
        format_func=lambda x: lang_display.get(x, x),
        index=0,
        key="global_language",
    )

    # Household ID selector
    household_id = st.sidebar.number_input(
        "Select Household (1-100)",
        min_value=1,
        max_value=100,
        value=1,
        step=1,
        key="global_household_id",
    )

    st.sidebar.markdown("---")
    from frontend.ui_strings import t
    st.sidebar.markdown(f"🔭 {t('sidebar_scenario_explorer_heading', lang_code)}")
    st.sidebar.caption(t("sidebar_scenario_explorer_desc", lang_code))

    return {
        "scenario": scenario,
        "language": lang_code,
        "household_id": household_id,
    }
