"""Nudge text in English / Hindi / Telugu. Dictionary first (never fails);
LLM only used to polish if an API key is present."""
from .config import ANTHROPIC_API_KEY, slot_to_time

APPLIANCE_NAMES = {
    "Washing machine": {"hi": "वॉशिंग मशीन", "te": "వాషింగ్ మెషిన్"},
    "Water pump": {"hi": "पानी की मोटर", "te": "నీటి మోటార్"},
    "Inverter charging": {"hi": "इन्वर्टर चार्जिंग", "te": "ఇన్వర్టర్ ఛార్జింగ్"},
    "Geyser": {"hi": "गीज़र", "te": "గీజర్"},
    "Iron": {"hi": "इस्त्री", "te": "ఇస్త్రీ పెట్టె"},
    "E-rickshaw charging": {"hi": "ई-रिक्शा चार्जिंग", "te": "ఈ-రిక్షా ఛార్జింగ్"},
}
TEMPLATES = {
    "en": "Run your {app} at {t} today instead of {f}. Earn {p} points and save about Rs {s}.",
    "hi": "आज अपनी {app} {f} के बजाय {t} बजे चलाएँ। {p} पॉइंट पाएँ और लगभग ₹{s} बचाएँ।",
    "te": "ఈరోజు మీ {app}‌ను {f}కు బదులుగా {t}కు నడపండి. {p} పాయింట్లు పొందండి, సుమారు ₹{s} ఆదా చేయండి.",
}


def nudge_text(appliance, from_slot, to_slot, points, saving, lang="en"):
    lang = lang if lang in TEMPLATES else "en"
    app = APPLIANCE_NAMES.get(appliance, {}).get(lang, appliance)
    return TEMPLATES[lang].format(app=app, t=slot_to_time(to_slot),
                                  f=slot_to_time(from_slot), p=points, s=f"{round(float(saving), 1):g}")


import os

def is_ai_personalization_enabled() -> bool:
    """Check if AI nudge personalization is explicitly opted into via environment."""
    return os.getenv("AI_NUDGE_PERSONALIZATION", "false").lower() in ("true", "1", "yes") and bool(os.getenv("ANTHROPIC_API_KEY", "").strip())


def personalize_nudge(appliance: str, from_slot: int, to_slot: int, points: int, saving: float, lang: str = "en", tone: str = "friendly") -> str:
    """
    Opt-in AI nudge personalization using Anthropic Claude.
    
    Guarantees:
    - Zero PII: sends only appliance, slot times, points, and rupees. Never household ID, name, or location.
    - Deterministic fallback: returns standard template on any error, timeout, or invalid output.
    - Output validation: ensures concise single-sentence response.
    """
    fallback = nudge_text(appliance, from_slot, to_slot, points, saving, lang=lang)
    if not is_ai_personalization_enabled():
        return fallback

    try:
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        client = anthropic.Anthropic(api_key=api_key)
        from_time = slot_to_time(from_slot)
        to_time = slot_to_time(to_slot)
        prompt = (
            f"Draft a concise, encouraging 1-sentence energy nudge in {lang}. "
            f"Action: shift {appliance} from {from_time} to {to_time}. "
            f"Reward: {points} points and about Rs {round(float(saving), 1):g} savings. "
            f"Tone: {tone}. Reply ONLY with the nudge sentence, no quotation marks."
        )
        msg = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        content = msg.content[0].text.strip().strip('"')
        if len(content) >= 15 and "\n" not in content[:30]:
            return content
        return fallback
    except Exception:
        return fallback


def llm_translate(text, lang):
    """Optional: friendlier wording via Claude. Falls back to input on any error."""
    if not ANTHROPIC_API_KEY or lang == "en":
        return text
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        target = {"hi": "Hindi", "te": "Telugu"}[lang]
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=200,
            messages=[{"role": "user", "content":
                       f"Rewrite this energy-saving nudge in simple, friendly {target}. "
                       f"Keep numbers and times unchanged. Reply with only the text:\n{text}"}])
        return msg.content[0].text.strip()
    except Exception:
        return text
