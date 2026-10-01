# PowerPool — Member 3 → Member 2 Integration Handoff

## Purpose

This document is the integration contract for connecting the current Streamlit Resident UI and DISCOM Dashboard with Member 2's ML/backend pipeline.

The current Streamlit application has been reported as running locally with FastAPI and Streamlit, and the core UI interactions have been manually tested. The goal now is to integrate the real ML/backend outputs without changing the frontend UX or API contract unnecessarily.

---

# 1. Current frontend structure

```text
powerpool/
├── backend/
├── data/
├── frontend/
│   ├── __init__.py
│   ├── api_client.py
│   ├── Home.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── cards.py
│   │   ├── charts.py
│   │   ├── nudge_card.py
│   │   ├── sidebar.py
│   │   ├── status_badge.py
│   │   └── traffic_light.py
│   └── pages/
│       ├── __init__.py
│       ├── 1_Resident.py
│       └── 2_DISCOM.py
├── ml/
├── pitch/
├── tests/
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

The frontend is Streamlit.

---

# 2. Important architecture decision

## Production/demo architecture

```text
ML + database
      |
      v
FastAPI backend
      |
      | REST / JSON
      v
Streamlit frontend
      |
      +---- Resident
      |
      +---- DISCOM
```

The frontend should NOT directly query SQLite for production dashboard data.

The frontend should communicate through the FastAPI API.

The frontend API client reads the backend URL from:

```env
API_URL=http://localhost:8000
```

A demo/fallback mode exists so the UI can continue to demonstrate the product if the backend is unavailable.

---

# 3. Required backend endpoints

The frontend expects these endpoints.

## 3.1 Forecast

```http
GET /forecast?date=YYYY-MM-DD
```

Expected response:

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

Requirements:

- 96 slots for a 24-hour forecast
- 15-minute resolution
- `demand_kw`
- `solar_kw`
- `capacity_kw`
- `gap_kw`
- `is_stress`

The frontend uses this for:
- resident forecast chart
- traffic-light status
- DISCOM forecast
- stress-window display

---

# 4. Optimize endpoint

```http
POST /optimize
```

Expected response:

```json
{
  "before": [
    {
      "slot": 76,
      "time": "19:00",
      "demand_kw": 182.4
    }
  ],
  "after": [
    {
      "slot": 76,
      "time": "19:00",
      "demand_kw": 151.0
    }
  ],
  "nudges_created": 143,
  "peak_before_kw": 196.2,
  "peak_after_kw": 158.7,
  "peak_reduction_pct": 19.1,
  "kwh_shifted": 42.8
}
```

Important:

The values above are the contract/example shape. Do not hard-code these numbers. The backend must calculate the actual values from the current data/model.

---

# 5. Resident nudges

## Get nudges

```http
GET /nudges/{household_id}
```

Expected:

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

The Resident UI displays:
- appliance
- original time
- recommended time
- energy shifted
- savings
- points
- message
- status

---

# 6. Nudge response

```http
POST /nudges/{id}/respond
```

Request:

```json
{
  "accept": true
}
```

or:

```json
{
  "accept": false
}
```

Expected response:

```json
{
  "id": 101,
  "status": "accepted",
  "points_added": 15,
  "saving_rs": 8.0,
  "message": "Great! Your load was shifted successfully."
}
```

Rules:

- Accept → update status and add points/savings
- Skip → update status without awarding points
- Repeated clicks should not double-award points

---

# 7. KPI endpoint

```http
GET /kpis
```

Expected:

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

The dashboard uses these values for KPI cards.

Important:

Do not return presentation-only hard-coded values.

The backend should calculate:

```text
peak reduction
kWh shifted
solar self-consumption
CO2 avoided
participants
```

from the actual simulation/model output.

---

# 8. Leaderboard

```http
GET /leaderboard
```

Expected:

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

The Resident UI displays the top households.

---

# 9. Flexible capacity

```http
GET /flex-capacity
```

Expected:

```json
{
  "window": "next_hour",
  "available_kw": 42.0,
  "households_available": 67
}
```

The DISCOM dashboard uses this for the flexible-capacity card.

---

# 10. Demand-response event

```http
POST /dr-event
```

Request:

```json
{
  "start_slot": 76,
  "end_slot": 88,
  "target_kw": 170
}
```

Expected:

```json
{
  "success": true,
  "nudges_created": 57,
  "target_kw": 170,
  "available_flexible_kw": 42.0,
  "peak_after_kw": 165.8
}
```

After this call the frontend refreshes:
- forecast
- KPIs
- flexible capacity
- dashboard chart

---

# 11. Frontend workflow

## Resident

```text
Load Resident page
      ↓
GET /forecast
      ↓
Calculate/display traffic-light state
      ↓
GET /nudges/{household_id}
      ↓
Display personalised nudges
      ↓
Resident clicks Accept/Skip
      ↓
POST /nudges/{id}/respond
      ↓
Refresh points/savings/nudge status
```

## DISCOM

```text
Load dashboard
      ↓
GET /forecast
GET /kpis
GET /flex-capacity
      ↓
Display feeder state
      ↓
POST /optimize
      ↓
Display before vs after
      ↓
POST /dr-event
      ↓
