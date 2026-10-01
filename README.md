# PowerPool - Member A (Data & ML Layer) Documentation

## Overview
Member A delivers the Data & Machine Learning infrastructure for **PowerPool** --- a neighbourhood-scale load flexibility platform.

The data layer simulates 100 households in Hyderabad at 15-minute resolution across 30 days, integrates Open-Meteo weather data, builds physics-based solar generation models, trains a LightGBM demand-forecasting pipeline (with a seasonal baseline fallback), and populates `data/powerpool.db` for Member B's FastAPI backend and optimizer.

---

## Architecture & File Structure

```
powerpool/
├── data/
│   ├── generator.py          # Synthetic household, appliance, & 30-day load generator
│   ├── weather.py            # Open-Meteo API integration with local caching & fallback
│   ├── powerpool.db          # Main SQLite database for backend integration
│   ├── sample_load.csv       # Sample CSV for quick integration tests
│   └── cached_weather.csv    # Local weather cache
│
├── ml/
│   ├── features.py           # Lag, rolling, & calendar feature extraction
│   ├── forecast_demand.py    # LightGBM demand forecasting model & baseline fallback
│   ├── forecast_solar.py     # Physics-based solar forecast & scenario curves
│   ├── metrics.py            # MAPE (with 1e-6 epsilon protection), MAE, RMSE metrics
│   ├── pipeline.py           # 96-slot scenario forecast pipeline
│   └── models/
│       ├── demand_model.txt  # Saved LightGBM booster model
│       └── metadata.json     # Model performance & feature metadata
│
├── scripts/
│   ├── build_dataset.py           # Generates 100 households, appliances, 30d load, weather
│   ├── build_forecasts.py         # Trains ML model & generates 3 demo scenario forecasts
│   └── validate_member_a_output.py# Comprehensive validation script for acceptance criteria
│
├── tests/
│   ├── test_generator.py     # Unit tests for data generation
│   ├── test_weather.py       # Unit tests for weather module & fallback
│   ├── test_forecast.py      # Unit tests for forecasting & gap formula
│   ├── test_scenarios.py     # Unit tests for demo scenarios (sunny, cloudy, heatwave)
│   └── test_database.py      # Unit tests for SQLite schema & constraints
│
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
└── README.md                 # Main project & handoff documentation
```

---

## SQLite Database Handoff Contract (`data/powerpool.db`)

### 1. `households`
- `id` (TEXT PRIMARY KEY) - e.g. `HH001`
- `name` (TEXT)
- `type` (TEXT: `low` | `mid` | `shop`)
- `block` (TEXT: `Block A`, `Block B`, ...)
- `language` (TEXT: `en` | `hi` | `te`)
- `points` (INTEGER) - starts at 0

### 2. `appliances`
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `household_id` (TEXT)
- `name` (TEXT) - includes exact required flexible appliances: `Washing machine`, `Water pump`, `Inverter charging`, `Geyser`, `Iron`, `E-rickshaw charging`
- `power_kw` (REAL > 0)
- `duration_slots` (INTEGER > 0)
- `flexible` (INTEGER: 0 | 1)
- `earliest_slot` (INTEGER: 0--95)
- `latest_slot` (INTEGER: 0--95)
- `usual_slot` (INTEGER: 0--95)

### 3. `load_history`
- `household_id` (TEXT)
- `timestamp` (TEXT ISO format e.g. `2026-09-01T00:00:00`)
- `kwh` (REAL >= 0)

### 4. `weather`
- `timestamp` (TEXT PRIMARY KEY)
- `temp_c` (REAL)
- `cloud_cover` (REAL: 0--100)
- `irradiance_wm2` (REAL >= 0)

### 5. `forecast`
- `timestamp` (TEXT PRIMARY KEY)
- `demand_kw` (REAL >= 0)
- `solar_kw` (REAL >= 0)
- `capacity_kw` (REAL)
- `gap_kw` (REAL: `demand_kw - solar_kw - capacity_kw`)
- `is_stress` (INTEGER: 1 if `gap_kw > 0` else 0)

### Demo Forecast Scenarios
Populated in `forecast` table (96 rows each, 288 rows total):
- `2026-10-01` = **Sunny**
- `2026-10-02` = **Cloudy**
- `2026-10-03` = **Heatwave** (Peak demand > 170 kW)

---

## Execution Commands

### 1. Build Full Dataset (Households, Load History, Weather)
```bash
python scripts/build_dataset.py
```

### 2. Train Forecast Model & Populate Demo Scenarios
```bash
python scripts/build_forecasts.py
```

### 3. Run Validation Suite
```bash
python scripts/validate_member_a_output.py
```

### 4. Run Unit Tests
```bash
pytest -v
```
