# PowerPool — Provisional Backend Data Contract

> **Status:** PROVISIONAL — SUBJECT TO AGREEMENT WITH MEMBER A AND MEMBER C
> **Author:** Member B
> **Branch:** `backend`
> **Last updated:** 2026-10-01
>
> All interfaces marked **PROVISIONAL** are unconfirmed assumptions. Do not
> treat them as finalised until Member A and Member C have reviewed and agreed.

---

## 1. Global Conventions

### 1.1 Timestamp Format

| Property | Value |
|---|---|
| Format | ISO-8601 string: `YYYY-MM-DDTHH:MM:SS` |
| Example | `2026-10-01T19:30:00` |
| Timezone | **PROVISIONAL** — no timezone suffix in current mock data |
| Assumed timezone | Indian Standard Time (UTC+05:30) |
| Stored as | SQLite `TEXT` column |
| **NEEDS AGREEMENT** | Whether timestamps use UTC+00:00 suffix or bare IST strings |

### 1.2 Slot Convention

| Property | Value |
|---|---|
| Slot count per day | 96 |
| Slot duration | 15 minutes |
| Slot 0 | 00:00 (midnight) |
| Slot 95 | 23:45 |
| kW to kWh per slot | kW x 0.25 |

### 1.3 Energy and Power Units

| Quantity | Unit |
|---|---|
| Instantaneous power | kW (all *_kw fields) |
| Energy per slot | kWh = power_kw x 0.25 |
| Monetary values | Indian Rupees (saving_rs) |
| CO2 factor | 0.71 kg CO2/kWh (configurable via CO2_PER_KWH) |

---

## 2. Database Schema

SQLite at `data/powerpool.db` (configurable via `DB_PATH` env var).

### 2.1 households

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER PRIMARY KEY | Not null |
| name | TEXT | Not null |
| type | TEXT | low or mid or shop |
| block | TEXT | e.g. Block A |
| language | TEXT | en or hi or te, default en |
| points | INTEGER | Default 0 |

### 2.2 appliances

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER PRIMARY KEY | |
| household_id | INTEGER | FK to households.id |
| name | TEXT | Must match translation dict |
| power_kw | REAL | > 0 |
| duration_slots | INTEGER | > 0, <= 96 |
| flexible | INTEGER | 0 or 1 |
| earliest_slot | INTEGER | 0-95 |
| latest_slot | INTEGER | 0-95 |
| usual_slot | INTEGER | 0-95, in stress window for flex appliances |

### 2.3 forecast (PROVISIONAL — Member A owns data generation)

| Column | Type | Constraints |
|---|---|---|
| timestamp | TEXT | ISO-8601, 96 distinct values per date |
| demand_kw | REAL | >= 0, aggregate neighbourhood demand |
| solar_kw | REAL | >= 0, aggregate solar generation |
| capacity_kw | REAL | = 170.0 (FEEDER_CAPACITY_KW) |
| gap_kw | REAL | demand_kw - solar_kw - capacity_kw |
| is_stress | INTEGER | 0 or 1; 1 if gap_kw > 0 |

96 rows required per date. Missing rows cause HTTP 503.
Demo dates: 2026-10-01 (sunny), 2026-10-02 (cloudy), 2026-10-03 (heatwave).

### 2.4 nudges (Member B owns entirely)

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| household_id | INTEGER | FK to households.id |
| appliance_id | INTEGER | FK to appliances.id |
| from_slot | INTEGER | 0-95 |
| to_slot | INTEGER | 0-95 |
| kwh_shifted | REAL | >= 0 |
| points | INTEGER | >= 0 |
| saving_rs | REAL | >= 0 |
| status | TEXT | pending or accepted or skipped |
| source | TEXT | optimize or dr |

### 2.5 load_history (PROVISIONAL — Member A will populate)

| Column | Type |
|---|---|
| household_id | INTEGER |
| timestamp | TEXT |
| kwh | REAL |