Refresh forecast/KPIs/flexible capacity
```

---

# 12. Data model expected by the product

SQLite tables specified by the project:

## households

```text
id
name
type
block
language
points
```

Household types:

```text
low
mid
shop
```

## appliances

```text
id
household_id
name
power_kw
duration_slots
flexible
earliest_slot
latest_slot
usual_slot
```

## load_history

```text
household_id
timestamp
kwh
```

15-minute resolution.

## weather

```text
timestamp
temp_c
cloud_cover
irradiance_wm2
```

## forecast

```text
timestamp
demand_kw
solar_kw
capacity_kw
gap_kw
is_stress
```

## nudges

```text
id
household_id
appliance_id
from_slot
to_slot
kwh_shifted
points
saving_rs
status
```

Status:

```text
pending
accepted
skipped
```

---

# 13. Frontend data requirements

## Resident

Required:

```text
forecast
current stress state
nudges
points
savings
leaderboard
personal energy shifted
personal CO2 impact
language
```

## DISCOM

Required:

```text
forecast demand
solar
capacity
before curve
after curve
peak before
peak after
peak reduction
kWh shifted
solar self-use
CO2
participants
flexible capacity
transformer risk
stress windows
```

---

# 14. Scenario support

The frontend supports:

```text
Sunny
Cloudy
Heatwave
```

The scenario should affect the underlying backend/model output.

Expected conceptual behavior:

### Sunny

```text
high midday solar
moderate demand
clear midday surplus
evening solar decline
```

### Cloudy

```text
lower solar
larger supply-demand gap
more stress
```

### Heatwave

```text
higher temperature
higher demand
larger peak
greater feeder stress
```

Do not merely change the scenario label while returning identical backend data.

---

# 15. Environment variables

Expected:

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

Never commit real secrets.

---

# 16. Local setup

From repository root:

```powershell
python -m venv .venv
```

Activate on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install:

```powershell
pip install -r requirements.txt
```

Seed data if needed:

```powershell
python -m data.seed_demo
```

Start backend:

```powershell
uvicorn backend.main:app --reload --port 8000
```

Start frontend in another terminal:

```powershell
streamlit run frontend/Home.py
```

Frontend:

```text
http://localhost:8501
```

Backend docs:

```text
http://127.0.0.1:8000/docs
```

---

# 17. Integration rules for Member 2

## Do

- Integrate the existing ML pipeline behind the agreed API.
- Preserve endpoint paths.
- Preserve JSON field names.
- Return 96 forecast slots.
- Return numeric values rather than formatted strings.
- Calculate KPIs from real model/data output.
- Keep the frontend independent of SQLite.
- Test endpoints independently using FastAPI `/docs`.
- Tell Member 3 if an endpoint contract must change before changing it.

## Do not

- Rewrite the Streamlit UI unnecessarily.
- Add direct SQLite queries to frontend pages.
- Rename API fields without coordination.
- Return UI-formatted strings where numbers are expected.
- Hard-code demo KPI values in production API responses.
- Remove demo fallback.
- add authentication/payment/hardware integration; those are outside the hackathon prototype scope.

---

# 18. Integration acceptance criteria

Integration is complete when:

```text
[ ] ML pipeline generates demand forecast
[ ] ML/physics pipeline generates solar forecast
[ ] /forecast returns 96 slots
[ ] /optimize uses current backend data
[ ] /kpis uses calculated values
[ ] /nudges/{household_id} returns real generated nudges
[ ] Accept updates backend state
[ ] Skip updates backend state
[ ] /leaderboard reflects points
[ ] /flex-capacity returns calculated flexible capacity
[ ] /dr-event changes the DR result
[ ] Resident UI renders backend output
[ ] DISCOM UI renders backend output
[ ] Sunny/Cloudy/Heatwave produce different outputs
[ ] Demo fallback still works
[ ] pytest passes
[ ] Streamlit loads without runtime errors
```

---

# 19. Important metric validation

The project specification uses a sample peak-reduction response of 19.1%, but this is an example contract value, not a guaranteed measured result.

Before using any number in the pitch:

```text
Run actual optimizer
        ↓
Capture peak_before
        ↓
Capture peak_after
        ↓
Calculate:
((peak_before - peak_after) / peak_before) * 100
        ↓
Use actual result
```

Do not fabricate model metrics.

---

# 20. Demo scenarios

The final demo should show:

```text
1. Sunny
2. Cloudy
3. Heatwave
```

Recommended live flow:

```text
Problem
  ↓
24-hour forecast
  ↓
Resident sees nudge
  ↓
Accept nudge
  ↓
DISCOM dashboard
  ↓
Optimise
  ↓
Before vs After
  ↓
Trigger DR
  ↓
Updated KPIs
```

Target demo duration from the project specification:

```text
2 minutes
```

---

# 21. Handoff strategy

Do NOT copy the entire project through chat.

Use Git.

Recommended branch:

```text
member3-frontend-integration
```

Push the current working frontend and shared contracts to the repository.

Member 2 should then:

```bash
git fetch origin
git checkout member3-frontend-integration
```

or merge/cherry-pick the required commits into their integration branch.

Before merging, Member 2 should verify the API contracts against the frontend API client.

---

# 22. Current known status

Reported as working:

```text
FastAPI startup       PASS
Streamlit startup     PASS
Home                  PASS
Resident              PASS
DISCOM                PASS
Resident interactions PASS
DISCOM interactions   PASS
Pytest                14/14 previously passed
```

There has also been a VS Code/Pylance diagnostic shown under `streamlit` in `1_Resident.py`. This does not currently prevent the application from running, but the Python interpreter/environment should be checked before deployment.

Useful check:

```powershell
python -c "import streamlit; print(streamlit.__version__)"
```

If VS Code still shows an unresolved `streamlit` import while the command above works, select the same `.venv` interpreter in VS Code/Pylance.

---

# 23. Final integration principle

The frontend contract is the interface between Member 2 and Member 3.

Member 2 can replace the internal ML/optimization implementation as long as the REST responses remain compatible.

The Streamlit UI should not need to know whether the backend uses:

- LightGBM
- baseline forecasting
- another model
- a physics-based solar calculation
- greedy optimization

It only needs the agreed API contract and valid calculated outputs.
