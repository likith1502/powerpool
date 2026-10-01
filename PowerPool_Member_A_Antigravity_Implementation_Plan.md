# PowerPool Hackathon 2026 --- Member A Implementation Plan

## Data & ML Work Package for Antigravity

**Project:** PowerPool --- Neighbourhood-Scale Load Flexibility
Platform\
**Hackathon:** Yuva Yodha Energy Tech Hackathon 2026 --- Challenge 03:
Grid Reliability / Renewable Intermittency\
**Role:** Member A --- Data & ML Engineer\
**Primary downstream consumer:** Member B --- Backend & Algorithm
Engineer\
**Build constraint:** 12-hour software-only hackathon\
**Primary goal:** Deliver a reliable, self-contained data + ML layer
that gives Member B exactly the data and forecast contracts needed for
the FastAPI backend, optimizer, nudges, KPIs, DR event, and demo.

------------------------------------------------------------------------

# 1. Mission

Implement the complete **Member A Data/ML layer** for PowerPool.

The implementation must:

1.  Generate realistic synthetic electricity consumption data for
    **60--100 households**, at **15-minute resolution**, for **30
    days**.
2.  Model Indian household/appliance usage patterns, including flexible
    appliances that can be shifted away from evening stress periods.
3.  Integrate **Open-Meteo** for Hyderabad weather/solar inputs.
4.  Store the required data in `data/powerpool.db` using the agreed
    SQLite schema.
5.  Generate three deterministic demo scenarios:
    -   Sunny
    -   Cloudy
    -   Heatwave
6.  Train a demand-forecasting model using **LightGBM** when available,
    with a deterministic baseline fallback.
7.  Generate next-24-hour demand forecasts at **96 × 15-minute slots**.
8.  Generate next-24-hour solar forecasts at the same resolution.
9.  Compute:
    -   `gap_kw = demand_kw - solar_kw - capacity_kw`
    -   `is_stress`
10. Ensure at least one demo scenario contains a peak above **170 kW**,
    so Member B's `/optimize` endpoint has something meaningful to
    reduce.
11. Produce a forecast API/data function that Member B can consume
    without changing the agreed schema.
12. Calculate forecasting accuracy metrics, especially **MAPE**, for the
    README/KPI layer.
13. Provide all configuration values through `.env` where appropriate.
14. Produce clean documentation and tests so Member B can integrate
    without reverse-engineering the data layer.

The hackathon plan explicitly assigns Member A synthetic data
generation, Open-Meteo integration, demand and solar forecasting,
accuracy metrics, and SQLite setup. The plan also requires a small
sample by Hour 2 and real data in `data/powerpool.db` by SYNC 1.

------------------------------------------------------------------------

# 2. Important Integration Contract With Member B

Member B should be able to assume the following.

## 2.1 Required SQLite database

File:

``` text
data/powerpool.db
```

Required tables:

``` text
households
appliances
load_history
weather
forecast
nudges
```

Member A owns the data population and forecasting-related tables. Member
B owns the optimizer/nudge/KPI logic.

## 2.2 Exact required columns

### `households`

``` text
id
name
type
block
language
points
```

Constraints:

``` text
type     = low | mid | shop
language = en | hi | te
points   starts at 0
```

### `appliances`

``` text
id
household_id
name
power_kw
duration_slots
flexible
earliest_slot
latest_slot
usual_slot
```

Important:

-   All slot values must be integers from `0` to `95`.
-   Flexible appliances must have a `usual_slot` that can fall in the
    evening stress period; otherwise Member B has nothing meaningful to
    move.
-   Appliance names must support the downstream translation dictionary.

Preferred names:

``` text
Washing machine
Water pump
Inverter charging
Geyser
Iron
E-rickshaw charging
```

Additional appliances are allowed, but the preferred names above must
exist in the generated dataset.

### `load_history`

``` text
household_id
timestamp
kwh
```

Resolution:

``` text
15 minutes
```

For a 30-day dataset:

``` text
96 slots/day
30 days
60–100 households
```

The default implementation should use **100 households** unless
configuration says otherwise.

### `weather`

``` text
timestamp
temp_c
cloud_cover
irradiance_wm2
```

### `forecast`

Exactly:

``` text
timestamp
demand_kw
solar_kw
capacity_kw
gap_kw
is_stress
```

For each requested forecast date:

``` text
96 rows
```

`is_stress` must be represented as `0/1` in SQLite.

### `nudges`

Member B owns this table's behavioral logic, but Member A should create
the schema if Member A is responsible for the initial database setup:

``` text
id
household_id
appliance_id
from_slot
to_slot
kwh_shifted
points
saving_rs
status
```

Allowed status values:

``` text
pending
accepted
skipped
```

------------------------------------------------------------------------

# 3. Repository Structure

Implement or align to this structure:

``` text
powerpool/
│
├── data/
│   ├── generator.py
│   ├── weather.py
│   ├── powerpool.db
│   ├── sample_load.csv
│   └── cached_weather.csv
│
├── ml/
│   ├── forecast_demand.py
│   ├── forecast_solar.py
│   ├── metrics.py
│   ├── features.py
│   ├── pipeline.py
│   └── models/
│       ├── demand_model.txt
│       └── metadata.json
│
├── tests/
│   ├── test_generator.py
│   ├── test_weather.py
│   ├── test_forecast.py
│   ├── test_database.py
│   └── test_scenarios.py
│
├── scripts/
│   ├── build_dataset.py
│   ├── build_forecasts.py
│   └── validate_member_a_output.py
│
├── .env.example
├── requirements.txt
└── README_MEMBER_A.md
```

If the existing repository already has an equivalent structure, **modify
existing files instead of creating duplicate implementations**.

Before coding, inspect the repository and reuse existing conventions.

------------------------------------------------------------------------

# 4. Phase 0 --- Repository Inspection

Antigravity must first inspect:

``` text
README.md
requirements.txt
.gitignore
data/
ml/
backend/
frontend/
src/
```

Search for existing implementations of:

``` text
powerpool.db
generator
forecast
weather
Open-Meteo
LightGBM
demand
solar
households
appliances
```

Do not overwrite working code blindly.

Determine:

1.  Existing database initialization.
2.  Existing schema.
3.  Existing `.env` variables.
4.  Existing backend expectations.
5.  Existing mock data from `seed_mock.py`.
6.  Existing branch/code conventions.
7.  Existing API response structures.

If Member B already has a `seed_mock.py`, use its field names as an
additional compatibility check.

------------------------------------------------------------------------

# 5. Phase 1 --- Configuration

Create or update `.env.example`.

Recommended configuration:

``` env
POWERPOOL_NUM_HOUSEHOLDS=100
POWERPOOL_DAYS=30
POWERPOOL_SLOT_MINUTES=15

FEEDER_CAPACITY_KW=170

PEAK_TARIFF_RS_PER_KWH=8
OFFPEAK_TARIFF_RS_PER_KWH=5

CO2_FACTOR_KG_PER_KWH=0.7

OPEN_METEO_LAT=17.3850
OPEN_METEO_LON=78.4867

OPEN_METEO_TIMEOUT_SECONDS=10

DEMAND_MODEL_PATH=ml/models/demand_model.txt

RANDOM_SEED=42

STRESS_MARGIN_KW=0
```

### Important

Do not hard-code values throughout the Python code.

Use environment variables with safe defaults.

The feeder capacity, tariffs, and CO2 factor must be configurable
because Member B explicitly needs the real values for `.env`.

If the hackathon organizers/team provide different official values,
those values must override the defaults.

------------------------------------------------------------------------

# 6. Phase 2 --- Household Model

Create deterministic household profiles.

Use three required household types:

``` text
low
mid
shop
```

Example conceptual distributions:

### Low-income household

Typical appliances:

``` text
LED lights
fan
TV
refrigerator
water pump
washing machine
geyser
iron
```

### Middle-income household

Typical appliances:

``` text
LED lights
fans
TV
refrigerator
washing machine
geyser
iron
water pump
inverter charging
```

### Small shop

Typical appliances:

``` text
lighting
fan
refrigerator
display/load equipment
water pump
inverter charging
```

The exact appliance list can be adjusted to maintain realistic total
feeder load, but the required flexible appliance names must be
represented.

------------------------------------------------------------------------

# 7. Phase 3 --- Appliance Model

Represent every appliance with:

``` python
{
    "name": str,
    "power_kw": float,
    "duration_slots": int,
    "flexible": int,
    "earliest_slot": int,
    "latest_slot": int,
    "usual_slot": int
}
```

## Flexible appliances

The core flexible set should include:

``` text
Washing machine
Water pump
Inverter charging
Geyser
Iron
E-rickshaw charging
```

Each should have:

-   realistic power
-   realistic duration
-   `flexible = 1`
-   an allowed scheduling window
-   a `usual_slot`
-   a meaningful evening usage case for at least some households

Example scheduling philosophy:

``` text
Washing machine:
  usual = evening
  allowed = late morning through evening

Water pump:
  usual = morning/evening
  allowed = morning through afternoon

Geyser:
  usual = evening
  allowed = afternoon/evening

Iron:
  usual = evening
  allowed = afternoon/evening

Inverter charging:
  usual = evening
  allowed = afternoon/evening

E-rickshaw charging:
  usual = evening/night
  allowed = afternoon/night
```

Do not make every appliance flexible.

Non-flexible appliances should remain in their natural usage slots.

------------------------------------------------------------------------

# 8. Phase 4 --- Synthetic Load Generation

Generate 15-minute load profiles for every household.

Required resolution:

``` text
15 minutes
```

Required slots:

``` text
0–95
```

For every household and timestamp:

``` text
load_kwh = sum(appliance consumption during the slot)
```

The generator should model:

### Morning activity

Approximately:

``` text
06:00–09:00
```

### Midday solar-rich period

Approximately:

``` text
10:00–16:00
```

### Evening peak

Approximately:

``` text
18:30–22:00
```

The evening period must be clearly higher than the midday period.

This is critical because PowerPool's purpose is to shift flexible
consumption away from the evening renewable-supply gap.

------------------------------------------------------------------------

# 9. Realistic Randomness

Use deterministic randomness:

``` python
np.random.default_rng(RANDOM_SEED)
```

Do not use uncontrolled random calls.

Add small household-specific variation:

``` text
±5–15%
```

and day-level variation.

Avoid unrealistic negative consumption.

All generated values must satisfy:

``` text
kwh >= 0
```

------------------------------------------------------------------------

# 10. Required Sample Dataset by Hour 2

Create:

``` text
data/sample_load.csv
```

It must contain enough rows for Member B to verify the integration.

At minimum include:

``` text
household_id
timestamp
kwh
```

Also create a small sample database if practical:

``` text
data/powerpool.db
```

with several households and appliances.

The purpose is to let Member B verify that the backend reads the real
column names rather than depending only on mocks.

------------------------------------------------------------------------

# 11. Phase 5 --- Open-Meteo Integration

Create:

``` text
data/weather.py
```

Responsibilities:

1.  Fetch Hyderabad weather.
2.  Request historical weather where available for model training.
3.  Request forecast weather for demo dates.
4.  Obtain:
    -   temperature
    -   cloud cover
    -   irradiance/solar radiation data as available
5.  Convert timestamps into the project's 15-minute representation.
6.  Cache the result locally.

The hackathon plan specifies Open-Meteo for Hyderabad weather/irradiance
and recommends caching weather data if the API fails.

------------------------------------------------------------------------

# 12. Weather Fallback

Never make the whole demo depend on an external API.

If Open-Meteo fails:

``` text
1. Try cached_weather.csv
2. If cache exists, use it
3. Otherwise generate deterministic synthetic weather
4. Log the fallback clearly
```

The code must not crash merely because Open-Meteo is unavailable.

Use a timeout.

Example:

``` python
requests.get(..., timeout=10)
```

------------------------------------------------------------------------

# 13. Weather Validation

Validate:

``` text
temperature is finite
cloud cover is within expected range
irradiance >= 0
timestamps are parseable
```

Do not allow:

``` text
NaN
inf
negative irradiance
duplicate timestamps
```

to enter the forecasting pipeline.

------------------------------------------------------------------------

# 14. Phase 6 --- Solar Forecasting

Create:

``` text
ml/forecast_solar.py
```

The primary method should be transparent and explainable.

Conceptually:

``` text
solar_kw =
    irradiance_wm2
    × panel_area_m2
    × panel_efficiency
    / 1000
```

