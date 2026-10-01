# PowerPool — 2-Minute Hackathon Demonstration Guide

**Yuva Yodha Energy Tech Hackathon 2026 — Challenge 03: Grid Reliability**  
*Project:* PowerPool — Autonomous Neighbourhood Load Flexibility & Demand Management

---

## 1. Quick Launch Commands

To start the full live application for presentation:

```powershell
# Terminal 1: Start FastAPI Backend (with isolated or local DB)
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Terminal 2: Start Streamlit Frontend
.venv\Scripts\python.exe -m streamlit run frontend/Home.py --server.port 8501

# Terminal 3 (Optional): Deterministic automated CLI demo runner
.venv\Scripts\python.exe scripts/run_demo.py --interactive
```

- **Resident & DISCOM UI:** [http://localhost:8501](http://localhost:8501)
- **FastAPI Interactive Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 2. Two-Minute Spoken Pitch Script

| Time | Slide / Screen | Spoken Script |
| :--- | :--- | :--- |
| **0:00 – 0:20** | **Home Page** (Traffic Light & Forecast) | *"Good morning, Jury. In Hyderabad, residential neighbourhoods face severe feeder transformer overload between 6:30 PM and 10 PM. At the same time, mid-day rooftop solar generation is curtailed. PowerPool solves this by creating a smart, automated flexibility market at the distribution feeder level."* |
| **0:20 – 0:45** | **Home Page** (Scenario Switcher) | *"Here on our dashboard for Feeder #HYD-17B, rated at 170 kW, our LightGBM model forecasts today's 24-hour load. Notice the RED alert in our traffic light widget. Under a **Sunny scenario**, solar peaks at 90 kW mid-day, but unmanaged evening demand surges to 196 kW. If we switch to **Heatwave**, demand escalates to 388 kW. PowerPool dynamically detects these stress windows."* |
| **0:45 – 1:10** | **Resident App** (`pages/1_Resident.py`) | *"Now let's step into the shoes of a resident in Block C. Opening the Resident Portal, we see personalized smart nudges. Instead of running an E-rickshaw charger or washing machine during the evening peak, the resident is asked to shift to 1:00 PM when solar energy is abundant. The nudge is localized in Telugu and Hindi. When the resident clicks 'Accept', they instantly earn reward points and see real rupee savings on their power bill."* |
| **1:10 – 1:35** | **DISCOM Center** (`pages/2_DISCOM.py`) | *"Switching to the DISCOM Command Center, the grid operator sees real-time feeder flexibility. Our greedy scheduling algorithm aggregates these shifted loads. Watch the central curve: the unmanaged red peak is shaved down by **19.2%**, safely beneath the transformer's limit, while solar self-consumption climbs to **99.8%**."* |
| **1:35 – 2:00** | **DR Trigger & Impact Summary** | *"During critical grid stress, the DISCOM can dispatch an instant Demand Response event with one click. 300+ appliances shift dynamically, shedding over 60 kW and bringing transformer risk from HIGH to LOW. PowerPool eliminates blackouts, saves utility CAPEX, and puts money back in residents' pockets. Thank you."* |

---

## 3. Click-by-Click UI Walkthrough

### Step 1: Landing Page (`Home.py`)
1. Open `http://localhost:8501`.
2. Point out the **Grid Status Traffic Light** showing **RED** (*"Peak Demand / Feeder Stress"*).
3. Review the **Summary KPI Cards**: Peak Reduction (~19%), Energy Shifted (~43 kWh), Solar Self-Use (~72–100%).
4. In the **Sidebar**, demonstrate scenario switching:
   - Change **Weather Scenario** from `☀️ Sunny` $\rightarrow$ `☁️ Cloudy` $\rightarrow$ `🔥 Heatwave`.
   - Point out how the demand curve peak jumps and solar generation curve drops.
   - Return to `☀️ Sunny`.

### Step 2: Resident Portal (`1_Resident.py`)
1. Click **"Open Resident App →"** button on the home page (or select `Resident` from the sidebar).
2. Point out **Household 01** and the **Reward Wallet** (Points, Estimated Savings ₹, Energy Shifted).
3. Scroll to **"⚡ Recommended Smart Actions"**.
4. In the sidebar, change **Language** from `🇬🇧 English` to `🇮🇳 हिन्दी (Hindi)` or `🇮🇳 తెలుగు (Telugu)`. Show that the nudge message translates dynamically.
5. Click **"✅ Accept"** on the nudge card.
   - Observe balloon animation and success notification (*"Great! Your load was shifted successfully. Earned +15 points!"*).
   - Point out the wallet balance increasing.
6. Scroll down to show the **Neighbourhood Leaderboard** with gamified rankings and personal environmental impact.

### Step 3: DISCOM Command Center (`2_DISCOM.py`)
1. In the sidebar, click on **`2_DISCOM`**.
2. Review the **6 Feeder Impact KPIs**: Peak Reduction, Energy Shifted, Solar Self-Use, CO₂ Avoided, Active Homes, Flex Capacity.
3. Review the **Central Feeder Load Curve**:
   - Dotted red line: Before PowerPool (Unmanaged load violating the 170 kW threshold).
   - Green line: After PowerPool (Shifted peak comfortably below threshold).
   - Yellow area: Solar generation utilized locally.
4. Point out the **Transformer Overload Risk** card.
5. In the **Automated Demand Response (DR) Trigger**:
   - Keep default slots (74–88, 18:30–22:00) and target (170 kW).
   - Click **"🚀 Trigger Instant Demand Response Event"**.
   - Observe success banner confirming DR event dispatch.

---

## 4. Recovery & Fallback Procedures

| Issue | Root Cause | Instant Recovery Action |
| :--- | :--- | :--- |
| **Backend Unreachable** | Backend terminal stopped | The frontend `ApiClient` automatically switches to self-contained, deterministic **Demo Mode** fallback with zero UI downtime. |
| **Nudge Already Accepted** | Re-running demo without resetting | Run `.venv\Scripts\python.exe scripts/run_demo.py` to reset the demo state, or click "Skip" on the UI to reset acceptance. |
| **Database Lock Error** | Multiple processes writing SQLite | The backend uses SQLite `check_same_thread=False` and connection context managers. Ensure only one backend process is active on port 8000. |
| **Port Conflict** | Port 8000 or 8501 in use | Run `Get-NetTCPConnection -LocalPort 8000, 8501` and terminate existing processes. |
