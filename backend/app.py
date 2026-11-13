"""LiveBetter API.

Every endpoint except /health needs `Authorization: Bearer <Supabase access token>`
from the app's login. The token is passed to Supabase, so row-level security
and the SQL functions decide what each user can see and change.
"""

from dotenv import load_dotenv

load_dotenv()  # reads backend/.env (never committed) before settings are used

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from food_recognition import food_router  # noqa: E402
from pantry.router import router as household_router  # noqa: E402
from receipts.router import router as receipts_router  # noqa: E402
from recipes.router import router as recipes_router  # noqa: E402

app = FastAPI(title="LiveBetter API")

# Allows the Expo web preview to call the API. Auth is by bearer token, not cookies.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

app.include_router(household_router)
app.include_router(food_router)
app.include_router(receipts_router)
app.include_router(recipes_router)


@app.get("/health")
def health():
    return {"status": "ok"}
