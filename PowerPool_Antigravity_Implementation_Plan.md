# PowerPool — Antigravity Complete Implementation Plan

## 0. Mission

Build and finish the **PowerPool** hackathon prototype end-to-end, with special emphasis on completing **Member C (Frontend, UX, Pitch)** work while integrating cleanly with Member A's data/ML work and Member B's FastAPI/algorithm work.

This document is written as an **execution specification for Antigravity**. Follow it sequentially. Do not stop after scaffolding. Implement, test, integrate, polish, and leave the repository in a runnable demo state.

### Product

PowerPool is a neighbourhood-scale load-flexibility platform that:

1. Forecasts feeder demand and solar generation.
2. Detects renewable intermittency / feeder stress windows.
3. Finds flexible household loads.
4. Shifts flexible loads from stressed periods to better windows.
5. Generates personalised resident nudges.
6. Tracks acceptance, points and savings.
7. Shows a DISCOM/community dashboard with before/after load curves and impact KPIs.

### Hackathon scope

The source plan defines five modules:

- Neighbourhood simulator
- Demand + solar forecasting
- Flexibility / nudge engine
- Resident mobile web app
- DISCOM/community dashboard

MUST-HAVE features are simulator, forecasts, greedy load shifting, before/after chart, resident nudge screen and KPIs. SHOULD-HAVE features include points/leaderboard, DR trigger, Hindi/Telugu nudges, CO2 and rupee savings. Telegram, LLM chat and battery simulation are stretch goals and must not delay the core demo.

---

# 1. Non-negotiable execution rules

Antigravity must follow these rules throughout implementation.

## 1.1 Inspect before modifying

Before creating or changing files:

- Inspect the repository tree.
- Identify the existing backend, frontend, ML and data code.
- Read `README.md`, `requirements.txt`, `.env.example` if present, and all relevant entry points.
- Reuse working code instead of replacing it.
- Do not delete functioning Member A/B code.
- Do not change API contracts unnecessarily.
- If an API already exists, adapt the frontend to it instead of inventing a second API.

## 1.2 Preserve the agreed architecture

Preferred architecture:

```text
Open-Meteo / cached weather
        |
        v
Synthetic household + appliance data
        |
        v
SQLite: powerpool.db
        |
        +-------------------------+
        |                         |
        v                         v
Forecasting engine          Flexibility optimizer
        |                         |
        +------------+------------+
                     |
                     v
                 FastAPI
                     |
             REST / JSON API
                     |
          +----------+----------+
          |                     |
          v                     v
   Resident Streamlit      DISCOM Streamlit
        App                   Dashboard
```

The source plan specifies Python, FastAPI, Streamlit, Plotly, SQLite, pandas/NumPy and LightGBM as the primary stack.

## 1.3 Demo-first engineering

Every implementation decision must optimize for:

- reliable local execution
- fast startup
- deterministic demo data
- clear visuals
- graceful fallback if backend/API/weather is unavailable
- no unnecessary authentication
- no real hardware integration
- no payment integration
- no real DISCOM integration

## 1.4 Never block the UI on optional services

The frontend must remain usable if:

- FastAPI is not running
- Open-Meteo is unavailable
- an LLM API is unavailable
- a deployment URL is unavailable

Use local/mock fallback data where appropriate.

---

# 2. Expected repository structure

Target structure:

```text
powerpool/
├── data/
│   ├── generator.py
│   ├── weather.py
│   ├── seed_demo.py
│   ├── scenarios/
│   │   ├── sunny.json
│   │   ├── cloudy.json
│   │   └── heatwave.json
│   └── powerpool.db
│
├── ml/
│   ├── forecast_demand.py
│   ├── forecast_solar.py
│   ├── metrics.py
│   └── models/
│       ├── demand_model.pkl
│       └── ...
│
├── backend/
│   ├── main.py
│   ├── optimizer.py
│   ├── nudges.py
│   ├── schemas.py
│   └── services/
│       ├── forecast_service.py
│       ├── kpi_service.py
│       └── scenario_service.py
│
├── frontend/
│   ├── Home.py
│   ├── api_client.py
│   ├── components/
│   │   ├── cards.py
│   │   ├── charts.py
│   │   ├── nudge_card.py
│   │   ├── traffic_light.py
│   │   └── sidebar.py
│   ├── pages/
│   │   ├── 1_Resident.py
│   │   └── 2_DISCOM.py
│   └── assets/
│
├── tests/
│   ├── test_api_contracts.py
│   ├── test_frontend_data.py
│   ├── test_kpis.py
│   └── test_smoke.py
│
├── pitch/
│   ├── demo_script.md
│   └── pitch_content.md
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

If the repository already uses a different but functional structure, preserve it and map these responsibilities onto the existing structure rather than blindly moving files.

---

# 3. Phase 0 — Repository audit

## Objective

Understand the current implementation before touching it.

### Tasks

1. Print repository tree.
2. Locate:
   - FastAPI entry point
   - Streamlit entry point
   - SQLite database
   - forecast code
   - optimizer
   - API schemas
   - existing frontend pages
3. Inspect current API routes.
4. Inspect database schema.
5. Inspect existing sample/demo data.
6. Inspect Git status and current branch.
7. Identify unfinished TODOs.
8. Identify broken imports and startup errors.

### Required output

Create:

```text
IMPLEMENTATION_STATUS.md
```

containing:

```text
Component        Status       Entry point        Notes
Data             ...
Forecasting      ...
Optimizer        ...
FastAPI          ...
Resident UI      ...
DISCOM UI        ...
Integration      ...
Deployment       ...
Pitch            ...
```

Do not make destructive changes during this phase.

---

# 4. Phase 1 — Lock the API contract

The frontend must be built against stable contracts.

Required endpoints:

```text
GET  /forecast?date=YYYY-MM-DD
POST /optimize
GET  /nudges/{household_id}
POST /nudges/{id}/respond
GET  /kpis
GET  /leaderboard
POST /dr-event
GET  /flex-capacity
```

The source specification expects `/forecast` to return 96 fifteen-minute slots and `/optimize` to return before/after curves and reduction metrics.

## 4.1 GET /forecast

Expected shape:

```json
{
  "date": "2026-10-01",
  "slots": [
    {
      "slot": 0,
      "time": "00:00",
      "timestamp": "2026-10-01T00:00:00",
      "demand_kw": 82.4,
      "solar_kw": 0.0,
      "capacity_kw": 170.0,
      "gap_kw": -87.6,
      "is_stress": false
    }
  ]
}
```

## 4.2 POST /optimize

Expected shape:

```json
{
  "before": [],
  "after": [],
  "nudges_created": 143,
  "peak_before_kw": 196.2,
  "peak_after_kw": 158.7,
  "peak_reduction_pct": 19.1,
  "kwh_shifted": 42.8
}
```

## 4.3 GET /nudges/{household_id}

```json
{
  "household_id": 1,
  "nudges": [
    {
      "id": 101,
      "appliance": "Washing Machine",
      "from_time": "19:00",
      "to_time": "13:00",
      "kwh_shifted": 1.2,
      "points": 15,
      "saving_rs": 8.0,
      "message": "Run your washing machine between 1-2 PM today.",
      "status": "pending"
    }
  ]
}
```

## 4.4 POST /nudges/{id}/respond

Request:

```json
{
  "accept": true
}
```

Response:

```json
{
  "id": 101,
  "status": "accepted",
  "points_added": 15,
  "saving_rs": 8.0,
  "message": "Great! Your load was shifted successfully."
}
```

## 4.5 GET /kpis

```json
{
  "peak_reduction_pct": 19.1,
  "kwh_shifted": 42.8,
  "solar_self_use_pct": 72.4,
  "solar_self_use_change_pct": 14.2,
  "co2_kg": 29.96,
  "participants": 67,
  "households": 100
}
```

## 4.6 GET /leaderboard

```json
{
  "leaderboard": [
    {
      "rank": 1,
      "household_id": 21,
      "name": "Household 21",
      "points": 420,
      "kwh_shifted": 31.2
    }
  ]
}
```

## 4.7 POST /dr-event

Request:

```json
{
  "start_slot": 76,
  "end_slot": 88,
  "target_kw": 170
}
```

Response:

```json
{
  "success": true,
  "nudges_created": 57,
  "target_kw": 170,
  "available_flexible_kw": 42.0,
  "peak_after_kw": 165.8
}
```

## 4.8 GET /flex-capacity

```json
{
  "window": "next_hour",
  "available_kw": 42.0,
  "households_available": 67
}
```

---

# 5. Phase 2 — Build the shared frontend API client

Create:

```text
frontend/api_client.py
```

Requirements:

- Read backend URL from `API_URL`.
- Default to `http://localhost:8000`.
- Use `requests`.
- Add timeout.
- Catch connection errors.
- Return typed/dict-like data.
- Automatically fall back to deterministic demo data.
- Never crash the Streamlit app because FastAPI is unavailable.

