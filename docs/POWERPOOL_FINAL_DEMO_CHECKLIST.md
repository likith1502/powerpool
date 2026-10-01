# POWERPOOL — FINAL HACKATHON LIVE DEMO CHECKLIST & EXECUTION GUIDE
**Project:** PowerPool — Neighbourhood-Scale Load Flexibility Platform  
**Challenge:** 03 — Grid Reliability (Yuva Yodha Energy Tech Hackathon 2026)  
**Primary Demonstration Configuration:** Configuration 1 (Active Full-Stack Application, 80 Registered Households)

---

## 1. CRITICAL SAFETY RULES (READ BEFORE STARTING)

> [!CAUTION]
> **DO NOT MUTATE THE PRODUCTION DATABASE**
> - **NEVER** call `POST /demo/reseed` against the running production server. That endpoint truncates and reseeds database tables.
> - **DO NOT** run arbitrary SQL write queries (`INSERT`, `UPDATE`, `DELETE`, `DROP`) against `data/powerpool.db`.
> - **DO NOT** run destructive test scripts during the demo that overwrite `data/powerpool.db`.
> - **DO NOT** delete, move, or rename `data/powerpool.db`.
> - All demonstration actions in the browser (viewing forecasts, running the optimizer, viewing nudges, accepting a nudge) are safe and designed for presentation.

---

## 2. CHRONOLOGICAL PRE-DEMO CHECKLIST (5 MINUTES PRIOR)

### Step 1: Verify Directory and Python Environment
Open PowerShell and verify:
```powershell
cd C:\Users\Likith\Downloads\PowerPool\powerpool
.\.venv\Scripts\python.exe --version
```
*Expected Output:* `Python 3.11.x`

### Step 2: Read-Only Database Sanity Check
Check the database file size, integrity, and current nudge count:
```powershell
.\.venv\Scripts\python.exe -c "import sqlite3; conn = sqlite3.connect('data/powerpool.db'); print('Integrity:', conn.execute('PRAGMA integrity_check').fetchone()[0]); print('Households:', conn.execute('SELECT COUNT(*) FROM households').fetchone()[0]); print('Appliances:', conn.execute('SELECT COUNT(*) FROM appliances').fetchone()[0]); print('Nudges:', conn.execute('SELECT COUNT(*) FROM nudges').fetchone()[0]); conn.close()"
```
*Expected Values:*
- Integrity: `ok`
- Households: `80`
- Appliances: `275`
- Nudges: `0` (or clean pending state from previous run)

### Step 3: Check Port Availability
Verify that ports `8000` (FastAPI) and `8501` (Streamlit) are not occupied by leftover processes:
```powershell
Get-NetTCPConnection -LocalPort 8000, 8501 -ErrorAction SilentlyContinue | Select-Object LocalPort, State, OwningProcess
```
*Action:* If stale processes occupy these ports, terminate them cleanly before proceeding.

---

## 3. SAFE SERVICE STARTUP COMMANDS

### Terminal 1: Start FastAPI Backend
Open a dedicated PowerShell window:
```powershell
cd C:\Users\Likith\Downloads\PowerPool\powerpool
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
*Expected Terminal Output:*
```text
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

*Quick Health Check in a second terminal (optional):*
```powershell
curl http://127.0.0.1:8000/health
```
*Expected JSON:* `{"status":"ok","mock_data":...}`

### Terminal 2: Start Streamlit Frontend
Open a second dedicated PowerShell window:
```powershell
cd C:\Users\Likith\Downloads\PowerPool\powerpool
.\.venv\Scripts\streamlit.exe run frontend/Home.py --server.port 8501
```
*Expected Terminal Output:*
```text
  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
```
*The default browser will automatically open to `http://localhost:8501`.*

---

## 4. STEP-BY-STEP LIVE BROWSER DEMO WALKTHROUGH

