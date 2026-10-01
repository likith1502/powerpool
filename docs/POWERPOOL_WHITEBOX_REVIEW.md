# PowerPool — White-Box Code Review

Revision reviewed: `main` @ 374602c, plus the fixes in this change · Date: 2026-10-01

## Result

7 defects found and fixed, 1 of them high severity: nudges leaked across scenarios, which corrupted KPIs and re-opened double payment of points. 6 findings are documented as recommendations rather than changed, because they alter an agreed API contract or are out of scope before the deadline. Final suite: **209 passed, 1 skipped, 0 failed**, stable across 3 runs. The headline results are unchanged: Sunny 196.0 → 169.68 kW, 121.5 kWh scheduled, 27 nudges, ₹236.93/day, 56.07 kg CO₂/day.

## Method

| Step | What was done |
|---|---|
| Coverage | `coverage run -m pytest` over `backend`, `ml`, `data`, `frontend`: 71% of 1,789 statements overall; core backend 91–100% (`optimizer` 98%, `services` 98%, `db` 100%, `schemas` 100%, `main` 91%) |
| Static analysis | `pyflakes`: no undefined names or broken imports; 3 unused variables, 14 unused imports (cosmetic) |
| Line-by-line reading | `optimizer.py`, `services.py`, `db.py`, `main.py`, `api_client.py`, `status_badge.py`, `forecast_service.py` |
| Pattern scan | All 16 outbound HTTP calls have timeouts; f-string SQL uses only fixed internal identifiers (no injection path) |
| Input fuzzing | 22 malformed or boundary requests across all routes: no 500 errors |
| Migration test | New code run against a database created by the previous version |
| Browser test | Chromium: optimize Sunny, switch to Cloudy, Resident page; 0 exceptions |

## Defects fixed

| ID | Severity | File | Problem | Fix |
|---|---|---|---|---|
| W1 | High | `services.py`, `db.py` | Nudges carried no scenario, so every scenario's KPIs applied every saved nudge. After optimizing Sunny, Cloudy showed its peak rising from 109.7 to 120.1 kW with 79 kWh "shifted"; after optimizing Heatwave, Sunny showed 179.4 kW (overloaded) | New `scenario_date` column (additive migration); KPIs, after-curve, optimizer, DR, resident nudges and flex capacity all filter by scenario date |
| W2 | High | `services.py` | Sunny → Cloudy → Sunny deleted the accepted nudge, so the same shift could be accepted and paid again (45 → 90 pts). The earlier fix (D8) only covered re-runs of the same scenario, not DR nudges or scenario switches | A re-run now deletes only *pending* nudges for that scenario; accepted and skipped nudges are kept, and their appliances are not re-scheduled |
| W3 | Medium | `main.py` | `/nudges/{id}` and `/flex-capacity` accepted `scenario` but ignored it | Scenario is resolved and passed through |
| W4 | Medium | `optimizer.py` | Feasibility "limiting factors" were stated whenever a result was infeasible, even when false (e.g. "261.5 kW pool is less than the overload"), could print a negative baseload, and hardcoded "65%" | Each reason is stated only when true; compliance comes from configuration |
| W5 | Low | `api_client.py` | Offline demo data valued savings at ₹4/kWh; the project tariff difference is ₹3/kWh | ₹3/kWh |
| W6 | Low | `main.py` | `/leaderboard?limit=-1` returned every household (SQLite treats −1 as unlimited) | `limit` validated to 1–100 |
| W7 | Low | tests | Two tests passed only because of W1 (a DR test relying on cross-scenario nudges; a points test picking an arbitrary nudge) | Tests now start from a defined state and target the same appliance |

Regression tests added for W1, W2, W4 and W6.

## Recommendations (not changed)

| ID | Finding | Why not changed now |
|---|---|---|
| R1 | Invalid input (unknown scenario, compliance = 0) returns `503 Service Unavailable`; `400 Bad Request` is the correct status | 503 is the documented team convention, enforced by 3 test files; changing an agreed API contract is a separate decision |
| R2 | Unknown household (`/nudges/HH999`) returns 200 with an empty list instead of 404 | The frontend treats any non-200 response as "use demo data", so a 404 would show demo nudges |
| R3 | If the backend is up but one endpoint fails, the frontend shows demo data under the green "Live Backend API" badge | Requires a UI change; rare with a seeded database. Unreachable backend is labeled correctly ("Demo Mode (Fallback)") |
| R4 | Appliance windows that cross midnight (earliest > latest) are never shifted | Current appliance data has no such windows |
| R5 | Live forecast uses the last 96 rows of history (`tail(96)`), not features for the requested date | Already listed in known limitations; affects the live-ML toggle only |
| R6 | 14 unused imports, 3 unused variables | Cosmetic |

## Migration safety

Tested on a database created by the previous version (27 nudges, 1 accepted, household HH002 at 45 points): the `scenario_date` column was added, all 27 rows and the 45 points were kept, and re-optimizing Sunny produced 26 new nudges (the accepted one was kept, not re-created). Nudges answered before the migration have no date and therefore still count towards every scenario until that data is reset; nudges created after the migration are fully scoped.