Recommended interface:

```python
get_forecast(date=None)
optimize()
get_nudges(household_id)
respond_to_nudge(nudge_id, accept)
get_kpis()
get_leaderboard()
trigger_dr_event(start_slot, end_slot, target_kw)
get_flex_capacity()
```

Add:

```python
is_backend_available()
```

and expose a UI indicator:

```text
● Live backend
```

or:

```text
● Demo mode
```

Do not expose stack traces to users.

---

# 6. Phase 3 — Create deterministic demo scenarios

Create three demo scenarios:

1. Sunny
2. Cloudy
3. Heatwave

These are explicitly required for the final demo.

Each scenario should alter:

- temperature
- irradiance
- solar generation
- household demand
- stress-window severity

## Sunny

Expected characteristics:

- strong midday solar
- low evening solar
- obvious midday surplus
- evening demand peak

## Cloudy

Expected characteristics:

- lower solar generation
- smaller surplus window
- larger evening gap

## Heatwave

Expected characteristics:

- high temperature
- higher cooling load
- higher evening demand
- stronger feeder stress

The exact numbers may be synthetic, but they must be internally consistent.

Add a scenario selector to the UI:

```text
Scenario
[ Sunny ▼ ]
```

Changing scenario must refresh:

- forecast chart
- stress window
- KPIs
- flexible capacity
- resident nudges

If the backend does not support scenarios, implement scenario transformations in demo/mock mode without changing production API contracts.

---

# 7. Phase 4 — Member C: Resident app

This is the highest-priority frontend implementation.

File:

```text
frontend/pages/1_Resident.py
```

## 7.1 UX goal

The resident must understand the entire product in less than 10 seconds.

The screen should communicate:

```text
Today's grid status
        ↓
Your recommended action
        ↓
What you earn/save
        ↓
Your points
```

## 7.2 Header

Create:

```text
PowerPool
Smart energy for your neighbourhood
```

Include:

- scenario selector
- language selector
- backend/demo status

Language options:

```text
English
हिन्दी
తెలుగు
```

## 7.3 Traffic light

Large visual status component:

```text
GREEN
Solar-rich / low-stress
```

```text
AMBER
Moderate grid stress
```

```text
RED
Peak demand / shift loads now
```

Determine status from forecast data.

Suggested logic:

```python
if current_gap <= 0:
    GREEN
elif current_gap < threshold:
    AMBER
else:
    RED
```

Do not hard-code the status if forecast data is available.

## 7.4 Today's energy chart

Use Plotly.

Show:

- demand
- solar
- feeder capacity
- stress region

Use a 24-hour x-axis.

Highlight 18:30–22:00 or dynamically detected stress windows.

Add hover information.

## 7.5 Nudge cards

Create reusable component:

```text
frontend/components/nudge_card.py
```

Card:

```text
⚡ Smart Energy Action

Washing Machine

Usually: 7:00 PM
Recommended: 1:00 PM – 2:00 PM

Shift: 1.2 kWh
Save: ₹8
Earn: +15 points

[ Accept ] [ Skip ]
```

When Accept is clicked:

1. call `/nudges/{id}/respond`
2. show success message
3. update points
4. update savings
5. change status to accepted
6. refresh card/KPIs

