# PowerPool — API Contract & Member C Integration Guide

> **Version:** 1.2
> **Status:** FINAL INTEGRATED CONTRACT
> **Target Audience:** Member C (Streamlit Dashboard & Resident Interface), Backend & Integration Engineers
> **Base URL:** `http://127.0.0.1:8000` (Local Dev) / `https://<render-slug>.onrender.com` (Production)

---

## 1. Global Conventions & Standards

* **Content-Type:** `application/json` for all requests and responses.
* **Timestamps:** ISO-8601 strings without timezone offset: `YYYY-MM-DDTHH:MM:SS` (e.g. `2026-10-01T19:00:00`).
* **Household IDs:** **Strings** matching Member A format: `HH001`, `HH002`, ..., `HH100`. (Integer backward-compatibility is maintained, but frontend should always use strings).
* **Time Slots:** 96 slots per day, 15 minutes each:
  * `slot = 0` → `00:00`
  * `slot = 48` → `12:00`
  * `slot = 76` → `19:00`
  * `slot = 95` → `23:45`
  * Helper formula: `slot = hour * 4 + minute // 15`
* **Physical & Financial Units:**
  * Power: **kW** (kilowatts)
  * Energy: **kWh** (kilowatt-hours)
  * Tariffs & Savings: **Rs / ₹** (INR)
  * Carbon emission factor: **0.71 kg CO₂ / kWh**
  * Gamification points: **10 points per kWh shifted** (minimum 1 point)
* **CORS:** Enabled for all origins (`*`), supporting Streamlit browser fetch requests or Python-backend requests.
* **Error Format:** Standard FastAPI error responses:
  ```json
  { "detail": "Descriptive error message" }
  ```
  * `404 Not Found`: Nudge ID or resource does not exist.
  * `422 Unprocessable Entity`: Validation failure (wrong data type or missing field).
  * `503 Service Unavailable`: Service-layer constraint error (e.g., fewer than 96 slots available).

---

## 2. API Endpoints

### 2.1 Health & Environment
#### `GET /health`
Returns backend health status and data source mode.
* **Response:** `200 OK`
  ```json
  {
    "status": "ok",
    "mock_data": false
  }
  ```
  * `mock_data = false`: Real ML pipeline forecasts in use.
  * `mock_data = true`: Fallback seed mock data in use.

---

### 2.2 Feeder Forecast
#### `GET /forecast?date={YYYY-MM-DD}`
Returns 96 consecutive 15-minute slots representing the 24-hour demand and solar generation forecast for the neighbourhood feeder.
* **Query Parameters:**
  * `date` (string, optional): Target date filter (e.g. `2026-10-01`, `2026-10-02`, `2026-10-03`). If omitted, returns first available 96 slots.
* **Response:** `200 OK` (Array of 96 items)
  ```json
  [
    {
      "slot": 0,
      "time": "00:00",
      "demand_kw": 43.4,
      "solar_kw": 0.0,
      "capacity_kw": 170.0,
      "gap_kw": -126.6,
      "is_stress": false,
      "data_source": "model"
    },
    {
      "slot": 76,
      "time": "19:00",
      "demand_kw": 340.32,
      "solar_kw": 0.0,
      "capacity_kw": 170.0,
      "gap_kw": 170.32,
      "is_stress": true,
      "data_source": "model"
    }
  ]
  ```

---

### 2.3 Optimization & Scheduling
#### `POST /optimize` (Canonical) | `POST /schedule/run` (Alias)
Clears all existing nudges, resets household points to 0, and runs the greedy load-shifting algorithm to schedule flexible loads away from evening peak hours (18:00–21:00) into solar surplus windows (10:00–15:00).
* **Query Parameters:**
  * `date` (string, optional): `YYYY-MM-DD` date filter.
* **Response:** `200 OK`
  ```json
  {
    "before": [
      { "slot": 0, "time": "00:00", "demand_kw": 43.4 },
      { "slot": 76, "time": "19:00", "demand_kw": 340.32 }
    ],
    "after": [
      { "slot": 0, "time": "00:00", "demand_kw": 43.4 },
      { "slot": 76, "time": "19:00", "demand_kw": 252.12 }
    ],
    "nudges_created": 148,
    "peak_before_kw": 340.32,
    "peak_after_kw": 252.12,
    "peak_reduction_pct": 25.9
  }
  ```

---

