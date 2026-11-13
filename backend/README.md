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

- **local** (no Supabase keys in `.env`): real registration and login on this backend (passwords hashed with
  PBKDF2, signed session tokens) plus the demo account `demo@livebetter.mu` / `demo1234`; data in
  `backend/.localdata/` (git-ignored), illustrative recipes. Works with no network, for laptops, tests and the
  demo.
- **supabase** (`SUPABASE_URL` + `SUPABASE_PUBLISHABLE_KEY` set): real accounts (`POST /auth/signup`,
  `/auth/login`), the team database and the UniTools recipes. Run once in the Supabase SQL Editor, in order:
  `sql/01_livebetter_schema.sql`, `sql/02_lb_confirm_cooking_v2.sql`, **`sql/03_module_state.sql`**,
  **`sql/04_user_security.sql`** (both new; wait until the database work is finished). Also set
  `MFA_ENCRYPTION_KEY` (see `.env.example`).
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
| Login | `POST /auth/signup`, `POST /auth/login` (→ `mfa_required` if the authenticator is on), `POST /auth/mfa`, `POST /auth/refresh`, `GET /auth/me` | integration |
| Security | `GET /security/status`, `PUT /security/pattern`, `POST /security/pattern/verify`, `POST /security/authenticator/setup·confirm·disable` | surprise card |
| Account | `POST /account/reset`, `POST /account/restore`, `GET /account/reset-status` (pattern needed) | surprise card |
| App | `POST /households/onboarding`, `GET /households/me` | integration |
| App | `GET/POST /bills`, `DELETE /bills/{kind}/{id}`, `GET /utilities/forecast?category=` | → water / electricity |
| App | `POST /household/scenarios` (`{category, reduction_percent}` or `{category, scenario, params}`) | → water / electricity |
| Big Brain | `GET /household/dashboard` (report format), `GET /household/insights` (app format + v3 summary), `GET /big-brain/dashboard` (v3), `POST /household/coach` | Manvi |
| App | `GET /activity`, `POST /demo/sample` (only on an empty account), `POST /demo/reset` (= `/account/reset`) | integration |
| Water | `/water/*`: assessment W1–W5, bills, readings, forecast, current cycle, checks, scenarios, goals, seasons, summary | Sanjana |
| Electricity | `/electricity/*`: assessment E1–E5, bills, readings, forecast, forecast checks, scenarios, goals, summary | Alexandra |
| Food | `GET /pantry`, `POST /pantry`, `PATCH /pantry`, `POST /receipts/parse`, `POST /receipts/confirm`, `GET /recipes`, `GET /recipes/ranked`, `POST /recipes/search`, `POST /recipes/recommend`, `POST /recipes/drafts`, `POST /recipes/{id}/cook`, `POST /food/recognize`, `GET /household` | Shruti |

Errors: `{"detail": {"code", "message", "details"}}` (401 not logged in / wrong pattern or code, 403 pattern
required, 409 onboarding required / conflict, 410 nothing to restore, 422 invalid input, 423 locked, 428 no
pattern set yet, 503 AI unavailable). "Not enough data" is not an error: responses carry
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

## Security (surprise card "Misuse") — `core/accounts.py`, `core/security.py`, `integration/security_routes.py`
Protected actions: reset account, restore, delete/replace a bill (water and electricity routes too), change the
household, switch the authenticator off. The app draws the pattern → `POST /security/pattern/verify` → a
one-time, 5-minute permission for that action → sent as `X-Step-Up`. Pattern hashed (PBKDF2 + salt); authenticator
secret encrypted (Fernet) and shown only once at setup; codes accepted for ±30 s and only once; recovery codes
hashed; 5 wrong tries → 5-minute lock; every attempt goes to the user's security log and to `activity_logs`.
Libraries: `pyotp`, `segno` (QR), `cryptography`; no code or keys from other repositories.
Known limit (Supabase mode): row-level security lets a user edit their own `user_security` row through the API
directly; that needs the owner's login, so it does not help the phone misuser. Production: service-role writes only.

## Big Brain v3 (Manvi's latest notebook) — `big_brain/v3.py`
The notebook `athenav3_ai_integrated_with_modules.py` had duplicated cells (Colab + Codex reruns). One copy of each
function is kept: `normalize_module_summary`, `extract_savings_actions`, `rank_module_savings`,
`normalize_savings_period` (savings per 30 days), `rank_normalized_actions`, `generate_big_brain_reasoning`,
`build_big_brain_v3_response`, `big_brain_v3`. It runs on the household's own water/electricity data (not the
notebook's sample files), Gemini output passes the same number check, and a template is used without a key.

## What changed in each person's code at integration (small, marked in the code)
| Module | Change |
|---|---|
| Food (Shruti) | `app.py` is now the whole backend (her routers unchanged). `core/auth.py` reuses the shared login. Added `POST/PATCH /pantry`, `GET /recipes/ranked`, `recipes/recommendations.py`. Her SQL functions are untouched. |
| Water (Sanjana) | `store.py` saves per household (`module_state`) and copies the shared household size; `api.py` also writes bills/readings/goals to the shared tables; `auth.py` accepts the shared login. |
| Electricity (Alexandra) | Same three changes as water; new accounts start empty (`data/empty_electricity.json`); the demo file with the team's real CEB bills is used only for the sample household. Folder moved from `backend electricity/electricity` to `backend/electricity`. |
| Big Brain (Manvi) | v2 and v3 notebook functions moved into `big_brain/` with the same names (duplicates removed); database client passed in instead of Colab globals; Gemini called through the backend's `core/llm.py`; originals kept in `research/big_brain/`. |
| App (Kentish) | His new screens kept. `src/api.ts`, `src/context.tsx`, `src/types.ts` call the backend in live mode. Login and Register now work; new `app/security.tsx` and `src/pattern.tsx` (pattern grid); pattern prompt added to onboarding edit, bill delete, reset/restore in Settings; Home shows the security alert and Big Brain priorities; Coach uses the backend coach in live mode. Demo (mock) mode unchanged. |
| Water / Electricity | Bill delete/replace and demo reset ask for the pattern (`guard(...)`, no effect when the module runs alone). |

## Tests
```
python -m pytest -q tests water/tests electricity/tests
```
115 tests: food (Shruti, 42 + 1 needing local PostgreSQL), water (36), electricity (18), end-to-end (13),
security / misuse (6).

## Credits and AI disclosure
Food API: Shruti · Water engine: Sanjana · Electricity engine: Alexandra · Big Brain: Manvi · App: Kentish.
AI tools: Claude (Anthropic) helped write the modules, the integration layer and the tests; Gemini (Google)
and Groq are used *by the app* for receipts, food photos, recipe drafts and Big Brain wording. The team
reviewed and tested the code.