When Skip is clicked:

1. call endpoint with `accept=false`
2. mark card skipped
3. do not add points

Avoid duplicate API calls using Streamlit session state.

## 7.6 Points wallet

Large metric cards:

```text
Points
245

Estimated Savings
₹86

Energy Shifted
12.4 kWh
```

## 7.7 Leaderboard

Show top 5 households.

Example:

```text
🏆 Neighbourhood leaderboard

1  Household 21    420 pts
2  Household 07    390 pts
3  Household 43    365 pts
4  Household 12    341 pts
5  Household 88    328 pts
```

Clearly label this as simulated/demo participation data.

## 7.8 Personal impact

Add:

```text
Your impact

12.4 kWh shifted
8.7 kg CO₂ avoided
₹86 estimated savings
```

---

# 8. Phase 5 — Member C: DISCOM dashboard

File:

```text
frontend/pages/2_DISCOM.py
```

This is the most important judge-facing screen.

## 8.1 Dashboard header

```text
PowerPool
Feeder Flexibility Command Center
```

Subheader:

```text
Hyderabad neighbourhood • 100 households
```

## 8.2 KPI row

Create six KPI cards:

```text
Peak Reduction
19.1%

Energy Shifted
42.8 kWh

Solar Self-Use
72.4%

CO₂ Avoided
30.0 kg

Participating Homes
67 / 100

Flexible Capacity
42 kW
```

Values must come from `/kpis` and `/flex-capacity`.

Do not hard-code production values.

## 8.3 Main before/after chart

This is the central visual.

Use Plotly.

Show:

- Before PowerPool demand
- After PowerPool demand
- Solar
- Feeder capacity

The visual story must be immediately obvious:

```text
BEFORE
             /\       OVERLOAD
            /  \
-----------/----\------------- capacity
          /      \

AFTER
          /\ 
---------/--\---------------- capacity
```

Use an annotation for:

```text
Peak reduced by 19.1%
```

Add shaded stress region.

## 8.4 Demand gap chart

Secondary chart:

- demand
- solar
- gap
- capacity

This explains why load shifting is necessary.

## 8.5 Flexible capacity widget

Large card:

```text
Available flexible capacity
42 kW

Next hour

67 households available
```

Button:

```text
Trigger Demand Response
```

Click behavior:

1. confirm with `st.button`
2. send `/dr-event`
3. show success result
4. refresh `/forecast`
5. refresh `/kpis`
6. update before/after chart
7. update flexible capacity
8. show number of nudges triggered

Success message:

```text
Demand-response event triggered.

57 households were nudged.
Estimated peak reduced to 165.8 kW.
```

## 8.6 Transformer risk indicator

Show:

```text
Transformer Risk

LOW
```

or:

```text
MEDIUM
```

or:

```text
HIGH
```

Suggested calculation:

```text
load / capacity

< 0.80  LOW
0.80–1.00 MEDIUM
> 1.00 HIGH
```

Use forecast peak or current selected slot.

## 8.7 Stress windows

Show:

```text
Today's critical windows

18:30 – 20:00   HIGH
20:00 – 21:30   HIGH
21:30 – 22:00   MEDIUM
```

Generate from `is_stress`.

---

# 9. Phase 6 — Frontend design system

Create reusable visual components instead of duplicating Streamlit code.

## Required components

```text
components/
├── cards.py
├── charts.py
├── nudge_card.py
├── traffic_light.py
├── status_badge.py
├── sidebar.py
└── formatters.py
```

## Design principles

- Mobile-friendly resident screen.
- Dense but readable DISCOM dashboard.
- Consistent spacing.
- Clear typography hierarchy.
- Avoid excessive text.
- Prefer cards, charts and status indicators.
- Use energy/grid visual language.
- Keep the interface professional enough for a hackathon judging screen.

Do not add a complex custom CSS framework.

Use Streamlit CSS only where it materially improves presentation.

---

# 10. Phase 7 — Language support

Implement three languages:

```text
English
Hindi
Telugu
```

Use a deterministic dictionary first.

