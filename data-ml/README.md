# PowerPool — Data / ML

**Owner: Member A**

This directory contains the data simulation, solar/weather pipeline, load
forecasting, and scheduling logic for the PowerPool platform.

## Planned Contents

```
data-ml/
├── data/        ← Raw and processed datasets (CSV, Parquet)
│                   Large files should be gitignored or stored in Git LFS
├── models/      ← Trained model artefacts (.pkl, .onnx, etc.)
└── README.md
```

## Integration with the Backend

Member A's pipeline writes to the SQLite database that the backend reads.
The target table is `forecast` with these columns:

| Column | Type | Description |
|---|---|---|
| `timestamp` | TEXT | ISO-8601, e.g. `2026-10-01T06:00:00` |
| `demand_kw` | REAL | Predicted aggregate demand |
| `solar_kw` | REAL | Predicted solar generation |
| `capacity_kw` | REAL | Feeder capacity (constant: 170 kW) |
| `gap_kw` | REAL | `demand_kw - solar_kw - capacity_kw` |
| `is_stress` | INTEGER | `1` if `gap_kw > 0`, else `0` |

Write 96 rows per day (15-minute slots). The backend reads from this table
on every `/forecast` and `/optimize` request.

**DB path:** set `DB_PATH` in `.env` (default: `data/powerpool.db`).

## Mock Data

While the real pipeline is under development, `backend/seed_mock.py` populates
the database with synthetic data (Gaussian demand curve + sinusoidal solar).
Run it from the repo root:

```powershell
python -m backend.seed_mock
```

Your pipeline will replace these rows when ready.
