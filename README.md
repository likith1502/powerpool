# PowerPool

**AI-powered neighbourhood energy management platform**

PowerPool forecasts electricity demand, schedules flexible household loads during solar-surplus hours, and helps reduce evening peak demand — all while rewarding residents with points and savings.

## Repository Layout

```
powerpool/
├── backend/          ← FastAPI server, DB, optimizer, Telegram bot (Member B)
│   ├── app modules   ← config, db, main, mock_main, optimizer, schemas,
│   │                    seed_mock, services, telegram_bot, translations
│   ├── tests/        ← pytest test suite
│   └── requirements.txt
├── data-ml/          ← Data simulation, solar/weather pipeline, ML (Member A)
│   ├── data/         ← CSV / parquet datasets (gitignored if large)
│   └── models/       ← Trained model artefacts
├── frontend/         ← DISCOM dashboard, resident UI, charts (Member C)
├── docs/             ← Architecture notes and API contract reference
├── .env.example      ← Copy to .env and fill in secrets
├── pytest.ini        ← Test discovery config (run `pytest` from repo root)
├── render.yaml       ← Render.com deployment config
└── README.md
```

## Quick Start

### Backend

```powershell
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Copy and configure environment
Copy-Item .env.example .env   # then edit .env with real values if needed

# 3. Seed mock data (first run only, or on a fresh DB)
python -m backend.seed_mock

# 4. Start the server (production app)
uvicorn backend.main:app --reload

# 5. Open API docs
start http://127.0.0.1:8000/docs

# [Dev-only] Mock server for frontend development (no DB required)
uvicorn backend.mock_main:app --reload --port 8001
```

### Tests

```powershell
# Run from repo root
pytest
```

## Component Interfaces

| Producer | Consumer | Transport |
|---|---|---|
| `backend/` REST API | `frontend/` dashboard | HTTP/JSON on port 8000 |
| `data-ml/` pipeline | `backend/` seed / forecast table | SQLite `forecast` table |
| `backend/` `/nudges` endpoint | Telegram bot (`telegram_bot.py`) | HTTP → Telegram API |

See [`docs/api-contract.md`](docs/api-contract.md) for the full endpoint reference.

## Team

| Member | Area | Directory |
|---|---|---|
| A | Data / ML pipeline | `data-ml/` |
| B | Backend / API | `backend/` |
| C | Frontend / UI | `frontend/` |

## Deployment

Deployed on [Render](https://render.com) via `render.yaml`.  
The production start command is:

```
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```