Example:

```python
TRANSLATIONS = {
    "accept": {
        "en": "Accept",
        "hi": "स्वीकार करें",
        "te": "అంగీకరించండి"
    }
}
```

Required translated nudge example:

English:

```text
Run your washing machine between 1–2 PM.
Earn 15 points and save about ₹8.
```

Hindi:

```text
अपनी वॉशिंग मशीन दोपहर 1–2 बजे चलाएँ।
15 अंक कमाएँ और लगभग ₹8 बचाएँ।
```

Telugu:

```text
మీ వాషింగ్ మెషీన్‌ను మధ్యాహ్నం 1–2 గంటల మధ్య నడపండి.
15 పాయింట్లు సంపాదించి సుమారు ₹8 ఆదా చేయండి.
```

The UI must work even when no LLM API key exists.

LLM translation is optional.

---

# 11. Phase 8 — Backend integration

Once frontend screens work with mock data, connect them to the real FastAPI.

## Integration order

### Step 1

Connect:

```text
GET /forecast
```

Verify chart.

### Step 2

Connect:

```text
GET /kpis
GET /flex-capacity
```

Verify dashboard cards.

### Step 3

Connect:

```text
POST /optimize
```

Verify before/after chart.

### Step 4

Connect:

```text
GET /nudges/{household_id}
```

Verify resident cards.

### Step 5

Connect:

```text
POST /nudges/{id}/respond
```

Verify acceptance and points.

### Step 6

Connect:

```text
GET /leaderboard
```

Verify leaderboard.

### Step 7

Connect:

```text
POST /dr-event
```

Verify live DR action.

---

# 12. Phase 9 — Optimizer and KPI validation

The source algorithm is:

```text
For each stress slot, highest gap first:
    Find flexible appliances normally operating in that slot.
    Find candidate slots inside allowed window.
    Exclude stress slots.
    Prefer slots with high solar surplus.
    Respect capacity.
    Move the load.
    Create a nudge.
    Calculate points and savings.
    Update both curves.
```

Compliance should be simulated around 60–70%.

Use a configurable value:

```python
COMPLIANCE_RATE = 0.65
```

Do not pretend simulated acceptance is real-world observed behavior.

## Required KPI formulas

### Peak reduction

```python
peak_reduction_pct = (
    (peak_before - peak_after) / peak_before
) * 100
```

### CO₂ avoided

Use:

```python
co2_kg = kwh_shifted * GRID_EMISSION_FACTOR
```

Keep the emission factor configurable.

### Solar self-consumption

Define clearly:

```text
solar self-consumption =
solar energy consumed locally / total solar generation
```

### Savings

For each shifted kWh:

```python
saving_rs = shifted_kwh * tariff_difference
```

If no tariff model exists, use a clearly documented demo tariff.

---

# 13. Phase 10 — Forecast validation

The source plan expects demand forecasting at 15-minute resolution for the next 24 hours and recommends LightGBM.

Required feature categories:

```text
hour
minute
quarter_slot
weekday
is_weekend
temperature
lag_1
lag_4
lag_96
rolling_mean
rolling_std
```

Solar forecast should use:

```text
irradiance
cloud_cover
temperature
solar capacity
```

or the agreed physics formula:

```text
solar_kw =
irradiance_wm2
* panel_area_m2
* efficiency
/ 1000
```

## Metrics

Calculate:

```text
MAE
RMSE
MAPE
```

Report held-out results.

Target from the source plan:

```text
MAPE < 10%
```

Do not fabricate this value. If the model does not achieve it, show the actual result and use the baseline fallback.

## Baseline

Implement:

```text
same 15-minute slot average over previous 7 days
```

Use the baseline if LightGBM is unavailable or underperforms.

---

# 14. Phase 11 — Scenario engine

Add:

```text
Scenario: Sunny / Cloudy / Heatwave
```

The selected scenario must affect the entire story.

### Sunny

Expected:

```text
high midday solar
low evening solar
moderate demand
```

### Cloudy

Expected:

```text
lower solar
larger supply-demand gap
more stress
```

### Heatwave

