# PowerPool — Architecture

## Overview

PowerPool is a neighbourhood energy management platform with three components:

```
┌──────────────────────────────────────────────────────────────────┐
│  Member A — Data / ML  (data-ml/)                                │
│  • Fetches real solar irradiance + weather data                  │
│  • Simulates household load profiles                             │
│  • Writes 96-slot daily forecast into SQLite (forecast table)    │
└───────────────────────────────┬──────────────────────────────────┘
                                │ SQLite (data/powerpool.db)
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  Member B — Backend / API  (backend/)                            │
│  • FastAPI on port 8000                                          │
│  • Greedy load-shifting optimizer (optimizer.py)                 │
│  • Nudge generation, points, KPIs, leaderboard                   │
│  • DR event management                                           │
│  • Optional: Telegram bot for nudge delivery                     │
└───────────────┬───────────────────────────┬──────────────────────┘
                │ HTTP/JSON                 │ HTTP → Telegram API
                ▼                           ▼
┌───────────────────────┐    ┌──────────────────────────────────┐
│  Member C — Frontend  │    │  Telegram Bot (telegram_bot.py)  │
│  (frontend/)          │    │  Residents accept/skip nudges     │
│  • DISCOM dashboard   │    │  via inline keyboard buttons      │
│  • Resident interface │    └──────────────────────────────────┘
│  • Charts, leaderboard│
└───────────────────────┘
```

## Data Flow

1. **Member A** runs the pipeline → writes 96 rows to the `forecast` table
   (`timestamp`, `demand_kw`, `solar_kw`, `capacity_kw`, `gap_kw`, `is_stress`).

2. **Member B** backend starts → calls `GET /forecast` internally to find
   stress slots, runs `greedy_schedule()`, writes nudges to the `nudges` table.

3. **Member C** frontend calls `GET /forecast`, `POST /optimize`, `GET /kpis`,
   `GET /leaderboard` to render the DISCOM dashboard.

4. Residents interact via the frontend or Telegram bot → `POST /nudges/{id}/respond`
   → backend updates points and nudge status in SQLite.

## Database Tables (SQLite)

| Table | Owner | Description |
|---|---|---|
| `forecast` | Member A writes, B reads | 96 slots/day of demand + solar |
| `households` | Member B seeds/manages | Residents, types, blocks, points |
| `appliances` | Member B seeds/manages | Flexible appliances per household |
| `nudges` | Member B writes, C/Bot read | Load-shift requests |
| `load_history` | Member A (future) | Historical kWh per household |
| `weather` | Member A (future) | Raw weather data |

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI + Uvicorn (Python 3.11) |
| Database | SQLite (upgradeable to Postgres) |
| Optimizer | Pure Python greedy scheduler |
| ML Pipeline | Python (Member A's choice) |
| Frontend | Member C's choice |
| Bot | python-telegram-bot 21.x |
| Hosting | Render.com (free tier) |

## Deployment

- **Backend:** Render Web Service via `render.yaml`
- **DB:** SQLite on Render ephemeral disk (OK for hackathon; swap to Render
  Postgres for persistence)
- **Frontend:** To be configured by Member C