Then aggregate the available household/community solar generation.

Apply realistic bounds.

Solar must approximately follow:

``` text
night       → 0
morning     → rising
midday      → maximum
evening     → falling
night       → 0
```

Cloudy scenarios should reduce solar generation.

Heatwave scenarios should increase temperature and may reduce effective
generation through an explicit scenario factor if needed.

Keep all assumptions configurable.

------------------------------------------------------------------------

# 15. Solar Scenario Rules

Create three deterministic scenarios.

## Sunny

Characteristics:

``` text
low cloud cover
high irradiance
normal temperature
strong midday solar
```

## Cloudy

Characteristics:

``` text
higher cloud cover
lower irradiance
reduced solar output
```

## Heatwave

Characteristics:

``` text
high temperature
higher household demand
solar still present
stronger evening stress
```

The three scenarios must be selectable by date.

Recommended demo dates:

``` text
2026-10-01 = sunny
2026-10-02 = cloudy
2026-10-03 = heatwave
```

These dates are an agreed integration convention from the Member B
requirements. Keep the mapping configurable.

------------------------------------------------------------------------

# 16. Phase 7 --- Demand Forecasting

Create:

``` text
ml/forecast_demand.py
```

Use LightGBM as the primary model.

Target:

``` text
next-24-hour feeder demand
```

Resolution:

``` text
96 predictions
```

Required input features should include:

``` text
hour
minute
slot
day_of_week
is_weekend
temperature
lag demand
rolling demand
```

Useful additional features:

``` text
lag_1
lag_4
lag_96
lag_192
rolling_mean_4
rolling_mean_96
temperature_lag
```

Do not use future target values.

Avoid data leakage.

------------------------------------------------------------------------

# 17. Feeder Demand Aggregation

The model target should be **feeder-level demand**, not
individual-household demand, unless the existing architecture
specifically requires otherwise.

Aggregate household load:

``` text
feeder_demand_kw(t)
    = sum(household_load_kw(t))
```

Remember:

``` text
15-minute energy kWh
```

and

``` text
power kW
```

are different.

If a 15-minute energy value is:

``` text
kwh = 0.75
```

then equivalent average slot power is:

``` text
kw = 0.75 / 0.25
   = 3.0 kW
```

Maintain units consistently.

------------------------------------------------------------------------

# 18. Demand Forecast Baseline

Before training LightGBM, implement a baseline.

Recommended:

``` text
same 15-minute slot average from recent days
```

or:

``` text
same slot average over previous 7 days
```

The baseline is required as a fallback if LightGBM is unavailable or
underperforms.

The hackathon plan explicitly allows a seasonal baseline as the
fallback.

------------------------------------------------------------------------

# 19. MAPE Evaluation

Implement:

``` text
ml/metrics.py
```

At minimum:

``` text
MAPE
MAE
RMSE
```

For MAPE, protect against zero actual values.

Use:

``` python
epsilon = 1e-6
```

and ignore or safely handle near-zero denominators.

Report:

``` text
model
MAPE
MAE
RMSE
```

The hackathon target is:

``` text
MAPE < 10%
```

Do not fake or manually force the metric.

If the actual model does not reach the target, report the measured value
and use the baseline/fallback where appropriate.

------------------------------------------------------------------------

# 20. Forecast Generation

Create a reusable function such as:

``` python
forecast_day(date, scenario=None)
```

Return exactly 96 records.

Each record:

``` python
{
    "timestamp": "...",
    "demand_kw": ...,
    "solar_kw": ...,
    "capacity_kw": ...,
    "gap_kw": ...,
    "is_stress": 0 or 1
}
```

Compute:

``` python
gap_kw = demand_kw - solar_kw - capacity_kw
```

Set:

``` python
is_stress = int(gap_kw > 0)
```

Do not use a different gap formula.

------------------------------------------------------------------------

# 21. Stress Window

The stress window should be data-driven from the gap.

Expected demo behavior:

``` text
evening demand ↑
solar ↓
gap ↑
stress = 1
```

The hackathon example focuses on approximately:

``` text
18:30–22:00
```

but the implementation should identify stress from the computed gap
rather than simply hard-coding the time.

------------------------------------------------------------------------

# 22. Ensure a Meaningful Demo

At least one demo scenario must have:

``` text
peak demand > 170 kW
```

This is necessary because Member B's optimizer needs a stress condition
to demonstrate load shifting.

Do not simply change the displayed number.

Instead, tune the synthetic household/appliance parameters so that the
generated feeder genuinely reaches the required peak.

The validation script must check this.

Example:

``` text
peak_kw > FEEDER_CAPACITY_KW
```

If false:

1.  increase realistic evening appliance participation,
2.  increase number of households,
3.  adjust appliance diversity,
4.  or adjust household load multipliers.

Do not create unrealistic spikes.

------------------------------------------------------------------------

# 23. Database Initialization

Create a robust database initializer.

It must:

1.  Create `data/powerpool.db`.
2.  Create all required tables.
3.  Add appropriate indexes.
4.  Clear/rebuild tables when running in rebuild mode.
5.  Preserve the schema expected by Member B.

Suggested indexes:

``` sql
CREATE INDEX IF NOT EXISTS idx_load_history_timestamp
ON load_history(timestamp);

CREATE INDEX IF NOT EXISTS idx_load_history_household
ON load_history(household_id);

CREATE INDEX IF NOT EXISTS idx_forecast_timestamp
ON forecast(timestamp);

CREATE INDEX IF NOT EXISTS idx_appliances_household
ON appliances(household_id);
```

------------------------------------------------------------------------

# 24. Database Population Pipeline

Implement one command that can build everything.

Example:

``` bash
python scripts/build_dataset.py
```

Expected sequence:

``` text
1. initialize database
2. generate households
3. generate appliances
4. generate 30-day load
5. fetch/cache weather
6. generate scenario data
7. train/load demand model
8. generate solar forecast
9. generate forecast table
10. validate outputs
```

The process must be deterministic with the same random seed.

------------------------------------------------------------------------

# 25. Three Demo Dates

Populate the forecast table with at least:

``` text
2026-10-01
2026-10-02
2026-10-03
```

Suggested mapping:

``` text
2026-10-01 → sunny
2026-10-02 → cloudy
2026-10-03 → heatwave
```

Each date must have:

``` text
96 forecast rows
```

Therefore the minimum demo forecast rows are:

``` text
3 × 96 = 288
```

------------------------------------------------------------------------

# 26. Exact Member B Handoff

Member B needs to be able to do:

``` text
GET /forecast?date=2026-10-01
```

and receive:

``` json
[
  {
    "timestamp": "2026-10-01T00:00:00",
    "demand_kw": 100.0,
    "solar_kw": 0.0,
    "capacity_kw": 170.0,
    "gap_kw": -70.0,
    "is_stress": 0
  }
]
```

The exact numerical values will come from the generated data.

Do not add unnecessary required fields to this contract.

Optional metadata can be returned separately.

------------------------------------------------------------------------

# 27. Member B Integration Data

Member B also needs:

## Household data

``` text
id
name
type
block
language
points
```

## Appliance data

``` text
id
household_id
name
power_kw
duration_slots
flexible
earliest_slot
latest_slot
usual_slot
```

This allows B's greedy scheduler to:

1.  Find appliances running in stress slots.
2.  Check their allowed movement windows.
3.  Find non-stress/solar-surplus slots.
4.  Move flexible consumption.
5.  Generate nudges.

------------------------------------------------------------------------

# 28. Appliance Translation Compatibility

Member B's translation system expects these names:

``` text
Washing machine
Water pump
Inverter charging
Geyser
Iron
E-rickshaw charging
```

Do not randomly rename these to variants such as:

``` text
washer
pump
EV
water heater
press
```

unless aliases are explicitly supported.

If additional appliances exist, Member B should be able to fall back to
their English name.

------------------------------------------------------------------------

# 29. Validation Script

Create:

``` text
scripts/validate_member_a_output.py
```

It should verify all of the following.

## Database

``` text
database exists
required tables exist
required columns exist
```

## Households

``` text
60–100 households
type values valid
language values valid
points start at 0
```

## Appliances

``` text
all household IDs valid
slot values 0–95
power_kw > 0
duration_slots > 0
required flexible appliances present
```

## Load

``` text
30 days
15-minute resolution
no negative values
no NaN/inf
```

## Weather

