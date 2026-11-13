# LiveBetter API: one backend for the whole app

Team Athena · IET MDX "Life Powered by Tech" · 13–14 Nov 2026

One FastAPI app serves the Expo app (`livebetter/`). Every module keeps its own calculations; they share
**one login, one household and one database**, and **Big Brain** combines them.

```
 Expo app (livebetter/)  ── Authorization: Bearer <token> ──►  backend/app.py
                                                               │ core/identity.py: who is calling, which household
   ┌───────────────┬──────────────────┬─────────────────────┬──┴──────────────────────────┐
   │ water/        │ electricity/     │ food: pantry/        │ big_brain/                  │
   │ (Sanjana)     │ (Alexandra)      │ receipts/ recipes/   │ (Manvi)                     │
   │ CWA tariff,   │ CEB tariff,      │ food_recognition/    │ collect → verify → combine  │
   │ forecast,     │ forecast,        │ (Shruti)             │ → rank → explain (Gemini)   │
   │ what-ifs      │ appliance what-if│ receipts, pantry,    │ dashboard + AI coach        │
   │               │                  │ recipes, cooking     │                             │
   └──────┬────────┴────────┬─────────┴──────────┬───────────┴───────────────┬─────────────┘
          │  integration/gateway.py: the routes the app calls (onboarding, bills, forecast, insights…)
          ▼
   Supabase (team database, row-level security)  ── or ──  core/localdb.py (no keys: local demo)
   households · utility_bills · meter_readings · grocery_receipts · receipt_items · pantry_items ·
   pantry_events · household_actions · activity_logs · cooking_operations · lb_recipes · module_state
```

## How the modules affect each other
| Change | What happens elsewhere |
|---|---|
| Onboarding (household size, goal, monthly target) | Water and electricity use the same household size; Big Brain ranks by the household's main goal and compares spending with the monthly target |
| Water or electricity bill confirmed | Saved in the module (tariff check, forecast snapshot, bill vs prediction) **and** in `utility_bills`; Big Brain and the Home screen update |
| Grocery receipt confirmed | Pantry stock added once, grocery spending recorded (`confirm_grocery_receipt`); food recommendations and recipes change |
| Recipe cooked | Stock deducted once per tap (`lb_confirm_cooking`), never a second expense |
| Water question W1 (shower time) + electricity question E3 = electric heater | Big Brain adds the cross-module action "shorter showers: less water **and** less water-heater electricity" |
| Goal completed (water/electricity) | Lowers the next forecast; written to `household_actions` |
| Anything above | One activity log (`activity_logs`) shown in the app's Activity screen |

## Run it
```
cd backend
python -m venv .venv
.venv\Scripts\activate          # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # Mac/Linux: cp .env.example .env
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```
Open http://127.0.0.1:8000/docs. `GET /info` says which mode is running:

- **local** (no Supabase keys in `.env`): one demo account `demo@livebetter.mu` / `demo1234`, data in
  `backend/.localdata/` (git-ignored), illustrative recipes. Works with no network, for laptops, tests and a
  fallback demo.
- **supabase** (`SUPABASE_URL` + `SUPABASE_PUBLISHABLE_KEY` set): real accounts (`POST /auth/signup`,
  `/auth/login`), the team database and the UniTools recipes. Run once in the Supabase SQL Editor, in order:
  `sql/01_livebetter_schema.sql`, `sql/02_lb_confirm_cooking_v2.sql`, **`sql/03_module_state.sql`** (new).
- `GEMINI_API_KEY` (optional): receipt reading, food photos, AI recipe drafts, and Big Brain wording. Without
  it Big Brain uses template explanations with the same numbers.

Only the publishable key is used; the user's own token is attached to every query, so row-level security
and the SQL functions decide what each user can see. Secrets stay in `backend/.env`, never in the app.

## Connect the app
In `livebetter/.env.local`:
```
EXPO_PUBLIC_USE_MOCKS=false
EXPO_PUBLIC_API_URL=http://<your-laptop-IP>:8000     # same Wi-Fi as the phone; or an https tunnel/host
```
Then `npx expo start --clear`, sign in (local mode: demo@livebetter.mu / demo1234), complete onboarding.
Settings → **Load sample household** fills a clearly labelled sample for rehearsing the demo.

