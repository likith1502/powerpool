# PowerPool — API Contract

Base URL: `http://localhost:8000` (dev) / Render URL (prod)
All responses are JSON. All timestamps are ISO-8601 strings.
Error format: `{"detail": "message"}` — HTTP 422 (validation), 404 (not found), 503 (service error).

---

## Health

### `GET /health`
```json
{ "status": "ok", "mock_data": true }
```
`mock_data`: `true` while seeded data is in use; `false` once `MOCK_DATA=false` is set and Member A pipeline is live.

---

## Forecast

### `GET /forecast?date=YYYY-MM-DD`
Returns 96 x 15-minute slots. Returns HTTP 503 if fewer than 96 rows exist for the requested date.

**Response (array of 96):**
```json
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
```
`data_source`: `"mock"` = seeded data; `"model"` = Member A pipeline (set `MOCK_DATA=false` in env).

---

## Schedule / Optimize

### `POST /optimize` (also: `POST /schedule/run`)
Clears all nudges, runs the greedy load-shift scheduler, creates new nudges.
Both paths return identical responses.

**Response:**
```json
{
  "before": [{ "slot": 0, "time": "00:00", "demand_kw": 75.0 }],
  "after":  [{ "slot": 0, "time": "00:00", "demand_kw": 71.2 }],
  "nudges_created": 143,
  "peak_before_kw": 196.0,
  "peak_after_kw": 163.0,
  "peak_reduction_pct": 16.8
}
```
`peak_reduction_pct` is a simulated projection, not a measured real-world result.

---

## Households

### `GET /households`
```json
[{ "id": 1, "name": "Sharma #1", "type": "low", "block": "Block A", "language": "en", "points": 50 }]
```

---

## Nudges / Per-Household Schedule

### `GET /nudges/{household_id}` (also: `GET /schedule/{household_id}`)
Returns all nudges for one household (all statuses). Returns `[]` for unknown households.

```json
[{
  "id": 1,
  "household_id": 1,
  "appliance_id": 3,
  "appliance": "Washing machine",
  "from_slot": 78, "to_slot": 52,
  "from_time": "19:30", "to_time": "13:00",
  "kwh_shifted": 0.5,
  "points": 5,
  "saving_rs": 1.5,
  "status": "pending",
  "message": "Run your Washing machine at 13:00 today instead of 19:30. Earn 5 points and save about Rs 2."
}]
```

### `POST /nudges/{nudge_id}/respond`
**Request:** `{ "accept": true }`
**Response:** `{ "nudge_id": 1, "status": "accepted", "household_points": 55 }`
**Error:** HTTP 404 if nudge_id does not exist.

---

## Nudge Send

### `POST /nudge/send`
Assembles nudge text for a household. Does not make real Telegram calls unless `TELEGRAM_TOKEN` is set and the standalone bot script is running.

**Request:**
```json
{ "household_id": 12, "nudge_id": null }
```
`nudge_id`: omit or `null` to target all pending nudges for the household.

**Response:**
```json
{
  "household_id": 12,
  "nudges_queued": 3,
  "channel": "api_only",
  "delivered": false,
  "messages": ["Run your Washing machine at 13:00 today instead of 19:30. Earn 5 points and save about Rs 2."]
}
```
`channel`: `"api_only"` when no token is set; `"telegram"` when `TELEGRAM_TOKEN` is present.
`delivered`: `false` in current implementation — no real Telegram push is made via this endpoint.

---

## KPIs / Impact Metrics

### `GET /kpis` (also: `GET /metrics`)
All values are simulated projections. Both paths return identical responses.

```json
{
  "peak_before_kw": 196.0,
  "peak_after_kw": 163.0,
  "peak_reduction_pct": 16.8,
  "kwh_shifted": 99.0,
  "rs_saved": 297.0,
  "co2_kg": 70.3,
  "solar_self_use_pct_before": 78.0,
  "solar_self_use_pct": 92.0,
  "participants": 22,
  "total_households": 80,
  "transformer_risk": "MEDIUM"
}
```
`transformer_risk`: `"LOW"` | `"MEDIUM"` | `"HIGH"` based on `peak_after / feeder_capacity` ratio.

---

## Leaderboard

### `GET /leaderboard?limit=10`
```json
[{ "rank": 1, "household_id": 5, "name": "Reddy #5", "block": "Block B", "points": 120 }]
```

---

## Demand-Response Event

### `POST /dr-event?date=YYYY-MM-DD`
Triggers a targeted DR event on top of existing nudges.

**Request:**
```json
{ "start_slot": 72, "end_slot": 84, "target_kw": 10.0 }
```
`start_slot`, `end_slot`: 0-95. `target_kw`: positive float.

**Response:**
```json
{
  "nudges_created": 21,
  "kw_reduced_expected": 8.0,
  "after": [{ "slot": 0, "time": "00:00", "demand_kw": 73.5 }]
}
```

---

## Flex Capacity

### `GET /flex-capacity`
Available flexible load (not yet nudged) per hour.

```json
[{ "hour": 17, "time": "17:00", "flexible_kw": 42.0 }]
```

---

## Demo Helpers

### `POST /demo/simulate-responses?rate=0.65&seed=7`
Randomly accepts ~`rate` fraction of pending nudges. For demo resets and CI.

```json
{ "processed": 143, "accepted": 93 }
```

### `POST /demo/reseed`
Wipes and re-seeds the database with fresh mock data (80 households, ~275 appliances, 96-slot forecast, 0 nudges). Do not call on production.

```json
{ "status": "reseeded" }
```

---

## Path Aliases

Both names are registered and return identical responses:

| Planned name | Internal name |
|---|---|
| `POST /schedule/run` | `POST /optimize` |
| `GET /schedule/{household_id}` | `GET /nudges/{household_id}` |
| `GET /metrics` | `GET /kpis` |

---

## Error Format
```json
{ "detail": "Forecast table has fewer than 96 slots. Run seed or Member A pipeline." }
```
- HTTP 503: service-layer error (e.g. not enough forecast rows)
- HTTP 404: resource not found (nudge ID, etc.)
- HTTP 422: request validation failure (wrong type, missing required field, out of range)
