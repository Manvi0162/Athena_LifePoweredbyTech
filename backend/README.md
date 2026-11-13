# LiveBetter API (FastAPI)

The backend the mobile app calls. It wraps the flows proven in the Colab notebook
(`AthenaV1_HybridRecipes`) and her Supabase SQL functions.

## Run it

```
python -m venv .venv
.venv\Scripts\activate          # Mac: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # Mac: cp .env.example .env   -> then fill in the keys
uvicorn app:app --reload
```

Open http://127.0.0.1:8000/docs to try every endpoint.

Database: run `sql/01_livebetter_schema.sql` (already done by the team) and
`sql/02_lb_confirm_cooking_v2.sql` once in the Supabase SQL Editor.

## Login

Every endpoint except `/health` needs `Authorization: Bearer <access token>`.
The app gets the token from Supabase Auth (`supabase.auth.signInWithPassword`).
The API passes it to Supabase, so row-level security and the SQL functions
decide what each user can see and change. Only the publishable key is used.

## Endpoints

| Method | Path | What it does | Saves anything? |
|---|---|---|---|
| GET | `/health` | Server is up | No |
| GET | `/household` | The user's household | No |
| GET | `/pantry` | Pantry items | No |
| POST | `/food/recognize` | Photo (`image` field) → food names, fresh/packaged, confidence | No |
| POST | `/recipes/search` | `{"ingredients": ["carrots"]}` → recipes using them, what's in the pantry, what to buy | No |
| GET | `/recipes` | All recipes the user can see | No |
| POST | `/recipes/recommend` | Verified recipe cookable now, otherwise an AI draft | No |
| POST | `/recipes/drafts` | `{"recipe": {...}}` → save AI draft as private, pending | Yes |
| POST | `/recipes/{id}/cook` | `{"operation_id": "<uuid>"}` → deduct ingredients once | Yes |
| POST | `/receipts/parse` | Receipt photo (`image` field) → food items to review; non-food lines (toiletries, batteries...) listed in `excluded_non_food`; `total` is the food total | No |
| POST | `/receipts/confirm` | Reviewed receipt → saved, pantry updated once. Any line with `"category": "non_food"` is dropped | Yes |

Flows:
- **Photo → recipes:** `/food/recognize` → user confirms names → `/recipes/search`
- **Receipt:** `/receipts/parse` → user reviews → `/receipts/confirm` (send back the `source_identifier`)
- **Cook:** app creates one UUID per "I cooked this" tap → `/recipes/{id}/cook`. Retrying with the same UUID never deducts twice.

Errors use `{"detail": {"code": ..., "message": ...}}`. Not enough stock → 409 with
the ingredient and amounts; AI unavailable → 503 (show manual entry).

## Tests

```
python -m pytest -q tests
```

41 tests. Two run the API against the real SQL functions in a local PostgreSQL
(skipped if none is running).

## AI tools used (hackathon rule 3)

- **Claude (Anthropic)**: helped write this API, the food-photo cells, `lb_confirm_cooking` v2 and the tests.
- **Gemini API (Google AI Studio)** and **Groq** (`qwen/qwen3.8-27b`): used *by the app* to read food photos and receipts and to draft recipes.
- Add any other AI tools the team used.
