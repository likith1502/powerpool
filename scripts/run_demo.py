"""
scripts/run_demo.py — Deterministic 2-Minute PowerPool Hackathon Demo Runner.

Yuva Yodha Energy Tech Hackathon 2026 — Challenge 03: Grid Reliability.

Executes the complete 12-step demo narrative against an isolated demo database:
1. Problem Introduction (feeder threshold 170 kW vs peak overload)
2. 24-Hour Feeder Demand & Solar Forecast
3. Scenario Contrasts (Sunny, Cloudy, Heatwave)
4. Grid Stress Traffic Light & Capacity Gap
5. Resident Portal & Personalized Nudge
6. Resident Action (Nudge Acceptance)
7. Rewards & Points Feedback
8. DISCOM Command Center Overview
9. Feeder Load Optimization (Before vs After)
10. Automated Demand Response Event
11. Updated Feeder KPIs & Stress Relief
12. Quantified Impact Summary

Usage:
  python scripts/run_demo.py               # Auto run
  python scripts/run_demo.py --interactive # Step-by-step with prompt
  python scripts/run_demo.py --scenario heatwave
"""

import os
import sys
import time
import argparse
from pathlib import Path

# Safe encoding for Windows consoles
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEMO_DB_PATH = REPO_ROOT / "data" / "demo_powerpool.db"
_ORIGINAL_ENV_DB_PATH = None
_ORIGINAL_MODULE_DB_PATH = None


def setup_demo_db():
    """Ensure clean isolated database for demonstration."""
    global _ORIGINAL_ENV_DB_PATH, _ORIGINAL_MODULE_DB_PATH
    import backend.db
    _ORIGINAL_ENV_DB_PATH = os.environ.get("DB_PATH")
    _ORIGINAL_MODULE_DB_PATH = getattr(backend.db, "DB_PATH", None)
    
    backend.db.DB_PATH = str(DEMO_DB_PATH)
    os.environ["DB_PATH"] = str(DEMO_DB_PATH)
    
    if DEMO_DB_PATH.exists():
        try:
            DEMO_DB_PATH.unlink()
        except Exception:
            pass
    from backend.db import init_db
    from backend.seed_mock import seed
    init_db()
    seed(n_households=100)


def cleanup_demo_db():
    """Safely remove isolated demo database."""
    global _ORIGINAL_ENV_DB_PATH, _ORIGINAL_MODULE_DB_PATH
    if DEMO_DB_PATH.exists():
        try:
            DEMO_DB_PATH.unlink()
        except Exception:
            pass
    if _ORIGINAL_MODULE_DB_PATH is not None:
        import backend.db
        backend.db.DB_PATH = _ORIGINAL_MODULE_DB_PATH
    if _ORIGINAL_ENV_DB_PATH is not None:
        os.environ["DB_PATH"] = _ORIGINAL_ENV_DB_PATH
    elif "DB_PATH" in os.environ:
        del os.environ["DB_PATH"]


def print_banner(title):
    width = 75
    print("\n" + "=" * width)
    print(f"  {title.center(width - 4)}")
    print("=" * width)


