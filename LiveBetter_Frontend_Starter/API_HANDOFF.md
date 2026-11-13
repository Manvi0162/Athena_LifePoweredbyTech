# Frontend ↔ Backend Handoff (PROPOSED CONTRACT)

**IMPORTANT:** The team blueprint specifies routes and responsibilities but not exact JSON schemas. The examples below are suggested shapes used by the frontend starter. Member 1 and Member 2 should agree and freeze them immediately. If the backend differs, update `src/api.ts`, `src/context.tsx` and `src/types.ts` together. All currency is `MUR`; absolute date fields are `YYYY-MM-DD`.

## Mode handling
- Demo: `EXPO_PUBLIC_USE_MOCKS=true` (default when unset): only local data and deterministic examples. No backend requests.
- Live: `EXPO_PUBLIC_USE_MOCKS=false`, `EXPO_PUBLIC_API_URL=https://host`: real HTTPS requests. No silent fallback to demo data.
- **Missing:** production authentication. Confirm Supabase JWT generation/refresh with M2. Do not treat client supplied household IDs as proof of authorization.

## 1. POST /households/onboarding (Member 2)
Request (field names from `Household` minus `id`):
```json
{
  "name":"Demo household","members":4,"home_type":"House",
  "water_tariff":"Domestic","electricity_tariff":"Domestic",
  "monthly_target":15000,"diet":"No preference","allergies":"",
  "water_habit":"","appliance_notes":""
}
```
**Needed for robust Live mode:** reply `{ "id": "household-uuid" }` or `{ "household": { "id": "household-uuid", ... } }` and provide a `GET /households/me` profile endpoint. The starter currently caches onboarding data locally for convenience; backend reads and a session are still required.

## 2. POST /bills and GET /utilities/forecast (Members 2+3)
Bill request:
```json
{
  "household_id":"demo-household-001","kind":"water",
  "period_start":"2026-10-01","period_end":"2026-10-31",
  "units":13,"amount":350,"tariff":"Domestic","currency":"MUR"
}
```
Forecast query: `GET /utilities/forecast?household_id=...&category=water`. Same for `electricity`.
Response:
```json
{
  "category":"water","period_start":"2026-12-01","period_end":"2026-12-31",
  "units":13,"unit":"m³","value":350,"currency":"MUR",
  "method":"historical_baseline (example ONLY)","confidence":"limited_history",
  "assumptions":["Not a current live-meter forecast"],"source_data":["bill-001"]
}
```
**Do not claim the sample Rs 350 as CWA-verified**. Member 3 should return tariff-calculated output (correct class, slabs and fees) plus method and limitations. If no readings, forecast a next-cycle baseline, not a current-cycle measured forecast.

## 3. POST /receipts/parse (Member 4)
Multipart/form-data keys: `file` as image JPEG and `household_id` as string.
Response (proposed):
```json
{"receipt_id":"r001","status":"needs_review","items":[
  {"name":"rice","quantity":1,"unit":"kg","price":95},
  {"name":"onion","quantity":2,"unit":"piece","price":30}
]}
```
Never write these raw proposals directly to the database as confirmed purchases.

## 4. POST /receipts/confirm and GET /pantry (Members 2+4)
Confirm request:
```json
{"household_id":"demo-household-001","receipt_id":"r001","items":[
  {"name":"rice","quantity":1,"unit":"kg","price":95}
]}
```
GET `/pantry?household_id=...` response as array or `{ "items": [ ... ] }`:
```json
[{"id":"p001","name":"rice","quantity":1,"unit":"kg","available":true,"expiry":"2026-11-25"}]
```
Confirm creates expense and stock ONCE. Backend should deduplicate receipt confirmation. Pantry `POST /pantry` / `PATCH /pantry` are proposed extra routes NOT listed in the blueprint. Confirm their final paths with M2/M4, and ensure any `PATCH` includes a unique target item identifier.

## 5. POST /recipes/recommend and POST /recipes/{id}/cook (Member 4)
Recommendation request: `{ "household_id":"demo-household-001" }`.
Response as array or `{ "recipes":[...] }`:
```json
[{"id":"recipe-42","name":"Vegetable Fried Rice",
  "ingredients":[{"name":"rice","quantity":0.2,"unit":"kg"}],
  "missing":[],"coverage":1,"instructions":"Cook ...",
  "source":"UniTools — theunitools.com (CC BY-SA 4.0)"}]
```
**Source string is an example of an expected credit, not evidence of actual dataset integration.**
Cooking request: `{ "household_id":"...", "idempotency_key":"unique-click-action-id" }`.
The server must atomically deduct ingredients once for that action ID, reject insufficient stock, and NOT create a second grocery expense.

## 6. GET /household/insights and POST /household/scenarios (Member 5 + Member 3)
Insights query: `GET /household/insights?household_id=...`.
Response:
```json
{
  "period_start":"2026-12-01","period_end":"2026-12-31","currency":"MUR",
  "water":350,"electricity":2100,"groceries_recorded":238,
  "total":null,
  "assumptions":["Grocery purchases cover a different period; do not sum them into the projected monthly total"],
  "recommendations":["Use existing ingredients before shopping"],
  "method":"period-aware structured aggregation","source_data":["bill-001","bill-002","receipt-001"]
}
```
Scenario request: `{ "household_id":"...", "category":"electricity", "reduction_percent":10 }`.
Response:
```json
{
  "baseline":2100,"adjusted":1980,"delta":120,"unit_change":18,
  "message":"Scenario amounts require the verified tariff engine; these values are illustrative only",
  "assumptions":["Example assumptions, not actual validated CEB slabs"]
}
```
No monetary amount should be claimed to be a tariff-verified saving unless the backend has calculated it with the right CEB/CWA tariff and period.

## 7. Error contract
Proposed non-2xx JSON:
```json
{"code":"INSUFFICIENT_STOCK","message":"Rice quantity insufficient","details":{}}
```
The current `src/api.ts` reads `message` or string `detail` and has a 12–15 second timeout. Align HTTP status and fields with Member 2. A failed live API must remain a visible error, not be replaced by mock output.

## 8. Tests required before demo
1. Submit onboarding; confirm real server-issued household ID can be loaded after app restart.
2. POST two bills; GET both forecast results; verify dates, cost tariff classes, currency.
3. Parse receipt image; edit item; confirm; refresh pantry; rerun same confirmation and ensure no double count.
4. Cook a recipe once with unique idempotency key; retry same request and ensure only one stock deduction.
5. Mark item unavailable; verify dataset-based recipe list changes.
6. Rerun insights after a pantry/purchase change; verify evidence and period alignment.
7. Kill and reopen standalone APK; verify saved state is authoritative from backend in Live mode.
