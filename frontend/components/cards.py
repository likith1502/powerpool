"""
Card components for Streamlit frontend.
"""

import streamlit as st


def render_kpi_card(title: str, value: str, subtitle: str = "", icon: str = "⚡", delta: str = None):
    """
    Renders a styled metric card in Streamlit.
    """
    st.markdown(
        f"""
        <div style="background-color: #1E293B; border-radius: 10px; padding: 16px; border: 1px solid #334155; margin-bottom: 10px;">
            <div style="color: #94A3B8; font-size: 0.85rem; font-weight: 500; display: flex; align-items: center; justify-content: space-between;">
                <span>{icon} {title}</span>
                <span style="color: #38BDF8; font-weight: 600;">{delta if delta else ''}</span>
            </div>
            <div style="color: #F8FAFC; font-size: 1.8rem; font-weight: 700; margin-top: 6px; margin-bottom: 2px;">
                {value}
            </div>
            <div style="color: #64748B; font-size: 0.75rem;">
                {subtitle}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