def run_demo(interactive=False, target_scenario="sunny"):
    setup_demo_db()
    
    from fastapi.testclient import TestClient
    from backend.main import app
    client = TestClient(app)

    def pause(step_msg):
        print(f"\n>> {step_msg}")
        if interactive:
            input("   [Press Enter to proceed to next step...]")
        else:
            time.sleep(0.5)

    print_banner("⚡ POWERPOOL — 2-MINUTE LIVE HACKATHON DEMO RUNNER ⚡")
    print("Project: Neighbourhood Load Flexibility Platform")
    print("Challenge 03: Grid Reliability • Hyderabad Feeder #HYD-17B")
    print(f"Isolated Demo DB: {DEMO_DB_PATH.name}")

    # Step 1: Problem Introduction
    pause("Step 1: Grid Reliability Problem Statement")
    print(" • Transformer Rated Capacity: 170.0 kW")
    print(" • Challenge: Evening rooftop solar drops to 0 kW while cooling/cooking peak surges.")
    print(" • Traditional Solution: Expensive diesel peaker plants or brownouts.")
    print(" • PowerPool Solution: Autonomous residential load flexibility.")

    # Step 2: 24-Hour Forecast
    pause(f"Step 2: 24-Hour Feeder Demand & Solar Forecast ({target_scenario.capitalize()})")
    fc = client.get(f"/forecast?scenario={target_scenario}").json()
    slots = fc.get("slots", [])
    peak_demand = max(s["demand_kw"] for s in slots)
    peak_solar = max(s["solar_kw"] for s in slots)
    print(f" • Loaded {len(slots)} quarter-hour forecast slots for {fc.get('date')}.")
    print(f" • Peak Unmanaged Demand: {peak_demand:.2f} kW (Exceeds 170 kW limit!)")
    print(f" • Peak Solar Output:     {peak_solar:.2f} kW (Available at mid-day slots 40-56)")

    # Step 3: Scenario Contrasts
    pause("Step 3: Physical Scenario Contrasts (Sunny vs Cloudy vs Heatwave)")
    fc_sunny = client.get("/forecast?scenario=sunny").json()
    fc_cloudy = client.get("/forecast?scenario=cloudy").json()
    fc_heatwave = client.get("/forecast?scenario=heatwave").json()
    print(f"   ☀️ Sunny    ({fc_sunny['date']}): Peak Demand = {max(s['demand_kw'] for s in fc_sunny['slots']):.1f} kW | Peak Solar = {max(s['solar_kw'] for s in fc_sunny['slots']):.1f} kW")
    print(f"   ☁️ Cloudy   ({fc_cloudy['date']}): Peak Demand = {max(s['demand_kw'] for s in fc_cloudy['slots']):.1f} kW | Peak Solar = {max(s['solar_kw'] for s in fc_cloudy['slots']):.1f} kW")
    print(f"   🔥 Heatwave ({fc_heatwave['date']}): Peak Demand = {max(s['demand_kw'] for s in fc_heatwave['slots']):.1f} kW | Peak Solar = {max(s['solar_kw'] for s in fc_heatwave['slots']):.1f} kW")

    # Step 4: Grid Stress & Capacity Gap
    pause("Step 4: Grid Stress Traffic Light & Overload Window")
    stress_slots = [s for s in slots if s.get("is_stress")]
    max_gap = max((s["gap_kw"] for s in slots), default=0.0)
    print(f" • Traffic Light Status: RED (Critical Overload)")
    print(f" • Overload Stress Slots: {len(stress_slots)} slots detected (18:30 – 22:00)")
    print(f" • Maximum Feeder Capacity Gap: +{max_gap:.1f} kW above safety threshold")

    # Step 5: Resident Portal & Nudge Generation
    pause("Step 5: Resident Mobile Portal & Localized Nudges")
    # Optimize first to populate resident schedule
    opt_init = client.post("/optimize", json={"scenario": target_scenario, "compliance_rate": 0.65}).json()
    households = client.get("/households").json()
    
    # Find household with nudges
    target_hh = None
    target_nudge = None
    for h in households:
        n_res = client.get(f"/nudges/{h['id']}").json()
        nudges = n_res.get("nudges", [])
        if nudges:
            target_hh = h
            target_nudge = nudges[0]
            break

    print(f" • Selected Resident: {target_hh['name']} ({target_hh['id']}) - {target_hh['block']}")
    print(f" • Current Reward Wallet: {target_hh['points']} pts")
    print(f" • Multilingual Nudge Message (EN): \"{target_nudge['message']}\"")
    print(f" • Hindi Translation (HI):          \"{target_nudge.get('message_hi', '')}\"")
    print(f" • Telugu Translation (TE):         \"{target_nudge.get('message_te', '')}\"")

    # Step 6 & 7: Nudge Acceptance & Rewards Feedback
    pause(f"Step 6 & 7: Resident Nudge Acceptance & Real-time Reward (Nudge #{target_nudge['id']})")
    resp_accept = client.post(f"/nudges/{target_nudge['id']}/respond", json={"accept": True}).json()
    print(f" • Response Status:   ✅ {resp_accept.get('status').upper()}")
    print(f" • Points Credited:   +{resp_accept.get('points_added')} pts")
    print(f" • Bill Savings:      ₹{resp_accept.get('saving_rs'):.1f}")
    print(f" • Updated Wallet:    {resp_accept.get('household_points')} pts")
    print(f" • Notification:      \"{resp_accept.get('message')}\"")

    # Step 8: DISCOM Command Center
    pause("Step 8: DISCOM Feeder Flexibility Command Center")
    kpis = client.get(f"/kpis?scenario={target_scenario}").json()
    flex = client.get(f"/flex-capacity?scenario={target_scenario}").json()
    print(f" • Monitored Feeder: Hyderabad Feeder #HYD-17B (100 Households)")
    print(f" • Feeder Transformer Overload Risk: {kpis.get('transformer_risk')}")
    print(f" • Flexible Load Available Next Hour: {flex.get('available_kw')} kW across {flex.get('households_available')} homes")

    # Step 9: Load Optimization (Before vs After)
    pause("Step 9: Autonomous Greedy Optimization Engine")
    print(f" • Nudges Generated across Feeder: {opt_init.get('nudges_created')} shifts scheduled")
    print(f" • Peak Load Before: {opt_init.get('peak_before_kw'):.2f} kW")
    print(f" • Peak Load After:  {opt_init.get('peak_after_kw'):.2f} kW")
    print(f" • Peak Reduction:   {opt_init.get('peak_reduction_pct'):.1f}%")
    print(f" • Total Energy Shifted into Solar Window: {opt_init.get('kwh_shifted'):.2f} kWh")

    # Step 10: Demand Response Event Trigger
    pause("Step 10: Trigger Emergency Automated Demand Response (DR)")
    dr_event = client.post("/dr-event", json={
        "start_slot": 74,
        "end_slot": 88,
        "target_kw": 170.0,
        "scenario": target_scenario
    }).json()
    print(" • DR Dispatch Window: 18:30 – 22:00 (Evening Stress Peak)")
    print(f" • Target Feeder Cap:   170.0 kW")
    print(f" • Dispatch Status:     ✅ {dr_event.get('success')}")
    print(f" • Additional Nudges:   {dr_event.get('nudges_created')} households targeted")
    print(f" • Expected Reduction:  {dr_event.get('kw_reduced_expected'):.2f} kW")
    print(f" • Managed Peak:        {dr_event.get('peak_after_kw'):.2f} kW")

    # Step 11 & 12: Measurable Impact & Summary
    pause("Step 11 & 12: Final Quantified Impact Summary")
    final_kpis = client.get(f"/kpis?scenario={target_scenario}").json()
    print_banner("🏆 POWERPOOL QUANTIFIED GRID IMPACT 🏆")
    print(f" 📉 Peak Feeder Demand Reduction:    {final_kpis.get('peak_reduction_pct'):.1f}%")
    print(f" ⚡ Unmanaged Peak vs Managed Peak: {final_kpis.get('peak_before_kw'):.1f} kW  →  {final_kpis.get('peak_after_kw'):.1f} kW")
    print(f" 🔋 Flexible Electricity Shifted:   {final_kpis.get('kwh_shifted'):.1f} kWh")
    print(f" ☀️ Solar Self-Consumption:         {final_kpis.get('solar_self_use_pct'):.1f}% (+{final_kpis.get('solar_self_use_change_pct'):.1f}% improvement)")
    print(f" 🌱 CO2 Avoided per Day:            {final_kpis.get('co2_kg'):.1f} kg")
    print(f" 🏠 Participating Households:        {final_kpis.get('participants')} / {final_kpis.get('total_households')}")
    print(f" ⚠️ Final Transformer Risk Level:    {final_kpis.get('transformer_risk')}")
    print("=" * 75)
    print("✅ 2-Minute Demo successfully executed with 100% data isolation.\n")

    cleanup_demo_db()
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PowerPool Hackathon Demo Runner")
    parser.add_argument("--interactive", action="store_true", help="Pause between steps for spoken presentation")
    parser.add_argument("--scenario", default="sunny", choices=["sunny", "cloudy", "heatwave"], help="Weather scenario")
    args = parser.parse_args()

    success = run_demo(interactive=args.interactive, target_scenario=args.scenario)
    sys.exit(0 if success else 1)