## Endpoints
| Area | Method + path | Owner |
|---|---|---|
| Login | `POST /auth/login`, `POST /auth/signup`, `POST /auth/refresh`, `GET /auth/me` | integration |
| App | `POST /households/onboarding`, `GET /households/me` | integration |
| App | `GET/POST /bills`, `DELETE /bills/{kind}/{id}`, `GET /utilities/forecast?category=` | → water / electricity |
| App | `POST /household/scenarios` (`{category, reduction_percent}` or `{category, scenario, params}`) | → water / electricity |
| Big Brain | `GET /household/dashboard` (report format), `GET /household/insights` (app format), `POST /household/coach` | Manvi |
| App | `GET /activity`, `POST /demo/sample`, `POST /demo/reset` | integration |
| Water | `/water/*`: assessment W1–W5, bills, readings, forecast, current cycle, checks, scenarios, goals, seasons, summary | Sanjana |
| Electricity | `/electricity/*`: assessment E1–E5, bills, readings, forecast, forecast checks, scenarios, goals, summary | Alexandra |
| Food | `GET /pantry`, `POST /pantry`, `PATCH /pantry`, `POST /receipts/parse`, `POST /receipts/confirm`, `GET /recipes`, `GET /recipes/ranked`, `POST /recipes/search`, `POST /recipes/recommend`, `POST /recipes/drafts`, `POST /recipes/{id}/cook`, `POST /food/recognize`, `GET /household` | Shruti |

Errors: `{"detail": {"code", "message", "details"}}` (401 not logged in, 409 onboarding required / conflict,
422 invalid input, 503 AI unavailable). "Not enough data" is not an error: responses carry
`status: insufficient_data | needs_input | needs_readings` and the message to show.

## Big Brain (from `research/big_brain/athenav2_(with_ai_layer).py`)
Same functions and JSON as the *LiveBetter Big Brain AI Integration Guide*:
`collect_household_data`, `verify_household_data`, `build_decision_context`, `generate_action_candidates`,
`rank_actions`, `explain_ranked_actions`, `validate_domain_recommendation`, `collect_domain_recommendations`,
`combine_big_brain_actions`, `build_integrated_dashboard` (`big_brain/core.py`, `big_brain/explain.py`).
The guide's "still to implement" items are done:
1. **Real module outputs connected**: `big_brain/adapters.py` turns `/water/summary`, `/electricity/summary`
   and the food module's recommendations (`recipes/recommendations.py`) into the section-3 format.
2. **Unified ranking**: every recommendation gets Manvi's score (0.40 impact + 0.35 urgency + 0.25 confidence),
   plus a visible bonus for the household's main goal; one ranked list.
3. **Backend endpoint**: `GET /household/dashboard` and `/household/insights`.
4. **End-to-end tests**: `tests/test_integration.py`.

Rules kept: modules calculate, Big Brain combines; Python ranks, Gemini only explains; missing information
stays unknown; `estimated_savings_mur` always comes from a module calculation. Added safeguard: an
explanation with a number that is not in the action's data is replaced by the template explanation.

## What changed in each person's code at integration (small, marked in the code)
| Module | Change |
|---|---|
| Food (Shruti) | `app.py` is now the whole backend (her routers unchanged). `core/auth.py` reuses the shared login. Added `POST/PATCH /pantry`, `GET /recipes/ranked`, `recipes/recommendations.py`. Her SQL functions are untouched. |
| Water (Sanjana) | `store.py` saves per household (`module_state`) and copies the shared household size; `api.py` also writes bills/readings/goals to the shared tables; `auth.py` accepts the shared login. |
| Electricity (Alexandra) | Same three changes as water; new accounts start empty (`data/empty_electricity.json`); the demo file with the team's real CEB bills is used only for the sample household. Folder moved from `backend electricity/electricity` to `backend/electricity`. |
| Big Brain (Manvi) | Notebook functions moved into `big_brain/` with the same names; database client passed in instead of Colab globals; Gemini called through the backend's `core/llm.py`; originals kept in `research/big_brain/`. |
| App (Kentish) | `src/api.ts`, `src/context.tsx`, `src/types.ts` call the backend in live mode (login token, real routes, field mapping); login, coach, Home priorities, utility details and settings use it. Demo (mock) mode unchanged. |

## Tests
```
python -m pytest -q tests water/tests electricity/tests
```
108 tests: food (Shruti, 42 + 1 needing local PostgreSQL), water (36), electricity (18), end-to-end (12).

## Credits and AI disclosure
Food API: Shruti · Water engine: Sanjana · Electricity engine: Alexandra · Big Brain: Manvi · App: Kentish.
AI tools: Claude (Anthropic) helped write the modules, the integration layer and the tests; Gemini (Google)
and Groq are used *by the app* for receipts, food photos, recipe drafts and Big Brain wording. The team
reviewed and tested the code.