``` text
timestamps valid
no invalid irradiance
```

## Forecast

For each demo date:

``` text
exactly 96 rows
no duplicate timestamps
demand_kw >= 0
solar_kw >= 0
capacity_kw > 0
gap_kw == demand_kw - solar_kw - capacity_kw
is_stress in {0,1}
```

## Demo condition

At least one:

``` text
peak demand > 170 kW
```

## MAPE

``` text
metric exists
numeric value
```

------------------------------------------------------------------------

# 30. Unit Tests

Implement tests for:

### Generator

``` text
test_household_count
test_appliance_schema
test_load_resolution
test_no_negative_load
test_deterministic_seed
```

### Weather

``` text
test_weather_schema
test_weather_fallback
test_irradiance_nonnegative
```

### Solar

``` text
test_solar_zero_at_night
test_solar_higher_at_midday
test_cloudy_less_than_sunny
```

### Forecast

``` text
test_forecast_has_96_slots
test_forecast_schema
test_gap_formula
test_stress_flag
```

### Scenarios

``` text
test_sunny_scenario
test_cloudy_scenario
test_heatwave_scenario
test_peak_above_capacity
```

### Database

``` text
test_required_tables
test_required_columns
test_forecast_row_count
```

------------------------------------------------------------------------

# 31. Data Quality Rules

Never allow these into the final database:

``` text
NaN
inf
negative kWh
negative kW
duplicate timestamps
duplicate appliance IDs
orphan household IDs
invalid language
invalid household type
slot outside 0–95
```

Use assertions or explicit validation errors.

------------------------------------------------------------------------

# 32. Performance Requirements

This is a 12-hour hackathon.

Prioritize:

``` text
reliable
fast
deterministic
simple
explainable
```

Do not over-engineer.

Avoid:

``` text
LSTM
deep learning
complex distributed pipelines
unnecessary microservices
heavy optimization frameworks
```

The hackathon plan specifically recommends LightGBM for tabular
forecasting and a transparent solar physics calculation.

------------------------------------------------------------------------

# 33. LightGBM Fallback

The environment may have difficulty installing LightGBM, particularly
during deployment.

Therefore:

``` python
try:
    import lightgbm
except ImportError:
    use_baseline_model()
```

The application must still run without LightGBM.

Record which model was used:

``` text
model_type = lightgbm
```

or:

``` text
model_type = seasonal_baseline
```

Do not let a missing optional dependency break the complete application.

------------------------------------------------------------------------

# 34. Model Artifact

If LightGBM is available, save the trained model:

``` text
ml/models/demand_model.txt
```

Save metadata:

``` text
ml/models/metadata.json
```

Metadata should include:

``` json
{
  "model_type": "LightGBM",
  "features": [],
  "training_start": "",
  "training_end": "",
  "mape": 0.0,
  "mae": 0.0,
  "rmse": 0.0,
  "random_seed": 42
}
```

Do not commit large/generated artifacts if the team's `.gitignore`
policy excludes them.

------------------------------------------------------------------------

# 35. Output Files for Member B

Produce:

``` text
data/sample_load.csv
data/cached_weather.csv
data/powerpool.db
```

and, if useful:

``` text
outputs/forecast_2026-10-01.csv
outputs/forecast_2026-10-02.csv
outputs/forecast_2026-10-03.csv
outputs/forecast_metrics.json
```

The database remains the primary integration artifact.

------------------------------------------------------------------------

# 36. Recommended Forecast CSV

Use:

``` text
timestamp,demand_kw,solar_kw,capacity_kw,gap_kw,is_stress
```

Exactly.

------------------------------------------------------------------------

# 37. Scenario Behavior

The scenarios should produce visibly different curves.

## Sunny

Expected:

``` text
strong solar midday
lower net gap midday
evening stress after solar falls
```

## Cloudy

Expected:

``` text
reduced midday solar
earlier/larger net gap
more stress than sunny
```

## Heatwave

Expected:

``` text
higher temperature
higher household cooling demand
stronger evening demand
potentially larger stress gap
```

The scenario differences must be generated from actual data
transformations, not merely labels.

------------------------------------------------------------------------

# 38. Forecast Plot Outputs

Generate plots useful for Member B/C and the pitch.

At minimum:

``` text
demand vs solar vs capacity
before optimization
```

For three scenarios:

``` text
sunny
cloudy
heatwave
```

Also generate:

``` text
actual vs predicted demand
```

for model validation.

Save under:

``` text
outputs/plots/
```

If plots are not needed by the final repository, they can be generated
on demand rather than committed.

------------------------------------------------------------------------

# 39. KPI Support

Provide the data needed for these KPIs:

``` text
peak reduction %
kWh shifted
solar self-consumption %
CO2 avoided
households participating
```

Member B owns the post-optimization KPI calculation.

Member A should ensure the input data supports:

``` text
baseline demand
solar generation
capacity
load
```

and provide the CO2 factor through configuration.

------------------------------------------------------------------------

# 40. Important Formula Consistency

Use these formulas consistently.

### Gap

``` text
gap_kw = demand_kw - solar_kw - capacity_kw
```

### Stress

``` text
is_stress = 1 if gap_kw > 0 else 0
```

### Slot power conversion

``` text
kW = kWh / 0.25
```

because each slot is 15 minutes.

### CO2

Member B can calculate:

``` text
co2_avoided = kwh_shifted × CO2_FACTOR_KG_PER_KWH
```

using the configured factor.

### Savings

Member B owns savings calculation:

``` text
saving_rs = shifted_kwh × tariff_difference
```

Member A only needs to expose/configure the tariff values.

------------------------------------------------------------------------

# 41. Antigravity Implementation Sequence

Execute in this exact order.

## Step 1 --- Inspect repository

Do not code yet.

Identify existing:

``` text
database
mock data
backend contracts
requirements
environment variables
```

## Step 2 --- Implement schemas/database

Create:

``` text
households
appliances
load_history
weather
forecast
nudges
```

## Step 3 --- Implement generator

Create:

``` text
60–100 households
30 days
15-minute resolution
```

## Step 4 --- Generate sample

Immediately create:

``` text
data/sample_load.csv
```

so Member B can integrate.

## Step 5 --- Implement Open-Meteo

Add:

``` text
API fetch
cache
fallback
validation
```

## Step 6 --- Implement solar model

Add:

``` text
sunny
cloudy
heatwave
```

## Step 7 --- Implement demand features

Create lag/rolling/calendar/weather features.

## Step 8 --- Train LightGBM

Add:

``` text
train
validate
save model
calculate metrics
```

## Step 9 --- Add baseline fallback

Make the complete system runnable without LightGBM.

## Step 10 --- Build forecast pipeline

Generate exactly:

``` text
96 rows/date
```

## Step 11 --- Populate three demo dates

``` text
2026-10-01
2026-10-02
2026-10-03
```

## Step 12 --- Validate peak

Ensure:

``` text
max demand > 170 kW
```

for at least one demo scenario.

## Step 13 --- Run validation script

Fix every validation failure.

## Step 14 --- Run unit tests

``` bash
pytest -q
```

## Step 15 --- Hand off to Member B

Send:

``` text
database path
sample CSV
schema
forecast contract
demo dates
MAPE
model type
configuration variables
```

------------------------------------------------------------------------

# 42. Commands Antigravity Should Leave Working

The final implementation should support commands similar to:

``` bash
python scripts/build_dataset.py
```

``` bash
python scripts/build_forecasts.py
```

``` bash
python scripts/validate_member_a_output.py
```

``` bash
pytest -q
```

If the existing repository uses different script names, preserve its
conventions, but provide equivalent functionality.

------------------------------------------------------------------------

# 43. Member B Handoff Message

After implementation, produce a concise handoff document:

``` text
MEMBER A → MEMBER B

Database:
data/powerpool.db

Forecast dates:
2026-10-01 = sunny
2026-10-02 = cloudy
2026-10-03 = heatwave

Forecast:
96 rows/date

Endpoint contract:
GET /forecast?date=YYYY-MM-DD

Columns:
timestamp
demand_kw
solar_kw
capacity_kw
gap_kw
is_stress

Household columns:
id
name
type
block
language
points

Appliance columns:
id
household_id
name
power_kw
duration_slots
flexible
earliest_slot
latest_slot
usual_slot

Required appliance names:
Washing machine
Water pump
Inverter charging
Geyser
Iron
E-rickshaw charging

Feeder capacity:
configured through FEEDER_CAPACITY_KW

Forecast model:
LightGBM / seasonal baseline fallback

MAPE:
<actual measured value>

Peak:
<actual measured peak>

Validation:
PASS/FAIL
```

