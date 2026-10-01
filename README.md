# PowerPool

**AI-powered neighbourhood energy flexibility and demand management platform**
*Yuva Yodha Energy Tech Hackathon 2026 — Challenge 03: Grid Reliability*

PowerPool forecasts neighbourhood electricity demand and solar generation, identifies periods of solar surplus and evening feeder stress, and schedules flexible household loads to reduce peak demand — while rewarding residents with transparent points and bill savings.

---

## 1. Repository Layout

```
powerpool/
├── backend/          ← FastAPI server, DB access, greedy scheduler, schemas (Member B)
│   ├── config.py     ← Environment settings & unit conversions
│   ├── db.py         ← SQLite connection pool & idempotent migrations
│   ├── main.py       ← FastAPI application routes & lifespan
│   ├── optimizer.py  ← Greedy load-shifting algorithm (pure functions)
│   ├── schemas.py    ← Pydantic API contract schemas (string household IDs)
│   ├── services.py   ← Core business logic, nudges, KPIs, DR event
│   └── tests/        ← Backend test suite (API, optimizer, migrations, household IDs)
├── data/             ← Member A dataset generator & weather fetcher
│   ├── generator.py  ← Synthetic 100-household and appliance generator
│   ├── weather.py    ← Open-Meteo weather fetcher with offline fallback
│   ├── sample_load.csv
│   └── cached_weather.csv
├── ml/               ← Member A Machine Learning & Forecasting
│   ├── features.py   ← 15-minute slot feature engineering
│   ├── forecast_demand.py ← LightGBM demand model & baseline fallback
│   ├── forecast_solar.py  ← Solar output physics-based model
│   ├── metrics.py    ← MAPE, MAE, RMSE evaluation
│   ├── models/       ← Model artifacts (demand_model.txt, metadata.json)
│   └── pipeline.py   ← 96-slot forecast pipeline & demo scenario builder
├── scripts/          ← Member A build and validation scripts
│   ├── build_dataset.py
│   ├── build_forecasts.py
│   ├── validate_member_a_handoff.py
│   └── validate_member_a_output.py
├── tests/            ← Member A ML and dataset unit tests
├── docs/             ← API contract & architecture reference
│   ├── API_CONTRACT.md ← Official API contract & Streamlit guide (Member C)
│   └── architecture.md
├── requirements.txt  ← Unified dependencies for API, ML, and testing
├── .env.example      ← Template environment configuration
├── pytest.ini        ← Configured testpaths (`backend/tests tests`)
└── README.md
```

---

## 2. Quick Start

### Prerequisites
* Python 3.11+
* Windows PowerShell (or macOS / Linux terminal)

### 1. Environment & Dependencies

```powershell
# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install unified dependencies (Web server, ML pipeline, and Pytest)
pip install -r requirements.txt
```

### 2. Configuration

```powershell
# Copy environment template
Copy-Item .env.example .env
```
*Note: The default `.env.example` settings point to `data/powerpool.db` with `MOCK_DATA=false` to use the real ML forecasts.*

### 3. Database Status & Safety
The repository includes a ready-to-run SQLite database at `data/powerpool.db` with:
* **100 Households** (`HH001` through `HH100`)
* **597 Appliances** (148 flexible, including all 6 target appliances)
* **288 Forecast Slots** across 3 demo scenarios:
  * `2026-10-01`: Sunny scenario
  * `2026-10-02`: Cloudy scenario
  * `2026-10-03`: Heatwave scenario (peak demand: 388.91 kW > 170 kW feeder capacity)

> **Important Safety Note:** Do NOT run `seed_mock` or dataset rebuild scripts against the working database unless intentionally resetting.

### 4. Start the Backend API

```powershell
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
* Interactive Swagger Docs: `http://127.0.0.1:8000/docs`
* OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
* Health Check: `http://127.0.0.1:8000/health`

---

## 3. Running Tests

Run the full unified test suite (covers backend routes, ML pipeline, string household IDs, migrations, and scenarios):

```powershell
pytest
```
*Current test suite status:* **89 passed, 1 warning** in ~3.8 seconds.

To run Member A handoff validation scripts:
```powershell
python scripts/validate_member_a_handoff.py
python scripts/validate_member_a_output.py
```

---

## 4. Frontend & Member C Integration

Member C can connect her Streamlit dashboard or resident UI directly to the running backend.
* **Full Specification & Code Examples:** See [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md).
* **Key Endpoints:**
  * Feeder Forecast: `GET /forecast?date=2026-10-01`
  * Run Scheduler: `POST /optimize` (alias: `POST /schedule/run`)
  * Grid KPIs: `GET /kpis` (alias: `GET /metrics`)
  * Resident Nudges: `GET /nudges/{household_id}` (e.g. `/nudges/HH001`)
  * Accept / Skip Nudge: `POST /nudges/{nudge_id}/respond`
  * Gamification Leaderboard: `GET /leaderboard`
  * Emergency DR Dispatch: `POST /dr-event`
  * Hourly Flex Gauge: `GET /flex-capacity`

---

## 5. Team Responsibilities

| Member | Focus Area | Artifacts |
|---|---|---|
| **Member A** | Data & ML Pipeline | Synthetic data generator, weather fetcher, LightGBM demand model, solar model, scenarios (`data/`, `ml/`, `scripts/`, `tests/`) |
| **Member B** | Backend, Scheduling, Integration | FastAPI server, greedy optimizer, schema migrations, API contract, test suite (`backend/`, `docs/`) |
| **Member C** | Frontend & UI | Streamlit dashboard, DISCOM operations view, resident gamified portal (`frontend/`) |
