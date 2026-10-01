"""
Nudge generation service with English, Hindi, and Telugu localization.
"""

from typing import Dict, Any

APPLIANCE_TRANSLATIONS = {
    "Washing Machine": {"hi": "वॉशिंग मशीन", "te": "వాషింగ్ మెషీన్"},
    "EV Charger": {"hi": "ईवी चार्जर", "te": "ఈవీ ఛార్జర్"},
    "Water Heater (Geyser)": {"hi": "वाटर हीटर (गीजर)", "te": "వాటర్ హీటర్"},
    "Dishwasher": {"hi": "डिशवॉशर", "te": "డిష్‌వాషర్"},
    "Smart AC": {"hi": "स्मार्ट एसी", "te": "స్మార్ట్ ఏసీ"},
}


def build_multilingual_messages(
    appliance: str,
    from_time: str,
    to_time: str,
    points: int,
    saving_rs: float
) -> Dict[str, str]:
    """
    Generates localized nudge text for English, Hindi, and Telugu.
    """
    app_hi = APPLIANCE_TRANSLATIONS.get(appliance, {}).get("hi", appliance)
    app_te = APPLIANCE_TRANSLATIONS.get(appliance, {}).get("te", appliance)

    msg_en = f"Run your {appliance} between {to_time}. Earn {points} points and save about ₹{int(saving_rs)}."
    msg_hi = f"अपनी {app_hi} {to_time} के बीच चलाएँ। {points} अंक कमाएँ और लगभग ₹{int(saving_rs)} बचाएँ।"
    msg_te = f"మీ {app_te}ను {to_time} సమయంలో నడపండి. {points} పాయింట్లు సంపాదించి సుమారు ₹{int(saving_rs)} ఆదా చేయండి."

    return {
        "en": msg_en,
        "hi": msg_hi,
        "te": msg_te,
    }


def calculate_nudge_rewards(kwh_shifted: float) -> Dict[str, Any]:
    """
    Calculates points (+15 per kWh shifted, min 10) and cost savings (₹6-8 per kWh).
    """
    points = max(10, int(kwh_shifted * 15))
    saving_rs = round(kwh_shifted * 6.5, 1)
    return {
        "points": points,
        "saving_rs": saving_rs,
    }
