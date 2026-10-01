# PowerPool — Final Test Report

Tested revision: `backend` @ 691f41a plus the fixes in this patch · Date: 2026-10-01 · Environment: Linux sandbox, Python 3.12, fresh clone, isolated temporary databases (production `data/powerpool.db` never used).

## Acceptance status: PASS WITH LIMITATIONS

The demo scope works end to end. Docker and the hosted Render deployment were configuration-checked but not run, because no Docker engine or Render account was available in the test environment.

## Results

| Area | Status | Evidence |
|---|---|---|
| Automated tests | PASS | 203 passed, 1 skipped (production-DB check, skipped by design on a fresh clone), 0 failed |
| Backend API | PASS | `/health`, `/forecast` (3 scenarios), `/forecast/live`, `/optimize`, `/kpis`, `/households`, `/leaderboard`, `/flex-capacity` all return 200; backend served 71 UI requests with 0 errors |
| Destructive endpoints | PASS | `/demo/reseed` and `/demo/simulate-responses` return 403 unless `ENABLE_DEMO_ENDPOINTS=true` |
| ML forecast | PASS | LightGBM (150 trees) loads; `?live=true` and `/forecast/live` return `data_source=live_model`; fallback is labeled `seasonal_fallback` |
| Optimizer (fresh DB, 80 households, 65% compliance) | PASS | Sunny 196.0 → 169.7 kW; Heatwave 186.3 → 169.7 kW; Cloudy 109.7 kW, no stress, 0 nudges; 0 kW remaining overload |
| KPIs | PASS | 78.98 kWh realized, ₹236.93/day, 56.07 kg CO₂/day, solar self-use 94.5% → 100% |
| Streamlit UI — browser (Chromium, headless) | PASS | Home, Resident and DISCOM pages at 1366×768 and 420×860: 0 Streamlit exceptions. Optimizer button shows "169.7 kW / 170 kW" and GRID FEASIBLE; Live ML toggle, DR event button and nudge Accept all work; Telugu nudges render |
| Docker Compose | CONFIG ONLY | Volume no longer shadows source; DB excluded from image; model and cached weather included; health check uses installed `curl`. Not built or run. |
| Render deployment | CONFIG FIXED, NOT DEPLOYED | Simulated Render build in a clean virtualenv: before fix, live forecast returned 503; after fix, 200 |

## Defects found and fixed

| ID | Severity | Component | Problem | Fix | Retest |
|---|---|---|---|---|---|
| D1 | High | Docker | DB volume mounted over `/app/data`, shadowing source code | DB moved to `/app/db` | Pass |
| D2 | High | Backend | Empty DB seeded the 100-household stress profile | Seeds 80 households (`SEED_HOUSEHOLDS`) | Pass |
| D3 | High | Security | `/demo/reseed` could wipe the DB in deployment | Guarded by `ENABLE_DEMO_ENDPOINTS` | Pass |
| D4 | High | ML | Live forecast labeled `live_model` even when LightGBM was missing | Labeled `seasonal_fallback` | Pass |
| D5 | High | Render | `render.yaml` installed `backend/requirements.txt`, which lacks pandas/numpy/LightGBM, so live ML returned 503 | Installs root `requirements.txt` | Pass (simulated) |
| D6 | Medium | Backend | `GET /forecast/live` silently returned the precomputed forecast | Route detected from the request path | Pass |
| D7 | Medium | Frontend | DISCOM header said "100 Residential Households"; picker allowed 1–100 though only HH001–HH080 exist | Shows 80; picker capped at 80 | Pass (browser) |

## Known limitations

- Load data is synthetic; 65% compliance is an assumption.
- Stage 2 is an aggregate analytical curtailment model, not physical control of any device.
- On a database with no load history, the live forecast uses synthetic lag inputs (peak ≈ 325 kW); use the precomputed scenario forecast for demos without history.
- 12 browser console 404s come from Streamlit static assets, not the API.
- Docs that quote "155.5 kW optimized peak" describe 100% acceptance; the app at 65% compliance shows 169.7 kW (fresh DB). To be reconciled against the developer's production DB.

## Commands

```
python -m pytest -q
uvicorn backend.main:app --port 8000
streamlit run frontend/Home.py
docker compose up --build        # not yet verified
```
