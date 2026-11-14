# Electricity Module – LiveBetter

This folder contains the Electricity module for the LiveBetter project, developed as part of the MDX IET Life Powered by Tech hackathon.

## Overview
The Electricity module handles:
- CEB tariff calculations and confirmed bill validation
- Meter-reading history and current-cycle data
- Next-cycle electricity forecasting
- Forecast backtesting and forecast-versus-actual checks
- E1–E5 assessment support
- Energy-saving scenarios and appliance-based recommendations
- Action completion tracking and savings adjustments
- Household AI summary integration

## Key implementation status
The module is designed to be deterministic and explainable, without using ML models or random-forest forecasting.

Completed work includes:
- Domestic CEB tariff calculation with rising blocks, minimum charges, meter rental, and TV licence
- Polling/validation of confirmed bill inputs and period checks
- Forecasting for the next billing cycle based on measured consumption
- Preliminary forecast support after one confirmed bill
- Insufficient-data handling when evidence is too weak
- E5 expected usage adjustment (increase/decrease/none/not sure)
- Appliance-based scenario eligibility checks
- Water-heater, AC, washing-machine, and electric cooking logic tied to assessment data
- Recommendation generation and budget comparison
- JSON-backed module storage designed to be replaced later by Supabase
- Backend routes for profile, bills, readings, assessment, forecast, actions, activity, and summary
- Automated tests covering tariff calculation, forecast flow, scenarios, and E5 logic

## Important project rules followed
- Electricity works independently and does not import Water or Food
- The module exposes its own API router and summary endpoint
- Shared contract requirements from `MODULE_CONTRACT.md` are respected
- Forecast reliability and data completeness are kept as separate concepts
- “Not sure” and unanswered assessment values do not increase completeness
- Assessed appliance usage is treated as an assumption, not measured consumption
- Historical backtests remain separate from actual forecast checks

## Module structure
- `electricity/` – main implementation package
  - `tariff.py` – tariff and bill calculation logic
  - `forecast.py` – forecasting, reliability, and forecast checks
  - `history.py` – measured periods and daily history generation
  - `actions.py` – action eligibility and savings calculations
  - `advice.py` – recommendations, budget, and summary output
  - `api.py` – Electricity API routes
  - `app.py` – standalone FastAPI app
  - `store.py` – JSON storage layer
  - `auth.py` – shared auth handling
  - `tests/` – automated test coverage

## API highlights
The module includes endpoints such as:
- `GET /electricity/profile`
- `PUT /electricity/profile`
- `GET /electricity/assessment`
- `PUT /electricity/assessment`
- `GET /electricity/bills`
- `POST /electricity/bills`
- `DELETE /electricity/bills/{bill_id}`
- `GET /electricity/readings`
- `POST /electricity/readings`
- `DELETE /electricity/readings/{reading_id}`
- `GET /electricity/forecast`
- `POST /electricity/scenarios`
- `GET /electricity/actions`
- `POST /electricity/actions`
- `POST /electricity/actions/{id}/complete`
- `GET /electricity/forecast-checks`
- `GET /electricity/activity`
- `POST /electricity/activity`
- `GET /electricity/summary`

## Validation
The electricity tests can be run with:

```bash
cd backend electricity
python -m pytest electricity/tests -v
```

## Notes
This folder reflects the work completed for the Electricity module and follows the project’s shared module contract. It is intended to remain modular, explainable, and ready for future integration with a database or shared household app layer.
