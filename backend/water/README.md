# LiveBetter: water module (standalone)

Owner: Sanjana (branch `Sanjana`). Python + FastAPI. Works on its own; the Household AI reads `GET /water/summary`.
No machine learning: every number comes from the official CWA tariff, real bills/meter readings and stated assumptions.

## Run
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate                     # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m pytest -q water/tests            # 24 tests
uvicorn water.app:app --reload --port 8001 # docs: http://localhost:8001/docs
```
Demo login `demo@livebetter.mu` / `demo1234` (env `LIVEBETTER_EMAIL`, `LIVEBETTER_PASSWORD`, `LIVEBETTER_SECRET`).
`LIVEBETTER_NO_AUTH=1` switches login off for quick UI work.

## API (all under `/water`, send `Authorization: Bearer <token>`)
| Method | Path | What it does |
|---|---|---|
| POST | `/auth/login` | `{email, password}` → `{token}` (shared by all modules) |
| GET/PUT | `/water/profile` | members, sewer, region, monthly budget, showers per day, shower minutes, measured flow |
| GET/POST | `/water/bills` | POST `{start, end, m3, start_reading?, end_reading?}` (from OCR) → bill + new forecast |
| DELETE | `/water/bills/{id}` | remove a wrong bill |
| GET/POST | `/water/readings` | POST `{date, index_m3}` meter reading between bills → new forecast |
| DELETE | `/water/readings/{id}` | remove a wrong reading |
| GET | `/water/history?days=90` | daily m3, `kind` = bill / reading / synthetic, `saved` |
| GET | `/water/forecast` | this cycle: m3 low/mid/high, Rs low/mid/high, bill lines, price block, method, confidence |
| GET | `/water/actions/catalogue` | actions, parameters, limits, formulas, assumptions |
| POST | `/water/scenarios` | `{action, params}` → baseline vs with action (m3, Rs) |
| GET/POST | `/water/actions` | list / select an action |
| POST | `/water/actions/{id}/complete` | mark done (idempotent) → later days drop |
| GET | `/water/insights` | forecast, you vs Mauritius, budget, alerts, ranked actions with evidence |
| GET | `/water/context` | season: rainfall and reservoir levels for this month (Statistics Mauritius) |
| GET | `/water/summary` | **shared module contract** for the Household AI |
| GET | `/water/activity` | log: bill / reading added, action selected / completed, profile updated |
| POST | `/water/demo/reset` | back to the demo household |

Errors: `{"detail": {"code", "message", "details"}}`, e.g. 409 overlapping bill, 422 "The meter cannot go backwards".

## How it works
1. **Tariff** (`tariff.py`): CWA rising blocks, Rs 45 minimum, wastewater if on sewer, meter rent, postal.
   Each bill line says how it was computed. Matches our real bill (0 m³ → Rs 69).
2. **Daily history** (`history.py`): bills and meter readings are real totals. Each is split into days
   (weekend ×1.12, ±12% variation, fixed seed) and scaled so the days add up exactly to the real m³.
   After the last measurement days continue at the latest rate. Days are labelled bill / reading / synthetic.
3. **Forecast** (`forecast.py`): used so far this cycle + daily rate × days left; range from re-sampling; cost from the tariff.
   Confidence: low (0–1 real bill), medium (2, or a reading since the last bill), good (3+, or 1 + a reading).
4. **What-if** (`actions.py`, `advice.scenario`): litres/day from a visible formula → whole tariff recalculated.
5. **Actions change the data**: completed actions lower the days after the last measurement.
6. **Insights** (`advice.py`): you vs Mauritius (198.9 L/person/day), budget check, next-price-block alert,
   possible-leak alert (latest period ≥30% above usual), season context, ranked actions with evidence.

## Limits (say them in the pitch)
- Daily values are synthetic; bill and reading totals are real.
- Demo water bills are placeholders until a real CWA bill is entered (the first real bill replaces them).
- Action defaults are North-American averages (REU 2016, US EPA); users can enter their own values.
- Reservoir/rain context is 2024–2025 data, not live.

## AI disclosure
Claude (Anthropic) helped research the data and draft this module; the team reviewed and tested it.
