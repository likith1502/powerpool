# PowerPool — Deployment & Infrastructure Guide

**Yuva Yodha Energy Tech Hackathon 2026 — Challenge 03: Grid Reliability**

---

## 1. Overview & Architecture

PowerPool consists of two coordinated services:

| Component | Technology | Default Port | Internal Docker URL |
| :--- | :--- | :--- | :--- |
| **Backend API** | FastAPI / Uvicorn (Python 3.11) | `8000` | `http://backend:8000` |
| **Frontend UI** | Streamlit (Python 3.11) | `8501` | `http://frontend:8501` |
| **Database** | SQLite3 (`data/powerpool.db`) | N/A (Embedded) | Persistent Volume `/app/data` |
| **ML Engine** | LightGBM + Scikit-learn + Pandas | In-process | Built into image with `libgomp1` |

---

## 2. Local Development (Native Python Environment)

### Prerequisites
- Python 3.11 installed.
- PowerShell or bash terminal.

### Step 1: Environment Setup
```powershell
# In repository root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 2: Configuration
Copy the template configuration file:
```powershell
cp .env.example .env
```

### Step 3: Run FastAPI Backend
```powershell
# Terminal 1
uvicorn backend.main:app --reload --port 8000
```
- Health Check: `http://localhost:8000/health`
- Interactive Swagger Docs: `http://localhost:8000/docs`

### Step 4: Run Streamlit Frontend
```powershell
# Terminal 2
streamlit run frontend/app.py
```
- Web Application: `http://localhost:8501`

---

## 3. Docker Container Deployment

### Production Features
- **Data Persistence:** Dedicated named volume (`powerpool-data`) preserves the SQLite database across container restarts.
- **Data Isolation:** Developer databases (`data/*.db`) and test databases are strictly excluded from Docker images via `.dockerignore`.
- **Health Checks:** Automated container health monitoring checks `http://localhost:8000/health` every 10 seconds.
- **Service Dependency:** The frontend container waits for backend health verification before launching.
- **Cross-Service Networking:** Frontend communicates with backend over internal Docker DNS (`http://backend:8000`), never relying on `localhost`.

### Multi-Service Deployment Commands
```bash
# Build and start services in background
docker compose up -d --build

# View real-time logs
docker compose logs -f

# Check container health status
docker compose ps

# Stop containers gracefully
docker compose down

# Stop containers and remove persistent volume (clean reset)
docker compose down -v
```

### Container Resource Configuration
For production clusters (Kubernetes / ECS / Nomad), allocate:
- Backend: `512MB RAM`, `0.5 vCPU`
- Frontend: `512MB RAM`, `0.5 vCPU`

---

## 4. Optional Integrations

### A. Telegram Bot Delivery
1. Create a bot via `@BotFather` on Telegram to receive a bot token.
2. In your `.env` or container environment, set:
   ```env
   TELEGRAM_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   ```
3. To test notification dispatch:
   ```bash
   curl -X POST http://localhost:8000/nudge/send \
     -H "Content-Type: application/json" \
     -d '{"household_id": "HH001", "chat_id": "<YOUR_TELEGRAM_CHAT_ID>"}'
   ```
4. If `TELEGRAM_TOKEN` is unset, the system automatically falls back to `api_only` channel mode without errors.

### B. AI Nudge Personalization (Claude 3 Haiku)
1. Get an Anthropic API Key from the Anthropic Console.
2. In your `.env` or container environment, set:
   ```env
   AI_NUDGE_PERSONALIZATION=true
   ANTHROPIC_API_KEY=sk-ant-api03-...
   ```
3. If disabled or if the API is unreachable, the system automatically uses the localized deterministic template without failing.

---

## 5. Troubleshooting & Health Verification

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| Frontend displays offline error | Backend unreachable or not started | Ensure backend container is healthy: `docker compose ps` |
| Database empty on first boot | Fresh volume initialized | Backend automatically seeds initial data on startup if forecast table is empty |
| LightGBM import error in Docker | Missing OpenMP runtime | Ensure `libgomp1` is installed via `apt-get` (already present in `Dockerfile`) |