Expected:

```text
higher temperature
higher demand
larger peak
more flexible capacity required
```

The scenario selector should be available from the main UI.

---

# 15. Phase 12 — Main Streamlit navigation

`frontend/Home.py` should act as the landing page.

Layout:

```text
POWERPOOL

Neighbourhood-scale load flexibility

[ Resident ]       [ DISCOM Dashboard ]

Today's status
████████ GREEN

Solar generation
...

Peak demand
...

Flexible capacity
...
```

Provide clear navigation to:

```text
Resident
DISCOM Dashboard
```

Add a small explanation:

```text
PowerPool shifts flexible household loads into solar-rich
hours to reduce feeder stress caused by renewable intermittency.
```

---

# 16. Phase 13 — Demo mode

Create a reliable demo mode.

Environment variable:

```text
DEMO_MODE=true
```

Demo mode must:

- work without backend
- work without internet
- load local deterministic scenario data
- provide realistic charts
- provide working Accept/Skip buttons
- provide simulated DR event
- update visible KPIs

The judges must be able to see the product even if deployment services fail.

---

# 17. Phase 14 — Automated testing

Create smoke tests.

## Test 1 — Backend starts

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Verify:

```text
GET /docs
```

## Test 2 — Forecast contract

Verify:

- HTTP 200
- 96 slots
- required fields present

## Test 3 — Optimize contract

Verify:

- before exists
- after exists
- peak_before exists
- peak_after exists
- reduction percentage is numeric

## Test 4 — Nudge response

Verify:

- pending -> accepted
- points increase
- skipped does not add points

## Test 5 — KPI consistency

Verify:

```text
peak_after <= peak_before
```

when the demo optimizer has available flexible loads.

## Test 6 — Frontend fallback

Stop backend and verify Streamlit still loads in DEMO_MODE.

## Test 7 — Scenario switching

Verify Sunny, Cloudy and Heatwave produce different solar/demand curves.

## Test 8 — DR event

Verify triggering DR changes the displayed result.

---

# 18. Phase 15 — Local run commands

Create or update README with:

## Install

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install:

```bash
pip install -r requirements.txt
```

## Seed data

```bash
python data/generator.py
```

or the repository's actual generator entry point.

## Start backend

```bash
uvicorn backend.main:app --reload --port 8000
```

## Start frontend

```bash
streamlit run frontend/Home.py
```

Document any actual entry-point differences discovered during repository audit.

---

# 19. Phase 16 — Environment configuration

Create:

```text
.env.example
```

Example:

```env
API_URL=http://localhost:8000
DEMO_MODE=true
DATABASE_PATH=data/powerpool.db
COMPLIANCE_RATE=0.65
GRID_EMISSION_FACTOR=0.70
```

Optional:

```env
OPEN_METEO_ENABLED=true
LLM_PROVIDER=
LLM_API_KEY=
```

Never commit actual API keys.

---

# 20. Phase 17 — Deployment readiness

## Backend

Preferred:

```text
Render
```

Alternative:

```text
Railway
```

## Frontend

Preferred:

```text
Streamlit Community Cloud
```

If deployment fails:

```text
local backend + ngrok
```

The frontend must read:

```env
API_URL=<deployed-backend-url>
```

Do not hard-code the deployment URL.

---

# 21. Phase 18 — Pitch implementation

Create:

```text
pitch/pitch_content.md
pitch/demo_script.md
```

## 2-minute demo

### 0:00–0:20 — Problem

Show:

```text
At evening peak:
Demand rises
Solar falls
Feeder approaches/exceeds capacity
```

### 0:20–0:50 — Forecast

Show:

- 24-hour demand
- solar
- gap
- stress window

Switch:

```text
Sunny -> Cloudy
```

Explain that the stress profile changes.

### 0:50–1:20 — Resident

Open resident screen.

Show:

```text
RED / peak period
```

Then show:

```text
Run washing machine 1–2 PM
+15 points
₹8 savings
```

Click:

```text
Accept
```

Show points increase.

### 1:20–1:45 — DISCOM

Open dashboard.

Click:

