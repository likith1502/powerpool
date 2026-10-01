"""
Shared API Client for PowerPool Streamlit frontend.
Connects to FastAPI backend with automatic deterministic mock fallback when offline or in DEMO_MODE.
"""

import os
import requests
from typing import Dict, Any, List, Optional
from data.seed_demo import generate_scenario_json
from backend.optimizer import run_load_shifting_optimization
from backend.services.kpi_service import calculate_system_kpis

API_URL = os.getenv("API_URL", "http://localhost:8000")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
TIMEOUT_SEC = 2.0


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
            return resp.status_code == 200
        except Exception:
            return False

    def _get_mock_state(self, scenario: str = "sunny") -> Dict[str, Any]:
        """
        Loads local mock scenario data as fallback.
        """
        sc_key = scenario.lower()
        if sc_key not in self._mock_cache:
            sc_data = generate_scenario_json(sc_key)
            opt_result = run_load_shifting_optimization(sc_data)
            kpis = calculate_system_kpis(
                opt_result["before"],
                opt_result["after"],
                opt_result["kwh_shifted"],
                len(sc_data["households"]),
            )
            self._mock_cache[sc_key] = {
                "scenario_data": sc_data,
                "optimization": opt_result,
                "kpis": kpis,
                "nudges_map": {n["id"]: n for n in opt_result["nudges"]},
            }
        return self._mock_cache[sc_key]

    def get_forecast(self, date: str = "2026-10-01", scenario: str = "sunny") -> Dict[str, Any]:
        """
        Gets 96-slot forecast data.
        """
        if not DEMO_MODE:
            try:
                resp = requests.get(
                    f"{self.base_url}/forecast",
                    params={"date": date, "scenario": scenario},
                    timeout=TIMEOUT_SEC
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass

        # Fallback
        state = self._get_mock_state(scenario)
        return {
            "date": date,
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
                    json={"date": "2026-10-01", "scenario": scenario, "compliance_rate": 0.65},
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
        households = state["scenario_data"]["households"]
        h_info = next((h for h in households if h["household_id"] == household_id), None)
        pts = h_info["points"] if h_info else 245
        kwh = h_info["kwh_shifted_total"] if h_info else 12.4
        saving = round(kwh * 6.5, 1)

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
        return {
            "household_id": household_id,
            "nudges": h_nudges,
            "points": pts,
            "kwh_shifted": kwh,
            "savings_rs": saving,
        }

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

    def trigger_dr_event(self, start_slot: int = 74, end_slot: int = 88, target_kw: float = 170.0, scenario: str = "sunny") -> Dict[str, Any]:
        """
        Triggers demand response event.
        """
        if not DEMO_MODE:
            try:
                resp = requests.post(
                    f"{self.base_url}/dr-event",
                    json={"start_slot": start_slot, "end_slot": end_slot, "target_kw": target_kw, "scenario": scenario},
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
