"""
Shared API Client for PowerPool Streamlit frontend.
Connects to FastAPI backend with automatic deterministic mock fallback when offline or in DEMO_MODE.
"""

import os
import math
import requests
from typing import Dict, Any, List, Optional

API_URL = os.getenv("API_URL", "http://localhost:8000")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
TIMEOUT_SEC = 5.0


def _build_fallback_mock_state(scenario: str = "sunny") -> Dict[str, Any]:
    """Generates a self-contained, deterministic mock state for offline/demo mode."""
    sc = scenario.lower()
    is_heatwave = sc == "heatwave"
    is_cloudy = sc == "cloudy"

    capacity = 170.0
    base_peak = 220.0 if not is_heatwave else 285.0
    solar_peak = 52.0 if not is_cloudy else 18.0

    before_slots = []
    after_slots = []

    for i in range(96):
        hour = (i * 15) // 60
        minute = (i * 15) % 60
        t_str = f"{hour:02d}:{minute:02d}"

        # Solar curve
        if 24 <= i <= 72:
            s_rad = (i - 24) / 48.0 * math.pi
            s_val = round(max(0.0, math.sin(s_rad)) * solar_peak, 2)
        else:
            s_val = 0.0

        # Demand curve
        if 74 <= i <= 88:
            d_before = round(base_peak - abs(81 - i) * 3.5, 2)
            d_after = round(d_before - 38.0, 2)
        elif 40 <= i <= 60:
            d_before = round(95.0 + (15.0 if is_heatwave else 0.0), 2)
            d_after = round(d_before + 28.0, 2)
        else:
            d_before = round(65.0 + (i % 8) * 2.0, 2)
            d_after = d_before

        gap_b = round(d_before - capacity, 2)
        gap_a = round(d_after - capacity, 2)

        before_slots.append({
            "slot": i,
            "time": t_str,
            "demand_kw": d_before,
            "capacity_kw": capacity,
            "solar_kw": s_val,
            "gap_kw": gap_b,
            "is_stress": gap_b > 0
        })
        after_slots.append({
            "slot": i,
            "time": t_str,
            "demand_kw": d_after,
            "capacity_kw": capacity,
            "solar_kw": s_val,
            "gap_kw": gap_a,
            "is_stress": gap_a > 0
        })

    peak_b = max(s["demand_kw"] for s in before_slots)
    peak_a = max(s["demand_kw"] for s in after_slots)
    red_pct = round(100.0 * (peak_b - peak_a) / peak_b, 1)
    kwh = 42.8 if not is_heatwave else 56.4

    mock_nudges = [
        {
            "id": 100 + h,
            "household_id": h,
            "appliance": "Washing Machine" if h % 3 == 0 else ("Geyser" if h % 3 == 1 else "Water Pump"),
            "from_time": "19:00",
            "to_time": "13:00–14:00",
            "kwh_shifted": 1.2,
            "points": 15,
            "saving_rs": 8.0,
            "message": "Run your appliance between 13:00–14:00 to use clean solar energy.",
            "message_hi": "स्वच्छ सौर ऊर्जा का उपयोग करने के लिए अपने उपकरण को 13:00–14:00 के बीच चलाएं।",
            "message_te": "శుభ్రమైన సౌర శక్తిని ఉపయోగించడానికి మీ ఉపకరణాన్ని 13:00–14:00 మధ్య నడపండి.",
            "status": "pending"
        }
        for h in range(1, 101)
    ]

    opt_result = {
        "before": before_slots,
        "after": after_slots,
        "nudges_created": len(mock_nudges),
        "peak_before_kw": peak_b,
        "peak_after_kw": peak_a,
        "peak_reduction_pct": red_pct,
        "kwh_shifted": kwh,
        "nudges": mock_nudges
    }

    kpis = {
        "peak_reduction_pct": red_pct,
        "kwh_shifted": kwh,
        "solar_self_use_pct": 74.2 if not is_cloudy else 58.1,
        "solar_self_use_change_pct": 14.5 if not is_cloudy else 8.2,
        "co2_kg": round(kwh * 0.71, 2),
        "participants": 67,
        "households": 80,
        "peak_before_kw": peak_b,
        "peak_after_kw": peak_a,
        "rs_saved": round(kwh * 4.0, 2)
    }

    mock_households = [
        {"household_id": h, "name": f"Household {h:02d}", "points": 450 - h * 12, "kwh_shifted_total": round(35.0 - h * 0.8, 1)}
        for h in range(1, 11)
    ]

    return {
        "scenario_data": {"households": mock_households},
        "optimization": opt_result,
        "kpis": kpis,
        "nudges_map": {n["id"]: n for n in mock_nudges}
    }


