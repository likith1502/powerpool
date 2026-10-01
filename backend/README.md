# PowerPool — Backend

FastAPI backend for the PowerPool neighbourhood energy management platform.

## Module Overview

| File | Purpose |
|---|---|
| `main.py` | FastAPI app, route definitions, CORS, lifespan |
| `mock_main.py` | Hard-coded JSON stub for frontend dev (no DB required) |
| `config.py` | Settings loaded from `.env` (tariffs, capacity, keys) |
| `db.py` | SQLite schema, connection manager, `rows()` helper |
| `schemas.py` | Pydantic request/response models (the API contract) |
| `services.py` | Business logic: forecasts, nudges, KPIs, DR events, leaderboard |
| `optimizer.py` | Greedy load-shifting scheduler (pure functions, no DB) |
| `seed_mock.py` | Populates DB with 80 synthetic households for development |
| `telegram_bot.py` | (Stretch) Telegram integration for nudge delivery |
| `translations.py` | Nudge text in English / Hindi / Telugu, optional Claude polish |

## Setup

```powershell
# From the repo root
pip install -r backend/requirements.txt
Copy-Item .env.example .env    # edit .env with real secrets
```

## Running

```powershell
# Production app (from repo root)
uvicorn backend.main:app --reload

# Mock server for Member C (frontend) — no DB needed
uvicorn backend.mock_main:app --reload --port 8001
```

The API is documented at <http://127.0.0.1:8000/docs>.

## Seeding Mock Data

```powershell
# Populates data/powerpool.db with 80 households + 96-slot forecast
python -m backend.seed_mock
```

> **Note:** Member A's real data pipeline (in `data-ml/`) will overwrite the
> `forecast` table with live solar/weather data. The schema columns remain
> identical, so the backend needs no changes when real data lands.

## Tests

```powershell
# From repo root (pytest.ini points to backend/tests/)
pytest
```

Tests use a separate `data/test_powerpool.db` (set via `DB_PATH` env var at
the top of `test_api.py`) so they never touch the development database.

## Telegram Bot (Stretch Goal)

```powershell
# Requires TELEGRAM_TOKEN and API_URL in .env
python -m backend.telegram_bot
```

Users send `/start <household_id>` to get their pending nudges with
Accept / Skip inline buttons.

## Environment Variables

See [`.env.example`](../.env.example) at the repo root for all supported keys.

| Variable | Default | Description |
|---|---|---|
| `DB_PATH` | `data/powerpool.db` | SQLite file path |
| `FEEDER_CAPACITY_KW` | `170` | Transformer limit |
| `COMPLIANCE` | `0.65` | Expected nudge acceptance rate |
| `PEAK_TARIFF` | `9.0` | Peak tariff Rs/kWh |
| `OFFPEAK_TARIFF` | `6.0` | Off-peak tariff Rs/kWh |
| `CO2_PER_KWH` | `0.71` | CO₂ kg per kWh (CEA factor) |
| `ANTHROPIC_API_KEY` | _(empty)_ | Optional: Claude for translation polish |
| `TELEGRAM_TOKEN` | _(empty)_ | Optional: Telegram bot token |
| `API_URL` | `http://127.0.0.1:8000` | Used by Telegram bot |