| Step | Page / Component | Actions to Perform | Exact Values to Look For | Speaking Focus |
|:---:|:---|:---|:---|:---|
| **1** | **Home Dashboard** (`Home.py`) | 1. Open `http://localhost:8501`.<br>2. Inspect 24-hr feeder curve.<br>3. Inspect capacity line. | • Feeder Capacity: **170.0 kW** (red horizontal line)<br>• Baseline Peak: **~196.00 kW** (evening slots 74–86)<br>• Solar Generation: Peaks midday, drops to **0 kW** by 18:30 | Frame the problem: sunset solar cliff + residential cooking/cooling surge creates a 26 kW overload on a simulated 170 kW transformer. |
| **2** | **DISCOM Command Center** (`2_DISCOM.py`) | 1. Click `2_DISCOM` in sidebar.<br>2. Toggle `⚡ Run Live ML Inference (LightGBM)`. | • Badge updates to: `Live LightGBM Booster`<br>• Plot shows 96 intervals with stress intervals flagged above 170 kW | Explain dual forecasting horizons: recursive day-ahead (2.42 kW MAE, 14.8% gain, zero future data) vs 15-min rolling dispatch (2.10 kW MAE, 26.1% gain). |
| **3** | **Run Optimizer** (`2_DISCOM.py`) | 1. Click green button `🚀 Run Load-Shift Optimizer`.<br>2. Inspect before/after Plotly comparison. | • Success banner: `After Optimization: 169.7 kW / 170 kW`, Peak Reduction **13.4%**, 27 nudges created<br>• Status badge: `🟢 FEASIBLE`<br>• Remaining Overload: **0.00 kW**<br>• Shifted Energy: **121.50 kWh scheduled** (~79.0 kWh realized at 65% compliance) | Emphasize constraints: exact energy conservation ($\Delta = 0$), 0 appliance window violations, destination block checks prevent rebound peaks. |
| **4** | **Stage 2 Reliability Caveat** (`2_DISCOM.py`) | 1. Point to the Two-Stage Grid Framework guidance text above the chart. | • Modeled Emergency Curtailment parameter: **120.0 kW** max.<br>• Heatwave residual overload finding: **12.52 kW** remains under extreme 389 kW peaks. | Candidly disclose Stage 2 as an analytic emergency simulation (EV throttle/thermostat setback), proving PowerPool does not force artificially flat curves. |
| **5** | **Resident Portal** (`1_Resident.py`) | 1. Click `1_Resident` in sidebar.<br>2. Select Household `HH001` (Sharma family).<br>3. Switch language: `English` $\to$ `తెలుగు` $\to$ `हिंदी`.<br>4. Click `Accept Nudge`. | • Multilingual nudge card renders correctly.<br>• Bill saving calculated via Time-of-Day differential: **₹3.00/kWh** ($₹9 peak - ₹6 solar off-peak).<br>• Points update dynamically on the community leaderboard. | Conclude with civic engagement: multi-lingual accessibility, transparent ToD economics, and gamified incentives for sustained participation. |

---

## 5. CONTINGENCY & FALLBACK PLAN (ERROR RECOVERY WITHOUT DB RESET)

| Potential Failure Point | Immediate Symptom | Cause | Recommended Immediate Action & Spoken Fallback |
|:---|:---|:---|:---|
| **External Weather API Lag** | Toggle `Run Live ML Inference` spins or takes >5 seconds. | Open-Meteo external HTTP network latency. | • Turn toggle off.<br>• **Spoken Fallback:** *"If external weather API feeds experience network latency, our service automatically falls back to cached day-ahead meteorological data, ensuring uninterrupted operation."* |
| **Browser Stale State** | Optimizer chart does not refresh after clicking. | Streamlit session cache mismatch. | • Press `R` on the keyboard to trigger an instant page rerun.<br>• **Spoken Fallback:** *"The before/after curve shows a 26.3 kW peak reduction at 65% compliance, bringing net demand down to 169.7 kW, just under the 170 kW limit."* |
| **Backend Process Disconnected** | Streamlit displays `ConnectionError: HTTPConnectionPool`. | Backend terminal closed or crashed. | • Do not panic. Re-run `.\.venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000` in Terminal 1.<br>• The frontend's `PowerPoolAPIClient` has built-in offline mock fallbacks, preventing raw stack traces. |
| **Nudge Already Accepted** | Clicking `Accept Nudge` shows `Nudge already responded to`. | Nudge was previously accepted in an earlier test. | • Select the next household in the dropdown (`HH002` or `HH003`) which has fresh pending nudges.<br>• **Spoken Fallback:** *"Our system enforces strict duplicate-response protection so residents cannot claim points twice for the same cycle."* |

---

## 6. CLEAN SHUTDOWN PROCEDURE (POST-DEMO)

1. In Terminal 2 (Streamlit): Press `Ctrl + C`.
2. In Terminal 1 (FastAPI): Press `Ctrl + C`.
3. Confirm database remained untouched:
   ```powershell
   (Get-FileHash data/powerpool.db).Hash
   ```
   *Expected Value:* `1A352F8813CBA41C94D3B44BAB8473A4F549FE1C4AABC4899C6042A3CE06F8EC`
