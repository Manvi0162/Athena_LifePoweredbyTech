"""LiveBetter API: one backend for the whole app.

  /auth/*                         one login for every module (core/identity.py)
  /households/*, /bills, /utilities/forecast, /household/*, /activity, /demo/*   the app's routes (integration/)
  /water/*                        water engine (Sanjana)
  /electricity/*                  electricity engine (Alexandra)
  /pantry, /receipts/*, /recipes/*, /food/*, /household   food engine (Shruti)
  /household/dashboard, /household/insights, /household/coach, /big-brain/dashboard   Big Brain (Manvi)
  /security/*, /account/*         misuse safeguards: pattern, Microsoft Authenticator, undoable reset

Every endpoint except /health and /auth/* needs `Authorization: Bearer <token>` from /auth/login.
With SUPABASE_URL + SUPABASE_PUBLISHABLE_KEY set, that is the Supabase access token and row-level
security applies. Without them the backend runs in local mode (accounts and data in local files).
"""

from dotenv import load_dotenv

load_dotenv()  # reads backend/.env (never committed) before settings are used

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from core.identity import IdentityMiddleware, mode  # noqa: E402
from core.identity import router as auth_router  # noqa: E402
from core.security import SecurityError  # noqa: E402
from core.accounts import SetupNeeded  # noqa: E402
from electricity.api import router as electricity_router  # noqa: E402
from food_recognition import food_router  # noqa: E402
from integration.gateway import router as app_router  # noqa: E402
from integration.security_routes import router as security_router  # noqa: E402
from integration.extras import router as extras_router  # noqa: E402
from pantry.router import router as household_router  # noqa: E402
from receipts.router import router as receipts_router  # noqa: E402
from recipes.router import router as recipes_router  # noqa: E402
from water.api import router as water_router  # noqa: E402

app = FastAPI(title="LiveBetter API", version="1.0")

# Allows the Expo web preview to call the API. Auth is by bearer token, not cookies.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(IdentityMiddleware)


@app.exception_handler(SetupNeeded)
def setup_needed(_: Request, exc: SetupNeeded):
    return JSONResponse(status_code=503, content={"detail": {"code": "database_setup_missing", "message": str(exc),
                                                             "details": {}}})


@app.exception_handler(SecurityError)
def security_error(_: Request, exc: SecurityError):
    return JSONResponse(status_code=exc.status, content={"detail": {"code": exc.code, "message": exc.message,
                                                                    "details": exc.details}})


# Friendly form errors (14 Nov): "Check the billing start date: use a date like 2026-09-13" instead of Pydantic's
# technical list. The original details stay in "details" for developers.
FIELD_NAMES = {"period_start": "billing start date", "period_end": "billing end date", "start": "billing start date",
               "end": "billing end date", "units": "amount used on the bill", "m3": "water used (m³)",
               "kwh": "electricity used (kWh)", "amount": "bill amount", "amount_rs": "bill amount", "email": "email",
               "password": "password", "message": "message", "question": "question", "members": "number of people",
               "date": "date", "index_m3": "meter number", "index_kwh": "meter number", "quantity": "quantity",
               "name": "name", "pattern": "pattern", "code": "code"}


def _friendly(e):
    field = next((str(x) for x in reversed(e.get("loc", [])) if isinstance(x, str) and x != "body"), "")
    label = FIELD_NAMES.get(field, field.replace("_", " ") or "form")
    t, ctx = e.get("type", ""), e.get("ctx") or {}
    if t == "missing":
        return f"Please fill in the {label}."
    if "date" in t:
        return f"Check the {label}: use a date like 2026-09-13."
    if t in ("greater_than", "greater_than_equal"):
        return f"The {label} must be more than {float(ctx.get('gt', ctx.get('ge', 0))):g}."
    if t in ("less_than", "less_than_equal"):
        return f"The {label} is too big."
    if t in ("float_parsing", "int_parsing", "float_type", "int_type"):
        return f"The {label} must be a number."
    if t == "string_too_short":
        return f"The {label} is too short."
    if t == "string_too_long":
        return f"The {label} is too long."
    msg = str(e.get("msg", "")).replace("Value error, ", "")
    return f"Check the {label}: {msg}" if label != "form" else msg or "Please check the form."


from fastapi.exceptions import RequestValidationError  # noqa: E402


@app.exception_handler(RequestValidationError)
def validation_error(_: Request, exc: RequestValidationError):
    errors = exc.errors()
    return JSONResponse(status_code=422, content={"detail": {"code": "validation_error",
                                                             "message": " ".join(dict.fromkeys(_friendly(e) for e in errors[:3])),
                                                             "details": {"errors": [{"loc": list(e.get("loc", [])), "msg": e.get("msg")}
                                                                                    for e in errors]}}})


@app.exception_handler(Exception)
def unexpected_error(_: Request, exc: Exception):
    import logging
    logging.getLogger("livebetter").exception("Unexpected error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": {"code": "server_error", "details": {},
                        "message": "Something went wrong on our side. Your data is safe: please try again in a moment."}})


app.include_router(auth_router)
app.include_router(app_router)
app.include_router(security_router)
app.include_router(extras_router)
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
