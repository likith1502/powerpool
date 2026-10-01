"""
frontend/ui_strings.py — Centralized UI string translations for all three supported languages.

Usage:
    from frontend.ui_strings import t, LANG_CODES
    label = t("wallet_points", lang)

Supported languages: en, hi, te
Fallback: English is always returned for missing keys.
"""

from typing import Dict

LANG_CODES = ("en", "hi", "te")

# ---------------------------------------------------------------------------
# Translation table
# Keys are stable internal identifiers; values are dicts keyed by lang code.
# ---------------------------------------------------------------------------
_STRINGS: Dict[str, Dict[str, str]] = {
    # ── Nudge card ──────────────────────────────────────────────────────────
    "nudge_pending_badge": {
        "en": "⚡ PENDING ACTION",
        "hi": "⚡ कार्रवाई बाकी",
        "te": "⚡ చర్య పెండింగ్",
    },
    "nudge_accepted_badge": {
        "en": "✓ ACCEPTED",
        "hi": "✓ स्वीकृत",
        "te": "✓ అంగీకరించబడింది",
    },
    "nudge_skipped_badge": {
        "en": "SKIPPED",
        "hi": "छोड़ा गया",
        "te": "దాటవేయబడింది",
    },
    "nudge_usually_label": {
        "en": "Usually:",
        "hi": "सामान्यतः:",
        "te": "సాధారణంగా:",
    },
    "nudge_recommended_label": {
        "en": "Recommended:",
        "hi": "अनुशंसित:",
        "te": "సిఫార్సు చేయబడింది:",
    },
    "nudge_shift_load_label": {
        "en": "Shift Load",
        "hi": "लोड शिफ्ट",
        "te": "లోడ్ మార్చు",
    },
    "nudge_est_savings_label": {
        "en": "Est. Savings",
        "hi": "अनुमानित बचत",
        "te": "అంచనా పొదుపు",
    },
    "nudge_earn_points_label": {
        "en": "Earn Points",
        "hi": "पॉइंट पाएँ",
        "te": "పాయింట్లు పొందండి",
    },
    "nudge_btn_accept": {
        "en": "✓ Accept",
        "hi": "✓ स्वीकार करें",
        "te": "✓ అంగీకరించు",
    },
    "nudge_btn_skip": {
        "en": "Skip",
        "hi": "छोड़ें",
        "te": "దాటవేయి",
    },
    # ── Resident page ───────────────────────────────────────────────────────
    "resident_page_title": {
        "en": "📱 Resident Portal",
        "hi": "📱 निवासी पोर्टल",
        "te": "📱 నివాసి పోర్టల్",
    },
    "resident_page_subtitle": {
        "en": "Smart Energy Assistant for your Neighbourhood Grid",
        "hi": "आपके मोहल्ले के ग्रिड के लिए स्मार्ट ऊर्जा सहायक",
        "te": "మీ పాడగ్రిడ్ కోసం స్మార్ట్ ఎనర్జీ అసిస్టెంట్",
    },
    "resident_grid_status_heading": {
        "en": "#### **Today's Neighbourhood Grid Status**",
        "hi": "#### **आज की मोहल्ला ग्रिड स्थिति**",
        "te": "#### **ఈరోజు పాడగ్రిడ్ స్థితి**",
    },
    "resident_wallet_heading": {
        "en": "#### **Your Wallet & Energy Rewards**",
        "hi": "#### **आपका वॉलेट और ऊर्जा पुरस्कार**",
        "te": "#### **మీ వాలెట్ & ఎనర్జీ రివార్డులు**",
    },
    "resident_wallet_points_title": {
        "en": "Reward Points",
        "hi": "रिवार्ड पॉइंट",
        "te": "రివార్డ్ పాయింట్లు",
    },
    "resident_wallet_points_subtitle": {
        "en": "Redeemable for power bill discounts",
        "hi": "बिजली बिल पर छूट के लिए भुनाएं",
        "te": "విద్యుత్ బిల్లు తగ్గింపుకు రిడీమ్ చేయండి",
    },
    "resident_wallet_savings_title": {
        "en": "Estimated Savings",
        "hi": "अनुमानित बचत",
        "te": "అంచనా పొదుపు",
    },
    "resident_wallet_savings_subtitle": {
        "en": "Saved by off-peak load shifting",
        "hi": "ऑफ-पीक लोड शिफ्टिंग से बचत",
        "te": "ఆఫ్-పీక్ లోడ్ షిఫ్టింగ్ ద్వారా పొదుపు",
    },
    "resident_wallet_kwh_title": {
        "en": "Energy Shifted",
        "hi": "ऊर्जा शिफ्ट की गई",
        "te": "మార్చిన శక్తి",
    },
    "resident_wallet_kwh_subtitle": {
        "en": "Shifted to solar-rich hours",
        "hi": "सौर-समृद्ध घंटों में स्थानांतरित",
        "te": "సోలార్ సమృద్ధ గంటలకు మార్చబడింది",
    },
    "resident_smart_actions_heading": {
        "en": "#### **⚡ Recommended Smart Actions**",
        "hi": "#### **⚡ अनुशंसित स्मार्ट कार्रवाइयाँ**",
        "te": "#### **⚡ సిఫార్సు చేయబడిన స్మార్ట్ చర్యలు**",
    },
    "resident_no_nudges_msg": {
        "en": "No active load shift recommendations right now. Check back during evening peak hours!",
        "hi": "अभी कोई सक्रिय लोड शिफ्ट सिफारिश नहीं है। शाम के पीक घंटों में दोबारा देखें!",
        "te": "ప్రస్తుతం ఎటువంటి సక్రియ లోడ్ షిఫ్ట్ సిఫార్సులు లేవు. సాయంత్రం పీక్ గంటల్లో తిరిగి చెక్ చేయండి!",
    },
    "resident_feeder_curve_heading": {
        "en": "#### **Feeder Load & Solar Curve**",
        "hi": "#### **फीडर लोड और सोलर कर्व**",
        "te": "#### **ఫీడర్ లోడ్ & సోలార్ కర్వ్**",
    },
    "resident_leaderboard_heading": {
        "en": "#### **🏆 Neighbourhood Leaderboard**",
        "hi": "#### **🏆 मोहल्ला लीडरबोर्ड**",
        "te": "#### **🏆 పాడగ్రిడ్ లీడర్‌బోర్డ్**",
    },
    "resident_impact_heading": {
        "en": "#### **🌱 Your Personal Environmental Impact**",
        "hi": "#### **🌱 आपका व्यक्तिगत पर्यावरणीय प्रभाव**",
        "te": "#### **🌱 మీ వ్యక్తిగత పర్యావరణ ప్రభావం**",
    },
    "resident_impact_total_label": {
        "en": "Total Impact to Date",
        "hi": "अब तक का कुल प्रभाव",
        "te": "ఇప్పటి వరకు మొత్తం ప్రభావం",
    },
    "resident_impact_solar_kwh": {
        "en": "clean solar energy used",
        "hi": "स्वच्छ सौर ऊर्जा उपयोग की गई",
        "te": "శుద్ధ సౌర శక్తి వినియోగించబడింది",
    },
    "resident_impact_co2": {
        "en": "kg CO₂ avoided from coal grid generation",
        "hi": "किग्रा CO₂ कोयला ग्रिड उत्पादन से बचाया",
        "te": "కిలో CO₂ బొగ్గు గ్రిడ్ ఉత్పత్తి నుండి నివారించబడింది",
    },
    "resident_impact_savings": {
        "en": "total power bill savings",
        "hi": "कुल बिजली बिल बचत",
        "te": "మొత్తం విద్యుత్ బిల్లు పొదుపు",
    },
    "resident_impact_points": {
        "en": "total community points earned",
        "hi": "कुल सामुदायिक पॉइंट अर्जित",
        "te": "మొత్తం కమ్యూనిటీ పాయింట్లు సంపాదించారు",
    },
    # ── Nudge accept/skip feedback messages ────────────────────────────────
    "nudge_accept_success": {
        "en": "🎉 {msg} Earned +{pts} points!",
        "hi": "🎉 {msg} +{pts} पॉइंट मिले!",
        "te": "🎉 {msg} +{pts} పాయింట్లు సంపాదించారు!",
    },
    "nudge_skip_info": {
        "en": "Nudge skipped.",
        "hi": "नज छोड़ा गया।",
        "te": "నడ్జ్ దాటవేయబడింది.",
    },
    # ── Sidebar ─────────────────────────────────────────────────────────────
    "sidebar_scenario_explorer_heading": {
        "en": "**Scenario Explorer**",
        "hi": "**परिदृश्य अन्वेषक**",
        "te": "**దృశ్య అన్వేషకుడు**",
    },
    "sidebar_scenario_explorer_desc": {
        "en": "Switch between Sunny, Cloudy, and Heatwave scenarios to explore feeder demand, renewable generation, and grid stress.",
        "hi": "फीडर मांग, नवीकरणीय उत्पादन और ग्रिड तनाव का पता लगाने के लिए धूप, बादल और हीटवेव परिदृश्यों के बीच स्विच करें।",
        "te": "ఫీడర్ డిమాండ్, పునరుత్పాదక శక్తి ఉత్పత్తి మరియు గ్రిడ్ ఒత్తిడిని అన్వేషించడానికి సన్నీ, క్లౌడీ మరియు హీట్‌వేవ్ దృశ్యాల మధ్య మారండి.",
    },
    # ── Data provenance labels ───────────────────────────────────────────────
    "data_source_mock": {
        "en": "📋 Seeded scenario data",
        "hi": "📋 सीडेड परिदृश्य डेटा",
        "te": "📋 సీడెడ్ దృశ్య డేటా",
    },
    "data_source_model": {
        "en": "🤖 ML model forecast",
        "hi": "🤖 ML मॉडल पूर्वानुमान",
        "te": "🤖 ML మోడల్ అంచనా",
    },
}


def t(key: str, lang: str = "en") -> str:
    """Return the UI string for key in the given language, falling back to English."""
    entry = _STRINGS.get(key)
    if entry is None:
        return f"[{key}]"  # Missing key — visible in dev, never silently empty
    return entry.get(lang) or entry.get("en", f"[{key}]")
