# LiveBetter — utility engine (water + electricity)

Branch: `Sanjana`. Python + FastAPI. One household account. No machine learning: every number comes from
official tariffs, real bills and stated assumptions, so it can be explained line by line.

## Run
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate        # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m pytest -q                                    # 17 tests, incl. our real CEB and CWA bills
uvicorn utility_engine.api:app --reload --port 8000    # API docs: http://localhost:8000/docs
```
Demo login: `demo@livebetter.mu` / `demo1234` (change with env vars `LIVEBETTER_EMAIL`, `LIVEBETTER_PASSWORD`, `LIVEBETTER_SECRET`).
For quick UI work you can switch login off with `LIVEBETTER_NO_AUTH=1`.

## Data (real) — see `data/SOURCES.md`
| File | Used for |
|---|---|
| `cwa_domestic_tariff_2012.csv` | Water bill: rising blocks Rs 6 / 8 / 17 / 32 per m³ per month (in force since 1 Jan 2012) |
| `ceb_domestic_tariff_2026.csv`, `ceb_minimum_charge_2026.csv` | Electricity bill: 12 rising blocks from Rs 3.63/kWh; minimum charge by tariff 110/120/140 |
| `mu_household_benchmarks_2025.csv` | "You vs Mauritius": 198.9 L/person/day water, 201.5 kWh/month electricity (Statistics Mauritius 2025) |
| `mu_water_*`, `mu_reservoir_*`, `mu_rainfall_*` | Statistics Mauritius tables, ready for extra features (reservoir situation, rain by region) |
| `demo_household.json` | Our team's real CEB bill history (personal details removed); water bills are placeholders until a teammate's CWA bill is entered |

Checked against our own bills: CEB 145 kWh, tariff 140 → consumption Rs 828, total Rs 998 ✔; CWA 0 m³ → Rs 45 + 10 + 14 = Rs 69 ✔.

## How it works
1. **Tariffs** (`tariffs.py`): each price applies only to the units inside its block; minimum charge, meter rent,
   postal/TV licence added; every line says how it was computed.
2. **Daily history** (`history.py`): bills give one number per month. We split each bill into days with a weekday
   pattern and fixed-seed variation, then scale so the days add up exactly to the bill (real totals unchanged).
   After the last bill, days continue at the recent average. These days are labelled `synthetic`.
3. **Forecast** (`forecast.py`): used so far this cycle + 30-day daily average × days left; a low–high range from
   re-sampled recent days; cost from the tariff. Returns period, method, assumptions and source data.
4. **What-if** (`actions.py`, `advice.py`): each action has a formula (e.g. 2 min × 7.6 L/min × 4 showers = 60.8 L/day;
   1.2 kW × 1 h = 1.2 kWh/day). The whole tariff is recalculated with and without it → rupees saved.
5. **Actions change the data**: when an action is marked done, the following synthetic days drop by its saving,
   so forecasts, insights and the activity log all change.
6. **Insights**: per-utility forecast, total projected cost, you vs Mauritius, price-block warnings, top actions by rupees saved.

## API (for the UI)
| Method | Path | Returns |
|---|---|---|
| POST | `/auth/login` | `{token}` → send `Authorization: Bearer <token>` |
| GET/PUT | `/household` | members, sewer, CEB tariff code, TV licence, today |
| GET/POST | `/bills` | bills; POST `{utility, start, end, units}` (from the OCR team) → updated forecast |
| GET | `/utilities/history?utility=water&days=90` | daily values with `kind` bill/synthetic and `saved` |
| GET | `/utilities/forecast` | water + electricity: units low/mid/high, cost, bill breakdown, block, evidence |
| GET | `/actions/catalogue` | actions, parameters, formulas, assumptions, appliance kW list |
| POST | `/household/scenarios` | `{action, params}` → baseline vs action, Rs and units difference |
| POST | `/actions`, `/actions/{id}/complete` | select / mark done (idempotent) |
| GET | `/household/insights` | forecasts, total, benchmarks, recommendations with evidence |
| GET | `/activity` | timestamped log (bill added, action selected/completed, profile updated) |
| POST | `/demo/reset` | back to the demo household |
Errors: `{"detail": {"code", "message", "details"}}` with a specific message (validation errors: HTTP 422).

## Limits (say them in the pitch)
- Daily values are synthetic (bills are monthly); totals per bill are real.
- CEB "last 3 consumptions" (130/143/116) assumed most recent first.
- Action savings use stated assumptions (REU 2016 shower flow and flush volume, typical appliance power).
- Water rising-block rule verified on 0 m³ only so far: add a CWA bill above 10 m³ to check it.

## AI disclosure
Claude (Anthropic) helped research the datasets and tariffs and draft this module; the team reviewed and tested it.