```text
Optimise
```

Then:

```text
Trigger Demand Response
```

Show:

```text
BEFORE -> AFTER
```

and KPI changes.

### 1:45–2:00 — Impact

Show:

```text
Peak reduction
Energy shifted
Solar self-consumption
CO₂ avoided
Households participating
```

End with:

```text
Zero resident hardware.
Feeder-by-feeder scalability.
```

---

# 22. Phase 19 — Pitch metrics

Compute all metrics from the actual simulation.

Target demonstration ranges from the source plan:

```text
Peak reduction: 15–25%
Solar self-consumption increase: +10–20 percentage points
Forecast MAPE: <10% target
CO₂: based on actual shifted kWh
```

These are demonstration targets, not guaranteed results.

Never insert invented performance numbers into the pitch.

---

# 23. Phase 20 — Judge Q&A preparation

Prepare factual answers for:

### Why would residents follow nudges?

Answer around:

- points
- estimated savings
- social leaderboard
- only flexible loads are targeted
- future integration with demand-response / time-of-use programmes

### Where does real data come from?

Explain:

- smart meters
- community solar inverters
- appliance self-reporting
- synthetic data is used for the prototype

### Why greedy optimisation?

Explain:

- fast
- explainable
- easy to debug
- suitable for hackathon prototype
- production upgrade can use LP / OR-Tools

### How does this relate to Schneider?

Explain that the concept can expose feeder demand-response signals to grid-management platforms and DERMS/ADMS-style workflows. Do not claim an actual Schneider integration unless one has been implemented.

### Privacy?

Explain:

- resident-facing data stays at community/app level
- DISCOM dashboard consumes aggregated feeder-level information
- prototype has no authentication because authentication is explicitly outside scope

---

# 24. Phase 21 — README

README must contain:

1. Project overview
2. Problem
3. Solution
4. Architecture
5. Repository structure
6. Tech stack
7. Data generation
8. Forecasting
9. Optimizer
10. API endpoints
11. Frontend
12. Demo scenarios
13. Metrics
14. Local setup
15. Deployment
16. Limitations
17. Future work
18. Team contribution

Include screenshots if available.

---

# 25. Phase 22 — Final integration checklist

Antigravity must not declare completion until every item below is verified.

## Data

- [ ] SQLite exists
- [ ] 60–100 households represented
- [ ] appliance data exists
- [ ] 15-minute load history exists
- [ ] weather data exists or cached data exists
- [ ] three scenarios exist

## ML

- [ ] demand forecast works
- [ ] solar forecast works
- [ ] gap calculation works
- [ ] stress windows work
- [ ] MAE calculated
- [ ] RMSE calculated
- [ ] MAPE calculated
- [ ] baseline exists

## Backend

- [ ] `/forecast`
- [ ] `/optimize`
- [ ] `/nudges/{household_id}`
- [ ] `/nudges/{id}/respond`
- [ ] `/kpis`
- [ ] `/leaderboard`
- [ ] `/dr-event`
- [ ] `/flex-capacity`

## Resident app

- [ ] traffic light
- [ ] forecast chart
- [ ] nudge cards
- [ ] Accept
- [ ] Skip
- [ ] points
- [ ] savings
- [ ] leaderboard
- [ ] English
- [ ] Hindi
- [ ] Telugu
- [ ] demo fallback

## DISCOM dashboard

- [ ] before/after chart
- [ ] KPI cards
- [ ] flexible capacity
- [ ] DR button
- [ ] transformer risk
- [ ] stress windows
- [ ] scenario selector
- [ ] demo fallback

## Integration

- [ ] frontend reads API_URL
- [ ] API errors do not crash UI
- [ ] Accept updates backend
- [ ] Optimize updates chart
- [ ] DR event updates results
- [ ] scenario changes affect visuals

## Pitch

- [ ] 2-minute demo script
- [ ] 3 scenarios
- [ ] actual metrics
- [ ] screenshots
- [ ] architecture diagram
- [ ] README
- [ ] backup demo plan

---

# 26. Phase 23 — Final demo test

Perform this exact sequence before declaring DONE.

