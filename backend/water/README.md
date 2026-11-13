# LiveBetter: water module (standalone)

Owner: Sanjana (branch `Sanjana`). Python + FastAPI. Follows the *Assessment Questions* spec and the *Complete
User Walkthrough* (13 Nov 2026). The lead AI reads `GET /water/summary`.
**No machine learning:** rules and formulas whose numbers come from data (bills, CWA tariff, Statistics Mauritius,
published studies), so every number can be explained line by line.

## Run
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate                     # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m pytest -q water/tests            # 36 tests (spec checklist + demo storyline)
uvicorn water.app:app --reload --port 8001 # docs: http://localhost:8001/docs
```
Login `demo@livebetter.mu` / `demo1234` (env `LIVEBETTER_EMAIL`, `LIVEBETTER_PASSWORD`, `LIVEBETTER_SECRET`).
`LIVEBETTER_NO_AUTH=1` switches login off for UI work. The account starts **empty** (no fabricated data).
`POST /water/demo/reset?sample=true` loads a clearly labelled **fictional sample household** for rehearsal.

## Honesty rules (from the spec) and how they are enforced
| Rule | Where |
|---|---|
| No bill or readings → no personal forecast | `forecast()` returns `status: insufficient_data`, no m3, no Rs |
| One bill → preliminary, period-normalised | 18 m3 / 30 days = 600 L/day; × days in the next cycle |
| "Better supported" needs measured evidence | 3+ bills **and** 2+ checks (back-tests or saved forecast vs later bill) |
| Completeness ≠ reliability | `data_completeness` (answers, bill fields) vs `reliability` (errors of past estimates) |
| Answers are not consumption | Assessment answers never change the estimate; only a sized W5 change does, as its own line |
| Changes are labelled, never hidden | Every estimate has `lines`: observed / season / user_declared / action / correction |
| Current month only from meter readings | `GET /water/forecast/current` → `needs_readings` without them |
| What-if never edits history | Scenarios are compared side by side; tests check the saved state is unchanged |
| Not enough data → say so | Scenarios return `needs_input` with the exact question ("Not sure" is not enough) |
| Cost only from the tariff | CWA rising blocks + minimum + meter + postal (+ wastewater); `cost.note = tariff_calculated_only` |
| OCR values only after the user confirms | `POST /water/bills` takes confirmed values; `ocr_id` kept for provenance |

## How the estimate is built (next billing cycle)
1. **Observed:** m³ per day from the last (up to 3) confirmed bills × days in the next cycle.
2. **Season (data):** hotter months use more water: +2.6 %/°C without AC, +0.7 %/°C with AC (Singapore, 121,480
   households, Salvo 2018) on Mauritian monthly temperatures (ERA5 2016–2025). Weekends ×1.12 (17 metered homes).
3. **Expected change:** W5 answer, only if the user gave a size (%).
4. **Completed goals:** savings of actions completed after the last bill.
5. **Correction:** after 2+ checks, the median actual/predicted ratio, if ≥3 % off ("we were 4 % too low").
6. **Cost:** CWA tariff on the total; range from bill-to-bill variation (3+ bills) or real day-to-day spread.

## The learning loop (bill vs prediction)
- Every confirmed bill saves a **forecast snapshot** for the next cycle (`forecast_issued`).
- When the next bill arrives, it is compared with that snapshot (`forecast_checked`: predicted vs actual m3 and Rs).
- **Back-tests:** each past bill is also predicted from the bills before it, which gives genuine checks from day one.
- Results feed reliability, the visible correction line, and `forecast_vs_actual` in `/water/summary`.

## Activity log (everything is an event)
`household_answered, profile_updated, assessment_answered (versioned), bill_confirmed, bill_replaced, bill_deleted,
reading_added, reading_deleted, forecast_issued, forecast_checked, scenario_run, scenario_saved_as_goal, action_completed`

## What-if scenarios
| Scenario | Formula | Needs |
|---|---|---|
| `shorter_showers` | people × minutes less × 7.9 L/min | G1 people, W1 |
| `extra_showers` | extra showers × W1 minutes × 7.9 L/min | W1, number of extra showers |
| `greywater_flush` | flushes replaced × 9.8 L | G1, W2 |
| `full_laundry_loads` | loads less × 111 L / 7 | W3 |
| `fix_dripping_tap` | taps × 31 L/day (EPA) | nothing |
| `less_outdoor_water` | sessions less × litres per session / 7 | W4 (not "never"), **litres per session** (measured by the user) |
| `guests_or_away` | (your L/day ÷ people) × people change × days | G1, a bill, people and days |
| `custom_change` | estimate × % | a bill, the % |
Without a bill, scenarios give **litres only** (`status: partial`). Rupees = the whole tariff recalculated.
Mauritian defaults (team decision): roof tank, no bucket baths, car wash about once a month, no water cuts; other
situations go in the what-if.

## Screen → endpoint map (for the UI)
| Walkthrough screen | Endpoints |
|---|---|
| General setup (4 questions) | `GET /water/onboarding/questions`, `PUT /water/household` (shared; M2 will own it) |
| Dashboard "not enough data" card | `GET /water/summary` → `status`, `status_message`, `data_completeness.missing[].prompt` |
| Water assessment (5 optional questions) | `GET/PUT /water/assessment` (partial saves allowed), `GET /water/assessment/versions` |
| Upload / confirm bill | `POST /water/bills` (after OCR review), `PUT /water/bills/{id}` (replace on purpose), `DELETE` |
| Meter log | `POST /water/readings`, `GET /water/forecast/current` |
| Water insights (estimate, range, "Why?") | `GET /water/forecast` → `lines`, `cost.breakdown`, `assumptions`, `source_ids` |
| Chart: actual vs estimates | `GET /water/history` (actual bills, saved estimates, checks) |
| What-if / compare / save as goal | `GET /water/scenarios/catalogue`, `POST /water/scenarios`, `POST /water/actions`, `POST /water/actions/{id}/complete` |
| Recommendations, alerts, "unlock more" | `GET /water/insights` → `recommendations`, `alerts`, `unlock` |
| Year view, season context | `GET /water/seasons`, `GET /water/context` |
| Lead AI / RAG | `GET /water/summary` (numbers + evidence; the AI explains, never computes) |

## Data and sources
See `data/SOURCES.md` (CWA tariff, Statistics Mauritius tables, REU 2016, EPA, Singapore study, ERA5, Zenodo smart
meters) and `data_prep/` for how the seasonal files were made.

## Limits (say them in the pitch)
- Seasonal effect comes from a tropical study abroad and patterns from German homes; no public Mauritian household data exists.
- Action defaults are North-American averages (marked *estimated*); users can enter their own.
- Water block rule above 10 m³ not yet checked against a real bill above 10 m³.
- Reservoir/rain context is 2024–2025, not live.

## AI disclosure
Claude (Anthropic) helped research the data and draft this module; the team reviewed and tested it.
