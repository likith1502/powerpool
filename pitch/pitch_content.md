# PowerPool — Pitch Deck Content & Architecture Summary

## Executive Summary
PowerPool is a neighbourhood-scale load-flexibility platform that aligns household power consumption with solar rooftop generation curves to eliminate distribution transformer overload.

## Key Features & Value Proposition
1. **DISCOM Feeder Command Center**:
   - Real-time 24-hour load forecasting & intermittency monitoring.
   - Central before vs after load curve visualization with 19.1% peak reduction.
   - Automated Demand Response (DR) trigger dispatches nudges to 100 neighbourhood households.

2. **Resident Smart Energy Web App**:
   - Instant Grid Traffic Light status (GREEN / AMBER / RED).
   - Multilingual smart action nudges (English, Hindi, Telugu).
   - Points rewards & bill savings wallet with community leaderboard.

3. **Core ML & Optimization Architecture**:
   - **Data Layer**: Synthetic 100-household load dataset with physics solar rooftop model and Open-Meteo weather integration.
   - **Optimization Engine**: Greedy load-shifting algorithm targeting solar surplus hours (11:00-15:30) with 65% simulated compliance rate.
   - **API Backend**: FastAPI REST service with SQLite state persistence.
   - **Frontend**: Streamlit multi-page dashboard with Plotly charts and automated demo fallback mode.
