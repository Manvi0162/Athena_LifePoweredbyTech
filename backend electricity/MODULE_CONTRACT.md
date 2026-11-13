# LiveBetter: Module Contract
**Water · Electricity · Food · Household AI**

## 1. Core Architecture

Each module works independently. A household can enable only Water, only Electricity, only Food, or any combination.

- Water, Electricity and Food must never call one another.
- Each module owns its data, calculations, forecasts, recommendations and API routes.
- Household AI is the only component that reads multiple modules.
- Household AI obtains information through each enabled module's `/summary` endpoint.
- A missing or disabled module must not prevent other modules from working.

## 2. Folder Structure

```text
backend/
├── water/                 # Sanjana
│   ├── data/
│   ├── tests/
│   ├── __init__.py
│   ├── app.py
│   ├── api.py
│   ├── auth.py
│   └── README.md
│
├── electricity/           # Electricity module owner
│   ├── data/
│   ├── tests/
│   ├── __init__.py
│   ├── app.py
│   ├── api.py
│   ├── auth.py
│   └── README.md
│
├── food/                  # Food team
│   ├── data/
│   ├── tests/
│   ├── __init__.py
│   ├── app.py
│   ├── api.py
│   ├── auth.py
│   └── README.md
│
├── household_ai/          # Household AI owner
│
├── main.py                # Combined application
├── requirements.txt
└── MODULE_CONTRACT.md
```

Each module must:
- Have its own `data/` and `tests/` folders.
- Provide an `app.py` that runs independently.
- Provide an `api.py` containing an `APIRouter`.
- Use the shared login and error conventions.
- Expose a `/summary` endpoint.

The combined `backend/main.py` includes the routers from all modules.

## 3. Shared Login

All modules use the same household account and authentication method.

**Endpoint**

`POST /auth/login`

Request:

```json
{
  "email": "user@example.com",
  "password": "password"
}
```

Response:

```json
{
  "token": "..."
}
```

Token generation:

`HMAC-SHA256(LIVEBETTER_SECRET, email)`

Rules:
- All modules use the same `LIVEBETTER_SECRET`.
- A token obtained from one module must work in every other module.
- Protected endpoints require:

`Authorization: Bearer <token>`

- Follow the implementation in `water/auth.py` as the shared reference.

## 4. Shared Error Format

All modules return errors using:

```json
{
  "detail": {
    "code": "validation_error",
    "message": "A sentence the user can act on",
    "details": {}
  }
}
```

HTTP status conventions:

| Status | Meaning |
|---|---|
| 401 | Not signed in |
| 404 | Resource not found |
| 409 | Conflict or duplicate |
| 422 | Invalid input |

Errors must be understandable and actionable.

## 5. Standard Module Summary

Every module exposes:

`GET /<module>/summary`

The response must follow this common structure:

```json
{
  "module": "electricity",
  "status": "ok",
  "currency": "MUR",
  "period_start": "2026-11-12",
  "period_end": "2026-12-12",
  "forecast": {
    "amount": 140.3,
    "unit": "kWh",
    "low": 130.0,
    "high": 150.0,
    "cost_rs": 998.0,
    "cost_low_rs": 900.0,
    "cost_high_rs": 1100.0,
    "confidence": "low",
    "method": "Plain-language explanation of the calculation"
  },
  "benchmark": {},
  "budget": {
    "budget_rs": 1200,
    "projected_rs": 998.0,
    "high_rs": 1100.0,
    "status": "ok"
  },
  "context": null,
  "recommendations": [],
  "recent_activity": []
}
```

### Shared fields

- `module`: `water`, `electricity` or `food`.
- `status`: `ok` or `no_data`.
- `currency`: `MUR`.
- `period_start` and `period_end`: forecast period.
- `forecast`: module-specific forecast.
- `benchmark`: module-specific benchmark with a source.
- `budget`: budget information, or `null` if unavailable.
- `context`: one explanatory sentence or `null`.
- `recommendations`: suggested actions and alerts.
- `recent_activity`: recent module events.

### Forecast fields

- `amount`: projected quantity.
- `unit`: `m3`, `kWh`, or the Food module's own unit.
- `low` and `high`: forecast range.
- `cost_rs`: projected cost in Mauritian rupees.
- `cost_low_rs` and `cost_high_rs`: cost range.
- `confidence`: `low`, `medium` or `good`.
- `method`: plain-language explanation.

Every module must explain its forecast period, data sources, assumptions and calculation method.