Currently empty. No backend API endpoint exposes this table yet.

### 2.6 weather (PROVISIONAL — Member A will populate via Open-Meteo/Hyderabad)

| Column | Type |
|---|---|
| timestamp | TEXT |
| temp_c | REAL |
| cloud_cover | REAL (0.0-1.0) |
| irradiance_wm2 | REAL |

Currently empty. No backend API endpoint exposes this table yet.

---

## 3. API Request and Response Schemas

Base URL: http://localhost:8000 (dev) / Render URL (prod)
All responses: JSON. Error format: {"detail": "message"} with HTTP 4xx/5xx.

### 3.1 GET /health

Response:
  { "status": "ok", "mock_data": true }

mock_data: true when MOCK_DATA=true in env; flip to false when Member A pipeline is live.

### 3.2 GET /forecast?date=YYYY-MM-DD

Returns 96 x 15-minute slots. Returns HTTP 503 if fewer than 96 rows exist.

Response array item:
  {
    "slot": 0,
    "time": "00:00",
    "demand_kw": 75.0,
    "solar_kw": 0.0,
    "capacity_kw": 170.0,
    "gap_kw": -95.0,
    "is_stress": false,
    "data_source": "mock"
  }

data_source: "mock" or "model" — PROVISIONAL, NEEDS TEAM AGREEMENT.
Member C uses this for a freshness badge.

### 3.3 POST /optimize  (alias: POST /schedule/run)

Clears nudges, runs greedy scheduler, creates new nudges.
Optional query param: ?date=YYYY-MM-DD

Response:
  {
    "before": [{"slot": 0, "time": "00:00", "demand_kw": 75.0}],
    "after":  [{"slot": 0, "time": "00:00", "demand_kw": 71.2}],
    "nudges_created": 143,
    "peak_before_kw": 196.0,
    "peak_after_kw": 163.0,
    "peak_reduction_pct": 16.8
  }

peak_reduction_pct is a simulated projection, not a measured real-world result.

### 3.4 GET /schedule/{household_id}  (alias: GET /nudges/{household_id})

Returns all nudges for one household (all statuses).
Returns [] (empty list, not 404) for unknown households or no nudges.

Response array item:
  {
    "id": 1,
    "household_id": 12,
    "appliance_id": 34,
    "appliance": "Washing machine",
    "from_slot": 78, "to_slot": 52,
    "from_time": "19:30", "to_time": "13:00",
    "kwh_shifted": 0.5,
    "points": 5,
    "saving_rs": 1.5,
    "status": "pending",
    "message": "Run your Washing machine at 13:00 today instead of 19:30. Earn 5 points and save about Rs 2."
  }

### 3.5 POST /nudges/{nudge_id}/respond

Request:  { "accept": true }
Response: { "nudge_id": 1, "status": "accepted", "household_points": 55 }
Error:    HTTP 404 if nudge_id does not exist.

### 3.6 GET /metrics  (alias: GET /kpis)

All values are simulated projections, not measured real-world results.

Response:
  {
    "peak_before_kw": 196.0, "peak_after_kw": 163.0,
    "peak_reduction_pct": 16.8, "kwh_shifted": 99.0,
    "rs_saved": 297.0, "co2_kg": 70.3,
    "solar_self_use_pct_before": 78.0, "solar_self_use_pct": 92.0,
    "participants": 22, "total_households": 80,
    "transformer_risk": "MEDIUM"
  }

transformer_risk: LOW or MEDIUM or HIGH (based on peak_after / feeder_capacity).

### 3.7 GET /leaderboard?limit=10

Response array item:
  { "rank": 1, "household_id": 5, "name": "Reddy #5", "block": "Block B", "points": 120 }

Only id, name, block, points are exposed. No private household data.

### 3.8 POST /nudge/send

PROVISIONAL — NEEDS TEAM AGREEMENT on real Telegram push vs preview only.

