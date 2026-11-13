# LiveBetter: electricity module (standalone): starter from the water team

Built the same way as the water module so both follow `backend/MODULE_CONTRACT.md`. Use it, change it, or replace it:
just keep the routes under `/electricity` and the `GET /electricity/summary` shape.

## Run
```bash
cd backend
pip install -r requirements.txt
python -m pytest -q electricity/tests             # 6 tests, incl. our real CEB bill (Rs 828 / Rs 998)
uvicorn electricity.app:app --reload --port 8002  # docs: http://localhost:8002/docs
```

## What is already there
- `tariff.py`: CEB 2026 rising blocks, minimum charge for tariff 110/120/140, meter rental, TV licence, VAT 0.
- `history.py`: real bills / meter readings split into synthetic days (weekend ×1.10) that add up exactly to each bill.
- `forecast.py`: current-cycle kWh and Rs (low/mid/high), bill lines, next price block, confidence.
- `actions.py`: blueprint formula kWh/day = kW × hours less per day; standby at the plug.
- `advice.py`: what-if (full tariff recalculated), you vs Mauritius (201.5 kWh/month), budget, alerts, `summary()`.
- `api.py`: `/electricity/profile, /bills, /readings, /history, /forecast, /actions/catalogue, /scenarios,
  /actions, /actions/{id}/complete, /insights, /summary, /activity, /demo/reset`.

## Ideas to extend (blueprint)
- Appliance list in onboarding (which appliances, hours per day) → personalised actions.
- Meter-reading reminders; time-of-use is not on the domestic tariff, so no need.