### 2.4 Households
#### `GET /households`
Lists all enrolled households in the neighbourhood.
* **Response:** `200 OK`
  ```json
  [
    {
      "id": "HH001",
      "name": "Mid Household 1",
      "type": "mid",
      "block": "Block B",
      "language": "hi",
      "points": 0
    },
    {
      "id": "HH002",
      "name": "Low Household 2",
      "type": "low",
      "block": "Block C",
      "language": "te",
      "points": 0
    }
  ]
  ```

---

### 2.5 Nudges & Resident Schedule
#### `GET /nudges/{household_id}` (Canonical) | `GET /schedule/{household_id}` (Alias)
Returns all recommended load shifts (nudges) for a specific household, with localised text based on the resident's preferred language (`en`, `hi`, `te`).
* **Path Parameters:**
  * `household_id` (string): e.g. `HH001`
* **Response:** `200 OK`
  ```json
  [
    {
      "id": 1,
      "household_id": "HH001",
      "appliance_id": 1916,
      "appliance": "Washing machine",
      "from_slot": 74,
      "to_slot": 44,
      "from_time": "18:30",
      "to_time": "11:00",
      "kwh_shifted": 1.4,
      "points": 14,
      "saving_rs": 4.2,
      "status": "pending",
      "message": "आज अपनी वॉशिंग मशीन 18:30 के बजाय 11:00 बजे चलाएँ। 14 पॉइंट पाएँ और लगभग ₹4 बचाएँ।"
    }
  ]
  ```

#### `POST /nudges/{nudge_id}/respond`
Records a resident's decision to accept or skip a recommended load shift.
* **Path Parameters:**
  * `nudge_id` (integer): ID of the nudge.
* **Request Body:**
  ```json
  {
    "accept": true
  }
  ```
* **Response:** `200 OK`
  ```json
  {
    "nudge_id": 1,
    "status": "accepted",
    "household_points": 14
  }
  ```
* **Error:** `404 Not Found` if `nudge_id` does not exist.

---

### 2.6 Nudge Notification Preview
#### `POST /nudge/send`
Previews notification delivery payload for a household.
* **Request Body:**
  ```json
  {
    "household_id": "HH001",
    "nudge_id": null
  }
  ```
* **Response:** `200 OK`
  ```json
  {
    "household_id": "HH001",
    "nudges_queued": 1,
    "channel": "api_only",
    "delivered": false,
    "messages": [
      "आज अपनी वॉशिंग मशीन 18:30 के बजाय 11:00 बजे चलाएँ। 14 पॉइंट पाएँ और लगभग ₹4 बचाएँ।"
    ]
  }
  ```

---

### 2.7 Impact KPIs & Metrics
#### `GET /kpis` (Canonical) | `GET /metrics` (Alias)
Aggregate feeder impact metrics for the DISCOM dashboard.
* **Query Parameters:**
  * `date` (string, optional): `YYYY-MM-DD`
* **Response:** `200 OK`
  ```json
  {
    "peak_before_kw": 340.32,
    "peak_after_kw": 252.12,
    "peak_reduction_pct": 25.9,
    "kwh_shifted": 127.24,
    "rs_saved": 381.72,
    "co2_kg": 90.34,
    "solar_self_use_pct_before": 96.1,
    "solar_self_use_pct": 98.4,
    "participants": 32,
    "total_households": 100,
    "transformer_risk": "HIGH"
  }
  ```
* `transformer_risk`:
  * `"LOW"`: `peak_after_kw / feeder_capacity <= 0.95`
  * `"MEDIUM"`: `0.95 < peak_after_kw / feeder_capacity <= 1.05`
  * `"HIGH"`: `peak_after_kw / feeder_capacity > 1.05`

---

### 2.8 Gamification Leaderboard
#### `GET /leaderboard?limit={limit}`
Returns the resident leaderboard ranked by accumulated reward points.
* **Query Parameters:**
  * `limit` (integer, default: 10)
* **Response:** `200 OK`
  ```json
  [
    {
      "rank": 1,
      "household_id": "HH001",
      "name": "Mid Household 1",
      "block": "Block B",
      "points": 45
    },
    {
      "rank": 2,
      "household_id": "HH004",
      "name": "Mid Household 4",
      "block": "Block D",
      "points": 32
    }
  ]
  ```

---

### 2.9 Demand-Response (DR) Emergency Event
#### `POST /dr-event?date={YYYY-MM-DD}`
Schedules an urgent targeted demand reduction during grid emergencies on top of existing nudges.
* **Request Body:**
  ```json
  {
    "start_slot": 74,
    "end_slot": 82,
    "target_kw": 25.0
  }
  ```
* **Response:** `200 OK`
  ```json
  {
    "nudges_created": 18,
    "kw_reduced_expected": 24.5,
    "after": [
      { "slot": 74, "time": "18:30", "demand_kw": 227.62 }
    ]
  }
  ```