Request:
  { "household_id": 12, "nudge_id": null }

household_id: required, > 0.
nudge_id: optional; null = all pending nudges for the household.

Response:
  {
    "household_id": 12, "nudges_queued": 3,
    "channel": "api_only", "delivered": false,
    "messages": ["Run your Washing machine at 13:00..."]
  }

channel: "api_only" unless TELEGRAM_TOKEN is set.
delivered: always false in current implementation (no real push).

### 3.9 GET /households

Response array item:
  { "id": 1, "name": "Sharma #1", "type": "low", "block": "Block A", "language": "en", "points": 50 }

### 3.10 POST /dr-event

Request:
  { "start_slot": 72, "end_slot": 84, "target_kw": 10.0 }

start_slot, end_slot: int 0-95. target_kw: float > 0.

Response:
  { "nudges_created": 21, "kw_reduced_expected": 8.0, "after": [...96 SlotPoints...] }

### 3.11 GET /flex-capacity

Response (24 items):
  [{ "hour": 17, "time": "17:00", "flexible_kw": 42.0 }]

---

## 4. Optimizer Interface

PROVISIONAL — current implementation is a greedy mock.
Member A ML optimizer interface is not yet defined.

Current internal signature:
  greedy_schedule(
      demand: list[float],       # 96 kW values
      solar: list[float],        # 96 kW values
      appliances: list[dict],    # flexible=1 rows from appliances table
      capacity: float,           # FEEDER_CAPACITY_KW (170.0)
      target_slots: list[int],   # DR window or None
      target_kw: float,          # DR target or None
      exclude_ids: set[int],     # already-nudged appliance IDs
      compliance: float,         # 0.65
  ) -> (list[Shift], list[float])

NEEDS MEMBER A to confirm:
  1. Function or HTTP service?
  2. Input format?
  3. Output format?
  4. Scheduling constraints enforced?
  5. Metrics returned?

---

## 5. Member A Integration Requirements

### 5.1 What Member A Will Deliver

Based on origin/data-ml plan (PowerPool_Member_A_Antigravity_Implementation_Plan.md):

  - SQLite data/powerpool.db with all 6 tables populated
  - 96 forecast rows per date for 2026-10-01, 2026-10-02, 2026-10-03
  - Scenarios: sunny (10-01), cloudy (10-02), heatwave (10-03)
  - LightGBM demand forecasting model with deterministic fallback
  - Open-Meteo integration for Hyderabad weather
  - Solar model (three scenarios)
  - MAPE < 10% accuracy target
  - data/sample_load.csv
  - data-ml/requirements.txt (separate from backend/requirements.txt)

### 5.2 Forecast Table Write Protocol

INSERT INTO forecast (timestamp, demand_kw, solar_kw, capacity_kw, gap_kw, is_stress)
VALUES ('2026-10-01T06:00:00', 142.3, 12.5, 170.0, -40.2, 0);

Formulas Member A must use:
  gap_kw    = demand_kw - solar_kw - capacity_kw
  is_stress = 1 if gap_kw > 0 else 0
  kWh/slot  = kW x 0.25

### 5.3 Handoff Checklist (Member A to Member B)

  [ ] Run python -m backend.seed_mock first
  [ ] Write 96 rows per date to forecast table
  [ ] Verify: SELECT COUNT(*) FROM forecast WHERE timestamp LIKE '2026-10-01%' = 96
  [ ] Set MOCK_DATA=false in .env
  [ ] Confirm GET /forecast?date=2026-10-01 returns 96 rows with "data_source":"model"
  [ ] Confirm POST /optimize reduces peak with real data
  [ ] Provide: MAPE, peak kW, model type, any new env vars

### 5.4 Confirmed Interface Agreements

  DB file:           data/powerpool.db
  Forecast columns:  timestamp, demand_kw, solar_kw, capacity_kw, gap_kw, is_stress
  Slots per day:     96
  Slot duration:     15 minutes
  Feeder capacity:   170.0 kW (via FEEDER_CAPACITY_KW)
  Peak constraint:   At least one scenario must have max demand > 170 kW
  Appliance names:   Must match Member B translation dictionary

