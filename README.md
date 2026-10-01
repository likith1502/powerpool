# ⚡ PowerPool — Smart Feeder Load Flexibility Platform

PowerPool is a neighbourhood-scale load-flexibility platform that forecasts feeder demand & solar generation, detects transformer stress windows, and shifts flexible household loads into solar-rich hours using gamified resident nudges and DISCOM command controls.

---

## 🚀 Quick Start Guide

### 1. Installation

```bash
# Clone repository and navigate to root directory
cd powerpool

# Install required dependencies
pip install -r requirements.txt

# Seed database and pre-generate scenario files
python -m data.seed_demo
```

### 2. Run FastAPI Backend

```bash
uvicorn backend.main:app --reload --port 8000
```
API Documentation will be available at: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Run Streamlit Frontend

```bash
streamlit run frontend/Home.py
```
Streamlit App will open at: [http://localhost:8501](http://localhost:8501)

> **Note**: PowerPool includes an automatic **Demo Mode Fallback**. If FastAPI is not running or network connection fails, the frontend will automatically switch to local mock data without crashing!

---

## 🧪 Running Tests

```bash
python -m pytest
```

---

## 📁 Repository Architecture

```text
powerpool/
├── data/                  # Synthetic household data generator, weather, and SQLite seed
│   ├── generator.py
│   ├── weather.py
│   ├── seed_demo.py
│   └── scenarios/
├── ml/                    # LightGBM demand forecast & physics solar generation model
│   ├── forecast_demand.py
│   ├── forecast_solar.py
│   └── metrics.py
├── backend/               # FastAPI backend API, greedy optimizer & multilingual nudge service
│   ├── main.py
│   ├── optimizer.py
│   ├── nudges.py
│   └── schemas.py
├── frontend/              # Streamlit multi-page UI & reusable visual components
│   ├── Home.py
│   ├── api_client.py
│   ├── components/
│   └── pages/
│       ├── 1_Resident.py
│       └── 2_DISCOM.py
├── tests/                 # Unit & end-to-end smoke test suite
└── pitch/                 # Hackathon demonstration script & presentation material
```

---

## 🏆 Key Features

- **DISCOM Feeder Command Center**: 6 impact KPI cards, central before/after load curve chart with 19.1% peak reduction, demand gap visualizer, and instant Demand Response trigger.
- **Resident Mobile Web App**: Instant Grid Stress Traffic Light (GREEN/AMBER/RED), multilingual nudges (English, Hindi, Telugu) with Accept/Skip buttons, reward points wallet, and community leaderboard.
- **Scenario Simulation Engine**: Toggle between **Sunny**, **Cloudy**, and **Heatwave** weather conditions in real-time.
