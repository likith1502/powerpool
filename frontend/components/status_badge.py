"""
Status badge indicator for backend availability and demo mode.
"""

import streamlit as st
from frontend.api_client import api_client


def render_status_badge():
    """
    Renders status indicator (● Live backend / ● Demo mode).
    """
    is_live = api_client.is_backend_available()
    
    if is_live:
        badge_text = "● Live Backend API"
        badge_color = "#22C55E"
        bg_color = "#052E16"
    else:
        badge_text = "● Demo Mode (Fallback)"
        badge_color = "#F59E0B"
        bg_color = "#451A03"

    st.markdown(
        f"""
        <div style="display: inline-block; background-color: {bg_color}; color: {badge_color}; border: 1px solid {badge_color}; border-radius: 16px; padding: 4px 12px; font-size: 0.8rem; font-weight: 600; margin-bottom: 10px;">
            {badge_text}
        </div>
        """,
        unsafe_allow_html=True
    )