------------------------------------------------------------------------

# 44. Acceptance Criteria

The task is complete only when all of these are true.

## Data

-   [ ] 60--100 households generated.
-   [ ] 30 days of load data generated.
-   [ ] 15-minute resolution.
-   [ ] Realistic morning/midday/evening patterns.
-   [ ] Required flexible appliances present.
-   [ ] `sample_load.csv` exists.

## Weather

-   [ ] Open-Meteo integration implemented.
-   [ ] Weather cached locally.
-   [ ] Offline fallback works.
-   [ ] Weather values validated.

## Solar

-   [ ] Solar forecast implemented.
-   [ ] Nighttime solar is approximately zero.
-   [ ] Midday solar is highest.
-   [ ] Cloudy scenario reduces solar.
-   [ ] Three scenarios work.

## Demand ML

-   [ ] LightGBM implemented.
-   [ ] Baseline fallback implemented.
-   [ ] No future leakage.
-   [ ] MAPE calculated.
-   [ ] MAE calculated.
-   [ ] RMSE calculated.
-   [ ] Model artifact saved when LightGBM is available.

## Database

-   [ ] `data/powerpool.db` exists.
-   [ ] Required tables exist.
-   [ ] Required columns match exactly.
-   [ ] Demo forecast has exactly 96 rows/date.

## Stress

-   [ ] `gap_kw` uses the agreed formula.
-   [ ] `is_stress` is 0/1.
-   [ ] At least one scenario has peak \> 170 kW.

## Integration

-   [ ] Member B can read the database.
-   [ ] Member B can obtain 96 forecast rows.
-   [ ] Appliance names match translation mappings.
-   [ ] `.env` contains required configuration.
-   [ ] No API dependency prevents the demo.

## Quality

-   [ ] Unit tests pass.
-   [ ] Validation script passes.
-   [ ] No NaN/inf.
-   [ ] No negative loads.
-   [ ] No invalid slot values.
-   [ ] README documentation updated.
-   [ ] Member B handoff completed.

------------------------------------------------------------------------

# 45. What NOT to Build

Do not spend Member A time on:

``` text
real smart meters
hardware
real DISCOM integration
authentication
payments
Telegram bot
LLM chatbot
complex optimization
deep-learning forecasting
production-grade cloud infrastructure
```

These are outside the core Member A scope and the hackathon plan
explicitly prioritizes the simulator, forecasting, load shifting,
before/after chart, nudge screen, and KPIs.

------------------------------------------------------------------------

# 46. Time-Pressure Fallback

If time is running out, prioritize in this order:

### Tier 1 --- absolutely required

``` text
1. SQLite schema
2. synthetic load generator
3. sample CSV
4. Open-Meteo/cache
5. solar calculation
6. demand forecast
7. forecast table
8. three demo dates
9. peak > 170 kW
10. validation
```

### Tier 2

``` text
11. MAPE/MAE/RMSE
12. model artifact
13. plots
14. additional tests
```

### Tier 3

``` text
15. advanced tuning
16. additional scenario realism
17. extra visualizations
```

Never sacrifice the database contract or 96-slot forecast for optional
ML sophistication.

------------------------------------------------------------------------

# 47. Final Antigravity Instruction

Implement this work package as **production-quality hackathon code**,
not as a tutorial or pseudocode.

Before changing code:

1.  Inspect the repository.
2.  Reuse existing files where possible.
3.  Preserve Member B's agreed database/API contract.
4.  Implement incrementally.
5.  Run the generator.
6.  Inspect actual outputs.
7.  Run validation.
8.  Run tests.
9.  Fix errors.
10. Provide the final Member B handoff.

The most important success criterion is:

> **Member B must be able to plug `data/powerpool.db` into the backend
> and immediately obtain valid household/appliance data and 96-slot
> demand/solar/gap forecasts for the three demo scenarios without
> modifying the data contract.**

The implementation should favor **determinism, explainability,
robustness, and integration reliability** over unnecessary model
complexity.
