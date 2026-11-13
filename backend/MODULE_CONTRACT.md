# LiveBetter: module contract (water · electricity · food · Household AI)

Each module works **alone**: the user can turn on only water, only food, etc. Modules do not call each other.
The **Household AI** is the only part that sees several modules: it reads each enabled module's `/summary`.

## 1. Folders (no merge conflicts)
```
backend/
  water/          Sanjana       → routes under /water
  electricity/    (friend)      → routes under /electricity
  food/           (team)        → routes under /food
  household_ai/   (AI owner)    → reads the three summaries
  requirements.txt  .gitignore  MODULE_CONTRACT.md
```
Each module folder holds its own `data/`, `tests/`, `README.md`, `app.py` (runs alone) and `api.py` (an APIRouter).
A final `backend/main.py` can include all routers in one app.

## 2. Login (same in every module)
- One household account. `POST /auth/login {email, password}` → `{token}`.
- Token = HMAC-SHA256(`LIVEBETTER_SECRET`, email). Same secret everywhere → one sign-in works for all modules.
- Header: `Authorization: Bearer <token>`. Copy `water/auth.py`.

## 3. Errors (same everywhere)
`{"detail": {"code": "validation_error", "message": "A sentence the user can act on", "details": {}}}`
401 not signed in · 404 not found · 409 conflict/duplicate · 422 invalid input.

## 4. The summary every module returns: `GET /<module>/summary`
```json
{
  "module": "water",                       // "water" | "electricity" | "food"
  "status": "preliminary",                 // insufficient_data | preliminary | better_supported
  "status_message": "This is an early estimate based on one billing period. Your future usage may differ.",
  "data_completeness": { "pct": 64, "missing": [ { "item": "W1_shower_minutes", "prompt": "Answer: ..." } ] },
  "reliability": { "checked_forecasts": 1, "backtests": 2, "mean_abs_error_pct": 3.6 },
  "forecast_vs_actual": [ { "kind": "real|backtest", "predicted_m3": 22.7, "actual_m3": 24.0, "error_pct": -5.3 } ],
  "unlock": [ { "scenario": "shorter_showers", "missing": [ { "item": "W1_shower_minutes", "prompt": "..." } ] } ],
  "currency": "MUR",
  "period_start": "2026-11-12", "period_end": "2026-12-12",
  "forecast": {
    "amount": 24.0, "unit": "m3",          // m3 | kWh | the food module's own unit (e.g. "meals")
    "low": 23.45, "high": 24.54,
    "cost_rs": 232.0, "cost_low_rs": 222.65, "cost_high_rs": 241.18,
    "confidence": "low",                   // low | medium | good
    "method": "plain-language method"
  },
  "benchmark": { "...": "module-specific, with a source" },
  "budget": { "budget_rs": 250, "projected_rs": 232.0, "high_rs": 241.18, "status": "ok" },   // ok | at_risk | over, or null
  "context": "one sentence or null",
  "recommendations": [
    {
      "id": "shorter_showers", "kind": "action",          // action | alert
      "title": "Shorter showers",
      "detail": "Saves about 1,896 L and Rs 32 a month.",
      "saving": { "cost_rs": 32, "per": "month", "...": "module units, e.g. litres / kWh / kg" },
      "status": "suggested",                             // suggested | selected | completed (null for alerts)
      "evidence": { "period_start": "...", "period_end": "...", "method": "...", "assumptions": ["..."], "...": "..." }
    }
  ],
  "recent_activity": [ { "at": "2026-11-13T10:00:00+00:00", "module": "water", "event": "action_completed" } ]
}
```
Rules
- No measured usage → `status: "insufficient_data"`, `forecast: null` (never a made-up number).
- Completeness (what the user told us) and reliability (how past estimates matched real bills) are separate.
- `cost_rs` is always Mauritian rupees for the module's current period, so the AI can add modules up.
- Every recommendation has `evidence` (period, data, method, assumptions). No number without a reason.
- Synthetic or placeholder data must be said in `forecast.method` / `evidence.assumptions`.

## 5. What the Household AI does with it
- Calls `/water/summary`, `/electricity/summary`, `/food/summary` for the modules the user turned on; a missing
  module is skipped and said ("Electricity is not set up").
- Total monthly spend = sum of `forecast.cost_rs` (periods may differ: show each period).
- Ranks all `kind: action` recommendations together by `saving.cost_rs`.
- Cross-module ideas only it can make (e.g. a shorter cooking time saves electricity; washing up uses water),
  always quoting the module evidence it used.
