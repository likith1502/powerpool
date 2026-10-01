# PowerPool — Frontend

**Owner: Member C**

This directory will contain the PowerPool frontend: DISCOM dashboard, resident
interface, load charts, and leaderboard.

## Integration with the Backend

The frontend talks to the backend REST API (default: `http://localhost:8000`).

During frontend development, before the full backend is ready, you can run
the mock server which returns hard-coded but correctly-shaped responses:

```powershell
# From the repo root
uvicorn backend.mock_main:app --reload --port 8001
```

Then point your frontend at `http://localhost:8001`.

Once the real backend is running, switch to `http://localhost:8000`.

## Key Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/forecast` | GET | 96-slot demand + solar forecast |
| `/optimize` | POST | Run load-shifting; returns before/after curves |
| `/kpis` | GET | Dashboard KPIs (peak, savings, CO₂, solar) |
| `/leaderboard` | GET | Top households by points |
| `/households` | GET | List all households |
| `/nudges/{id}` | GET | Pending nudges for a household |
| `/nudges/{id}/respond` | POST | Accept or skip a nudge |
| `/flex-capacity` | GET | Hourly flexible load available |
| `/dr-event` | POST | Trigger a demand-response event |

See [`../docs/api-contract.md`](../docs/api-contract.md) for full request/response shapes.

## CORS

The backend allows all origins (`*`) in development. Update `CORSMiddleware`
in `backend/main.py` before production.