### Test A

Start backend.

### Test B

Start Streamlit.

### Test C

Open Home.

### Test D

Select:

```text
Sunny
```

### Test E

Open Resident.

Verify:

```text
traffic light
forecast
nudge
points
leaderboard
```

### Test F

Accept one nudge.

Verify points change.

### Test G

Open DISCOM.

Verify:

```text
before chart
after chart
KPIs
flexible capacity
transformer risk
```

### Test H

Click:

```text
Optimise
```

Verify curve changes.

### Test I

Click:

```text
Trigger Demand Response
```

Verify:

```text
nudges triggered
peak reduced
KPIs refreshed
```

### Test J

Switch:

```text
Sunny -> Cloudy -> Heatwave
```

Verify charts change.

### Test K

Stop backend.

Reload in DEMO_MODE.

Verify the app still works.

---

# 27. Phase 24 — Git hygiene

Do not rewrite history or force-push unless explicitly requested.

Before final commit:

```bash
git status
git diff --stat
```

Check for:

- `.env`
- API keys
- generated secrets
- huge datasets
- unnecessary cache files
- `.venv`
- Python `__pycache__`

Ensure `.gitignore` includes:

```gitignore
.venv/
__pycache__/
*.pyc
.env
.streamlit/secrets.toml
*.log
.DS_Store
```

SQLite demo data may be committed if the project requires it and its size is reasonable.

---

# 28. Antigravity execution order

Execute in exactly this order:

```text
1. Audit repository
2. Write IMPLEMENTATION_STATUS.md
3. Identify existing A/B/C work
4. Lock API contracts
5. Build/repair API client
6. Build deterministic demo data/scenarios
7. Complete Resident UI
8. Complete DISCOM UI
9. Add reusable components
10. Add language support
11. Integrate real FastAPI
12. Validate optimizer/KPIs
13. Validate forecasting
14. Add fallback mode
15. Add tests
16. Run complete smoke test
17. Prepare README
18. Prepare pitch content
19. Verify deployment configuration
20. Run final 2-minute demo flow
21. Fix all blocking issues
22. Only then declare completion
```

---

# 29. Priority if time becomes limited

If implementation time is running out, use this order.

## Tier 1 — MUST NOT CUT

```text
1. Resident screen
2. DISCOM screen
3. Before/after chart
4. Forecast chart
5. Nudge Accept/Skip
6. KPI cards
7. Optimise action
8. Demo fallback
9. Three scenarios
10. End-to-end local demo
```

## Tier 2 — Keep if stable

```text
11. Leaderboard
12. DR trigger
13. Hindi/Telugu
14. CO₂
15. Savings
16. Transformer risk
```

## Tier 3 — Cut first

```text
17. LLM translation
18. Telegram
19. Chat assistant
20. Battery simulation
21. Advanced authentication
22. Real external integrations
```

---

# 30. Definition of DONE

The implementation is DONE only when:

> A judge can open the application, understand the problem visually, see a forecasted feeder stress period, see a resident receive a personalised load-shifting nudge, accept it, open the DISCOM dashboard, trigger optimisation/demand response, and immediately see the feeder's before/after curve and KPI improvements — without needing to understand the underlying code.

The final system must be:

- runnable
- deterministic in demo mode
- integrated
- visually polished
- API-contract compliant
- tested
- documented
- pitch-ready

Do not declare completion merely because files were created. Run the application and execute the final demo sequence.

---

# 31. Final Antigravity report

At the end, produce a concise report:

```text
POWERPOOL IMPLEMENTATION COMPLETE

Repository:
...

Backend:
PASS / FAIL

Resident UI:
PASS / FAIL

DISCOM UI:
PASS / FAIL

Forecasting:
PASS / FAIL

Optimizer:
PASS / FAIL

Scenario engine:
PASS / FAIL

API integration:
PASS / FAIL

Demo fallback:
PASS / FAIL

Tests:
X passed / Y failed

Local run:
...

Deployment:
...

Remaining issues:
...

Files changed:
...
```

If anything is still broken, explicitly report it instead of claiming completion.