If there is insufficient data, return `status: "no_data"` with a clear `message`. Do not invent a forecast.

## 6. Electricity-Specific Requirements

The Electricity module follows its own detailed implementation plan while respecting the shared summary contract.

### 6.1 Input data

The module receives:
- Confirmed CEB bill information extracted by the team's LLM bill-extraction process.
- User-confirmed bill values.
- Optional meter readings.
- Optional electricity assessment answers.
- Shared household profile information.

The Electricity module does not implement duplicate bill OCR or extraction.

### 6.2 Forecasting

The Electricity module must:
- Forecast the next billing cycle by default.
- Use confirmed bill consumption and valid meter readings as measured evidence.
- Use observed daily consumption as its baseline.
- Calculate projected kWh using the baseline and the forecast period.
- Use CEB rising-block tariffs to calculate projected costs.
- Clearly distinguish measured consumption, estimated daily history and forecast adjustments.
- Never present synthetic daily values as real meter readings.

Electricity-specific forecast statuses:

| Status | Condition |
|---|---|
| `insufficient_data` | No confirmed bill and fewer than two meter readings |
| `preliminary` | One confirmed bill |
| `better_supported` | At least three comparable bills and two checked forecasts |

These detailed statuses must be exposed as an additional electricity-specific field, such as `forecast.forecast_status`.

For shared compatibility:
- The top-level summary `status` remains `no_data` or `ok`.
- The shared `forecast.confidence` remains `low`, `medium` or `good`.
- Confidence must be based on measured evidence, not the number of assessment answers.

### 6.3 Tariff calculation

- Use the CEB domestic tariff data.
- Apply rising-block rates, minimum charges and applicable additional charges.
- Recalculate the full tariff for projected usage and savings scenarios.
- Do not estimate savings by multiplying kWh by an average electricity price.
- Compare calculated charges with confirmed bill amounts and flag significant differences.

### 6.4 Assessment and scenarios

The optional electricity assessment covers:
- Regularly used appliances.
- Air-conditioning usage.
- Water-heating method.
- Main cooking energy.
- Expected changes in appliance usage.

Assessment answers are assumptions, not measured consumption.

Scenarios must check that the required assessment information is available. If information is missing, return `needs_input` with an actionable message instead of guessing.

### 6.5 Actions and learning

- Completed actions may affect future forecast adjustments.
- Actions must not modify historical bills or meter readings.
- Completing an action twice must not apply its savings twice.
- Forecasts must be saved as immutable snapshots.
- When a confirmed bill covers a forecasted period, record a forecast-versus-actual check.
- Forecast reliability can improve using measured forecast errors.

## 7. Recommendations and Evidence

Every recommendation follows this structure:

```json
{
  "id": "shorter_ac_hours",
  "kind": "action",
  "title": "Reduce air-conditioning usage",
  "detail": "Estimated electricity saving from using the AC less.",
  "saving": {
    "cost_rs": 100,
    "per": "month",
    "kwh": 15
  },
  "status": "suggested",
  "evidence": {
    "period_start": "2026-11-12",
    "period_end": "2026-12-12",
    "method": "Appliance power multiplied by hours reduced and days",
    "assumptions": [
      "Appliance power is estimated until confirmed by the user."
    ]
  }
}
```

Rules:
- `kind` must be `action` or `alert`.
- Action status must be `suggested`, `selected` or `completed`.
- Alert status is `null`.
- Every recommendation must contain evidence.
- No saving figure may be shown without its calculation method and assumptions.
- Synthetic or placeholder data must be disclosed.

## 8. Household AI Responsibilities

Household AI:
1. Reads `/water/summary`, `/electricity/summary` and `/food/summary` for enabled modules.
2. Skips disabled or unavailable modules.
3. Clearly tells the user when a module is not set up.
4. Calculates combined monthly spending from module costs.
5. Displays each module's forecast period because periods may differ.
6. Ranks actions across modules using `saving.cost_rs`.
7. Can suggest cross-module ideas using evidence from the relevant modules.

Household AI must not silently modify module calculations or invent savings.

## 9. Independence and Integration Rules

- Each module can run and be tested independently.
- Each module owns its storage and calculations.
- Modules communicate with Household AI through their summary endpoints.
- Do not import another module's internal calculation functions.
- Keep module-specific tests inside the corresponding `tests/` folder.
- The combined application must not break independent module execution.

## 10. Development Principle

Implement the shared contract first, then complete each module's own requirements.

Changes to one module must not require changes to another module's internal implementation, provided the shared API contract remains satisfied.