class PowerPoolAPIClient:
    """
    API client wrapper for Streamlit pages.
    """

    def __init__(self, base_url: str = API_URL):
        self.base_url = base_url.rstrip("/")
        self._mock_cache: Dict[str, Any] = {}

    def is_backend_available(self) -> bool:
        """
        Checks if the FastAPI backend is running and reachable.
        """
        if DEMO_MODE:
            return False
        try:
            resp = requests.get(f"{self.base_url}/", timeout=1.0)
            if resp.status_code == 200:
                return True
            resp2 = requests.get(f"{self.base_url}/health", timeout=1.0)
            return resp2.status_code == 200
        except Exception:
            return False

    def _get_mock_state(self, scenario: str = "sunny") -> Dict[str, Any]:
        """
        Loads local mock scenario data as fallback.
        """
        sc_key = scenario.lower()
        if sc_key not in self._mock_cache:
            self._mock_cache[sc_key] = _build_fallback_mock_state(sc_key)
        return self._mock_cache[sc_key]

    def get_forecast(self, date: Optional[str] = None, scenario: str = "sunny", live: bool = False) -> Dict[str, Any]:
        """
        Gets 96-slot forecast data. Supports live=True for live LightGBM model inference.
        """
        if not DEMO_MODE:
            try:
                params = {"scenario": scenario}
                if date:
                    params["date"] = date
                if live:
                    params["live"] = "true"
                resp = requests.get(
                    f"{self.base_url}/forecast",
                    params=params,
                    timeout=TIMEOUT_SEC
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass

        # Fallback
        sc_dates = {"sunny": "2026-10-01", "cloudy": "2026-10-02", "heatwave": "2026-10-03"}
        effective_dt = date or sc_dates.get(scenario.lower(), "2026-10-01")
        state = self._get_mock_state(scenario)
        return {
            "date": effective_dt,
            "scenario": scenario,
            "slots": state["optimization"]["before"],
        }

    def optimize(self, scenario: str = "sunny") -> Dict[str, Any]:
        """
        Runs load shifting optimization.
        """
        if not DEMO_MODE:
            try:
                resp = requests.post(
                    f"{self.base_url}/optimize",
                    json={"scenario": scenario, "compliance_rate": 0.65},
                    timeout=TIMEOUT_SEC
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass

        # Fallback
        state = self._get_mock_state(scenario)
        opt = state["optimization"]
        return {
            "before": opt["before"],
            "after": opt["after"],
            "nudges_created": opt["nudges_created"],
            "peak_before_kw": opt["peak_before_kw"],
            "peak_after_kw": opt["peak_after_kw"],
            "peak_reduction_pct": opt["peak_reduction_pct"],
            "kwh_shifted": opt["kwh_shifted"],
        }

    def get_nudges(self, household_id: int = 1, scenario: str = "sunny") -> Dict[str, Any]:
        """
        Gets nudges for a specific household.
        """
        if not DEMO_MODE:
            try:
                resp = requests.get(
                    f"{self.base_url}/nudges/{household_id}",
                    params={"scenario": scenario},
                    timeout=TIMEOUT_SEC
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass

        # Fallback
        state = self._get_mock_state(scenario)
        nudges_map = state["nudges_map"]
        h_nudges = [n for n in nudges_map.values() if n["household_id"] == household_id]
        if not h_nudges:
            h_nudges = [{
                "id": 900 + household_id,
                "household_id": household_id,
                "appliance": "Washing Machine",
                "from_time": "19:00",
                "to_time": "13:00–14:00",
                "kwh_shifted": 1.2,
                "points": 15,
                "saving_rs": 8.0,
                "message": "Run your Washing Machine between 13:00–14:00. Earn 15 points and save about ₹8.",
                "message_hi": "अपनी वॉशिंग मशीन 13:00–14:00 के बीच चलाएँ। 15 अंक कमाएँ और लगभग ₹8 बचाएँ।",
                "message_te": "మీ వాషింగ్ మెషీన్‌ను 13:00–14:00 సమయంలో నడపండి. 15 పాయింట్లు సంపాదించి సుమారు ₹8 ఆదా చేయండి.",
                "status": "pending",
            }]
        return {"household_id": household_id, "nudges": h_nudges}

    def respond_to_nudge(self, nudge_id: int, accept: bool) -> Dict[str, Any]:
        """
        Responds to a nudge (Accept / Skip).
        """
        if not DEMO_MODE:
            try:
                resp = requests.post(
                    f"{self.base_url}/nudges/{nudge_id}/respond",
                    json={"accept": accept},
                    timeout=TIMEOUT_SEC
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass

        # Fallback response
        status = "accepted" if accept else "skipped"
        pts = 15 if accept else 0
        save = 8.0 if accept else 0.0
        msg = "Great! Your load was shifted successfully." if accept else "Nudge skipped."
        return {
            "id": nudge_id,
            "status": status,
            "points_added": pts,
            "saving_rs": save,
            "message": msg,
        }

    def get_kpis(self, scenario: str = "sunny") -> Dict[str, Any]:
        """
        Gets system KPIs.
        """
        if not DEMO_MODE:
            try:
                resp = requests.get(
                    f"{self.base_url}/kpis",
                    params={"scenario": scenario},
                    timeout=TIMEOUT_SEC
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass

        # Fallback
        state = self._get_mock_state(scenario)
        return state["kpis"]

    def get_leaderboard(self, scenario: str = "sunny") -> Dict[str, Any]:
        """
        Gets neighbourhood leaderboard.
        """
        if not DEMO_MODE:
            try:
                resp = requests.get(
                    f"{self.base_url}/leaderboard",
                    params={"scenario": scenario},
                    timeout=TIMEOUT_SEC
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass

        # Fallback
        state = self._get_mock_state(scenario)
        households = state["scenario_data"]["households"]
        sorted_h = sorted(households, key=lambda x: x["points"], reverse=True)[:5]
        board = []
        for idx, h in enumerate(sorted_h, start=1):
            board.append({
                "rank": idx,
                "household_id": h["household_id"],
                "name": h["name"],
                "points": h["points"],
                "kwh_shifted": h["kwh_shifted_total"],
            })
        return {"leaderboard": board}

    def trigger_dr_event(self, start_slot: int = 74, end_slot: int = 88, target_kw: float = 170.0, scenario: Optional[str] = None) -> Dict[str, Any]:
        """
        Triggers demand response event.
        """
        if not DEMO_MODE:
            try:
                payload = {"start_slot": start_slot, "end_slot": end_slot, "target_kw": target_kw}
                if scenario:
                    payload["scenario"] = scenario
                resp = requests.post(
                    f"{self.base_url}/dr-event",
                    json=payload,
                    timeout=TIMEOUT_SEC
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass

        # Fallback
        return {
            "success": True,
            "nudges_created": 57,
            "target_kw": target_kw,
            "available_flexible_kw": 42.0,
            "peak_after_kw": 165.8,
            "message": f"Demand response event triggered for slots {start_slot}-{end_slot}. 57 households nudged.",
        }

    def get_flex_capacity(self, scenario: str = "sunny") -> Dict[str, Any]:
        """
        Gets available flexible capacity.
        """
        if not DEMO_MODE:
            try:
                resp = requests.get(
                    f"{self.base_url}/flex-capacity",
                    params={"scenario": scenario},
                    timeout=TIMEOUT_SEC
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass

        # Fallback
        state = self._get_mock_state(scenario)
        kwh = state["optimization"]["kwh_shifted"]
        return {
            "window": "next_hour",
            "available_kw": max(20.0, round(kwh * 0.98, 1)),
            "households_available": 67,
        }


# Global client instance
api_client = PowerPoolAPIClient()
