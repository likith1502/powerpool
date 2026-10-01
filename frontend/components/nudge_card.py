"""
Interactive Nudge Card Component for Resident Streamlit App.
All user-facing labels are translated via frontend.ui_strings.t().
"""

import streamlit as st
from typing import Dict, Any, Callable
from frontend.ui_strings import t


def render_nudge_card(
    nudge: Dict[str, Any],
    lang: str = "en",
    on_respond_callback: Callable[[int, bool], None] = None
):
    """
    Renders an interactive smart energy nudge card with Accept/Skip buttons.

    The message body and all UI labels are rendered in the requested language.
    Supported languages: 'en', 'hi', 'te'. Falls back to English for any missing key.
    """
    nid = nudge["id"]
    status = nudge.get("status", "pending")
    appliance = nudge.get("appliance", "Appliance")
    from_time = nudge.get("from_time", "19:00")
    to_time = nudge.get("to_time", "13:00")
    kwh = nudge.get("kwh_shifted", 1.2)
    pts = nudge.get("points", 15)
    saving = nudge.get("saving_rs", 8.0)

    # ── Select localized message body ─────────────────────────────────────────
    # The backend pre-generates message, message_hi, and message_te in services.py.
    # The nudge card picks the right one based on the sidebar language selection.
    if lang == "hi" and nudge.get("message_hi"):
        msg = nudge["message_hi"]
    elif lang == "te" and nudge.get("message_te"):
        msg = nudge["message_te"]
    else:
        # English (or fallback for missing translation)
        msg = nudge.get("message", f"Run your {appliance} at {to_time}.")

    # ── Status badge and border colour ────────────────────────────────────────
    if status == "accepted":
        card_border = "#10B981"
        badge_text = t("nudge_accepted_badge", lang)
        badge_color = "#10B981"
    elif status == "skipped":
        card_border = "#64748B"
        badge_text = t("nudge_skipped_badge", lang)
        badge_color = "#64748B"
    else:
        card_border = "#38BDF8"
        badge_text = t("nudge_pending_badge", lang)
        badge_color = "#38BDF8"

    # ── Translated UI labels ───────────────────────────────────────────────────
    lbl_usually = t("nudge_usually_label", lang)
    lbl_recommended = t("nudge_recommended_label", lang)
    lbl_shift = t("nudge_shift_load_label", lang)
    lbl_savings = t("nudge_est_savings_label", lang)
    lbl_points = t("nudge_earn_points_label", lang)

    st.markdown(
        f"""
        <div style="background-color: #1E293B; border: 2px solid {card_border}; border-radius: 12px; padding: 18px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="color: #F8FAFC; font-weight: 700; font-size: 1.1rem;">⚡ {appliance}</span>
                <span style="background-color: #0F172A; color: {badge_color}; border: 1px solid {badge_color}; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;">
                    {badge_text}
                </span>
            </div>
            <div style="color: #CBD5E1; font-size: 0.9rem; margin-bottom: 12px; line-height: 1.4;">
                {msg}
            </div>
            <div style="display: flex; gap: 16px; background-color: #0F172A; padding: 10px; border-radius: 8px; margin-bottom: 14px; font-size: 0.85rem;">
                <div><span style="color: #94A3B8;">{lbl_usually}</span> <strong style="color: #FCA5A5;">{from_time}</strong></div>
                <div><span style="color: #94A3B8;">{lbl_recommended}</span> <strong style="color: #86EFAC;">{to_time}</strong></div>
            </div>
            <div style="display: flex; justify-content: space-around; background-color: #0F172A; padding: 10px; border-radius: 8px; margin-bottom: 14px; text-align: center;">
                <div>
                    <div style="color: #94A3B8; font-size: 0.75rem;">{lbl_shift}</div>
                    <div style="color: #38BDF8; font-weight: 700;">{kwh} kWh</div>
                </div>
                <div>
                    <div style="color: #94A3B8; font-size: 0.75rem;">{lbl_savings}</div>
                    <div style="color: #4ADE80; font-weight: 700;">₹{int(saving)}</div>
                </div>
                <div>
                    <div style="color: #94A3B8; font-size: 0.75rem;">{lbl_points}</div>
                    <div style="color: #FBBF24; font-weight: 700;">+{pts} pts</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Action buttons — only shown for pending nudges
    if status == "pending":
        col1, col2 = st.columns(2)
        btn_accept_label = f"{t('nudge_btn_accept', lang)} (+{pts} pts)"
        btn_skip_label = t("nudge_btn_skip", lang)
        with col1:
            if st.button(btn_accept_label, key=f"btn_accept_{nid}", use_container_width=True, type="primary"):
                if on_respond_callback:
                    on_respond_callback(nid, True)
                st.rerun()
        with col2:
            if st.button(btn_skip_label, key=f"btn_skip_{nid}", use_container_width=True):
                if on_respond_callback:
                    on_respond_callback(nid, False)
                st.rerun()