---

### 2.10 Hourly Flexible Capacity
#### `GET /flex-capacity`
Returns available shiftable capacity per hour (in kW) for appliances not yet nudged.
* **Response:** `200 OK` (24 items, hours 00 through 23)
  ```json
  [
    { "hour": 0, "time": "00:00", "flexible_kw": 0.0 },
    { "hour": 18, "time": "18:00", "flexible_kw": 48.9 }
  ]
  ```

---

### 2.11 Interactive Demo Controls
#### `POST /demo/simulate-responses?rate={rate}&seed={seed}`
Simulates random resident compliance by accepting approximately `rate` (default: 0.65) fraction of all pending nudges.
* **Response:** `200 OK`
  ```json
  { "processed": 148, "accepted": 96 }
  ```

---

## 3. Canonical vs. Planned Alias Endpoint Mapping

| Feature / Intent | Canonical Endpoint | Planned External Alias | Method | Notes |
|---|---|---|---|---|
| Run Grid Optimization | `/optimize` | `/schedule/run` | POST | Returns before/after curves |
| Household Nudges | `/nudges/{household_id}` | `/schedule/{household_id}` | GET | Pass string ID: `HH001` |
| Grid Impact KPIs | `/kpis` | `/metrics` | GET | Peak reduction, Rs, CO₂ |

---

## 4. Member C Streamlit Integration Guide

### 4.1 Running the Backend and Dashboard Side-by-Side

In Terminal 1 (Start FastAPI Backend):
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

In Terminal 2 (Start Streamlit App):
```bash
streamlit run frontend/app.py
```

### 4.2 Streamlit Client Utility Code Snippet

Use this helper pattern in your Streamlit app:

```python
import os
import requests
import streamlit as st

API_BASE = os.getenv("API_URL", "http://127.0.0.1:8000")

@st.cache_data(ttl=5)
def get_forecast(date="2026-10-01"):
    resp = requests.get(f"{API_BASE}/forecast", params={"date": date}, timeout=5)
    resp.raise_for_status()
    return resp.json()

@st.cache_data(ttl=5)
def get_kpis(date="2026-10-01"):
    resp = requests.get(f"{API_BASE}/kpis", params={"date": date}, timeout=5)
    resp.raise_for_status()
    return resp.json()

def run_optimizer(date="2026-10-01"):
    resp = requests.post(f"{API_BASE}/optimize", params={"date": date}, timeout=10)
    resp.raise_for_status()
    return resp.json()

def get_household_nudges(household_id="HH001"):
    resp = requests.get(f"{API_BASE}/nudges/{household_id}", timeout=5)
    resp.raise_for_status()
    return resp.json()

def respond_to_nudge(nudge_id: int, accept: bool):
    resp = requests.post(f"{API_BASE}/nudges/{nudge_id}/respond", json={"accept": accept}, timeout=5)
    resp.raise_for_status()
    return resp.json()
```

### 4.3 Feature-to-Endpoint Mapping Table for Dashboard

| Streamlit Dashboard Component | Recommended Endpoint | Display Recommendation |
|---|---|---|
| **Feeder Demand & Solar Chart** | `GET /forecast?date={date}` | Line chart with `demand_kw` and `solar_kw` over 96 slots; dashed line at `capacity_kw` (170 kW); highlight `is_stress == true`. |
| **Grid Impact KPI Cards** | `GET /kpis` | Metric cards: Peak Reduction %, Energy Shifted (kWh), Financial Savings (₹), CO₂ Saved (kg), Transformer Risk badge (`LOW`/`MEDIUM`/`HIGH`). |
| **Optimization Action Button** | `POST /optimize` | Triggers scheduler; update chart with `before` and `after` curve comparison. |
| **Resident Profile Selector** | `GET /households` | Selectbox showing `name` and `block`, passing string `id` (e.g. `HH001`). |
| **Resident Nudge Cards** | `GET /nudges/{household_id}` | Cards displaying appliance name, `message`, time window shift, reward points, and saving ₹. |
| **Accept / Skip Action** | `POST /nudges/{nudge_id}/respond` | Buttons triggering instant points badge increment and status badge update. |
| **Leaderboard Table** | `GET /leaderboard?limit=10` | Top residents ranked by points with block identifiers. |
| **Emergency DR Simulator** | `POST /dr-event` | Sliders for start slot, end slot, target kW reduction. |
| **Hourly Flex Gauge** | `GET /flex-capacity` | Bar chart of flexible kW available per hour. |