### 5.5 Open Questions for Member A

  A-1: Will scripts write directly to data/powerpool.db or output CSV for B to import?
  A-2: Will Member A run seed_mock.py first or generate households independently?
  A-3: Timestamp timezone: bare IST or UTC+00:00?
  A-4: Will capacity_kw be hardcoded to 170 or read from env?
  A-5: Will data-ml/requirements.txt exist separately or merge into backend/requirements.txt?
  A-6: Is the ML optimizer a replaceable Python function for Member B to plug in?

---

## 6. Member C Integration Notes

### 6.1 Appliance Name Translation Mapping (required for nudge text)

  Washing machine       -> Hindi: washing machine (hi), Telugu: washing machine (te)
  Water pump            -> supported
  Inverter charging     -> supported
  Geyser                -> supported
  Iron                  -> supported
  E-rickshaw charging   -> supported

### 6.2 Endpoints Member C Consumes

  GET  /forecast              demand/solar chart (96 slots)
  POST /schedule/run          run optimizer, get before/after curves
  GET  /schedule/{home_id}    per-household nudge list with messages
  GET  /metrics               11 KPI fields for DISCOM dashboard
  GET  /leaderboard           ranked households by points
  POST /nudges/{id}/respond   accept or skip a nudge
  POST /nudge/send            nudge text preview
  GET  /flex-capacity         24-hour flexible load heatmap
  POST /dr-event              trigger demand-response event

### 6.3 Open Questions for Member C

  C-1: Should data_source field show a freshness badge?
  C-2: Should /nudge/send trigger real Telegram push or stay preview?
  C-3: Canonical paths: /schedule/run or /optimize? Both work.
  C-4: Is authentication needed for any endpoint?
  C-5: Will frontend call /demo/reseed for demo resets?

---

## 7. Validation Rules

  slot:               integer 0-95
  demand_kw, solar_kw: >= 0.0
  capacity_kw:        > 0.0 (currently 170.0)
  gap_kw:             any real (negative = surplus)
  is_stress:          0 or 1 in DB; bool in API
  kwh_shifted:        >= 0.0
  points:             >= 0 integer
  saving_rs:          >= 0.0
  start_slot/end_slot: 0-95 (Pydantic Field(ge=0, le=95))
  target_kw:          > 0.0 (Pydantic Field(gt=0))
  household_id in /nudge/send: > 0
  status:             pending, accepted, or skipped only

---

## 8. Error Response Format

  { "detail": "human-readable message" }

  200: success
  422: Pydantic validation failure
  404: resource not found
  503: service-layer error (e.g. fewer than 96 forecast slots)

Stack traces and SQLite internals are never exposed.

---

## 9. Current Assumptions and Risks

  Assumption: All times are IST bare strings — RISK: Medium
    If Member A uses UTC, date filtering breaks at midnight boundaries.

  Assumption: capacity_kw = 170 kW constant — RISK: Low
    Configurable via FEEDER_CAPACITY_KW env var.

  Assumption: SQLite sufficient for MVP — RISK: Low
    Multi-worker Render deployments need single-worker mode.

  Assumption: 80 households in mock data — RISK: Low
    Member A plan specifies 60-100; backend adapts to any count.

  Assumption: Compliance rate = 0.65 — RISK: Low
    Configurable via COMPLIANCE env var.

  Assumption: CO2 = 0.71 kg/kWh — RISK: Low
    Configurable via CO2_PER_KWH env var.

  Assumption: SQLite on Render free tier is ephemeral — RISK: HIGH
    DB wiped on every redeploy. App auto-reseeds on cold start but
    nudge history and accepted responses are lost.
    Mitigation: Use Render Persistent Disk or Postgres before production.
