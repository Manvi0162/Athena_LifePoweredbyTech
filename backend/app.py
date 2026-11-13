"""LiveBetter API: one backend for the whole app.

  /auth/*                         one login for every module (core/identity.py)
  /households/*, /bills, /utilities/forecast, /household/*, /activity, /demo/*   the app's routes (integration/)
  /water/*                        water engine (Sanjana)
  /electricity/*                  electricity engine (Alexandra)
  /pantry, /receipts/*, /recipes/*, /food/*, /household   food engine (Shruti)
  /household/dashboard, /household/insights, /household/coach   Big Brain (Manvi)

Every endpoint except /health and /auth/* needs `Authorization: Bearer <token>` from /auth/login.
With SUPABASE_URL + SUPABASE_PUBLISHABLE_KEY set, that is the Supabase access token and row-level
security applies. Without them the backend runs in local mode (one demo account, local file database).
"""

from dotenv import load_dotenv

load_dotenv()  # reads backend/.env (never committed) before settings are used

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from core.identity import IdentityMiddleware, mode  # noqa: E402
from core.identity import router as auth_router  # noqa: E402
from electricity.api import router as electricity_router  # noqa: E402
from food_recognition import food_router  # noqa: E402
from integration.gateway import router as app_router  # noqa: E402
from pantry.router import router as household_router  # noqa: E402
from receipts.router import router as receipts_router  # noqa: E402
from recipes.router import router as recipes_router  # noqa: E402
from water.api import router as water_router  # noqa: E402

app = FastAPI(title="LiveBetter API", version="1.0")

# Allows the Expo web preview to call the API. Auth is by bearer token, not cookies.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(IdentityMiddleware)

app.include_router(auth_router)
app.include_router(app_router)
app.include_router(household_router)
app.include_router(food_router)
app.include_router(receipts_router)
app.include_router(recipes_router)
app.include_router(water_router)
app.include_router(electricity_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/info")
def info():
    """Which mode the backend runs in: 'supabase' (team database) or 'local' (one demo account, no keys)."""
    return {"status": "ok", "mode": mode(), "modules": ["water", "electricity", "food", "big_brain"]}
