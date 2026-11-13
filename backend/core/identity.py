"""One login and one household for every module.

Two modes, chosen automatically:
  supabase : SUPABASE_URL + SUPABASE_PUBLISHABLE_KEY are set. The app sends the Supabase access token;
             we check it with Supabase and attach it to the database client, so row-level security and
             the SQL functions apply (same rule as the food module and the Big Brain notebook).
  local    : no keys. One demo account (LIVEBETTER_EMAIL / LIVEBETTER_PASSWORD), data in a local file
             database that behaves like Supabase (core/localdb.py). For laptops, tests and a no-network demo.

IdentityMiddleware reads `Authorization: Bearer <token>` once per request and stores who is calling in a
context variable. Water, electricity, food and Big Brain all read it, so they share the same household.
"""
import hashlib
import hmac
import logging
import os
from contextvars import ContextVar
from dataclasses import dataclass, field

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from .config import get_settings

log = logging.getLogger(__name__)


@dataclass
class RequestContext:
    user_id: str
    db: object
    mode: str                                   # "supabase" | "local"
    email: str | None = None
    _household: dict | None = field(default=None, repr=False)
    _looked_up: bool = field(default=False, repr=False)


CURRENT: ContextVar[RequestContext | None] = ContextVar("livebetter_request", default=None)
_LOCAL_DBS = {}


def mode():
    s = get_settings()
    return "supabase" if s.supabase_url and s.supabase_key else "local"


def _local_email():
    return os.environ.get("LIVEBETTER_EMAIL", "demo@livebetter.mu").strip().lower()


def local_token():
    secret = os.environ.get("LIVEBETTER_SECRET", "change-me")
    return "local-" + hmac.new(secret.encode(), _local_email().encode(), hashlib.sha256).hexdigest()


def local_db(user_id="local-demo-user"):
    from .localdb import LocalDB
    if user_id not in _LOCAL_DBS:
        _LOCAL_DBS[user_id] = LocalDB(user_id)
    return _LOCAL_DBS[user_id]


def _supabase_client():
    from supabase import create_client
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_key)


def resolve(token):
    """Token -> RequestContext, or None if the token is not valid."""
    if not token:
        return None
    if hmac.compare_digest(token, local_token()):
        return RequestContext("local-demo-user", local_db(), "local", _local_email())
    if mode() == "supabase":
        try:
            db = _supabase_client()
            resp = db.auth.get_user(token)
            if not resp or not resp.user:
                return None
            db.postgrest.auth(token)
            return RequestContext(resp.user.id, db, "supabase", getattr(resp.user, "email", None))
        except Exception as exc:                     # expired / invalid token, Supabase unreachable
            log.info("Token rejected: %s", type(exc).__name__)
            return None
    return None


def household(ctx: RequestContext | None):
    """The caller's household (first one they own), or None before onboarding. Cached per request."""
    if ctx is None:
        return None
    if not ctx._looked_up:
        rows = (ctx.db.table("households").select("id,name,members,currency,preferences,budget_goals,created_at")
                .eq("owner_id", ctx.user_id).order("created_at").limit(1).execute().data or [])
        ctx._household, ctx._looked_up = (rows[0] if rows else None), True
    return ctx._household


def forget_household(ctx):
    ctx._looked_up, ctx._household = False, None


def err(status, code, message, details=None):
    raise HTTPException(status, {"code": code, "message": message, "details": details or {}})


def require_context():
    ctx = CURRENT.get()
    if ctx is None:
        err(401, "unauthorized", "Log in first: send 'Authorization: Bearer <access token>' (POST /auth/login).")
    return ctx


def require_household():
    ctx = require_context()
    h = household(ctx)
    if h is None:
        err(409, "onboarding_required", "Set up your household first (POST /households/onboarding).")
    return ctx, h


class IdentityMiddleware:
    """Pure ASGI middleware, so the context variable is visible inside sync endpoints and dependencies."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        auth = dict(scope.get("headers") or []).get(b"authorization", b"").decode()
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        ctx = await run_in_threadpool(resolve, token) if token else None
        reset = CURRENT.set(ctx)
        try:
            await self.app(scope, receive, send)
        finally:
            CURRENT.reset(reset)


# ---------- login routes (the app calls these; no Supabase SDK needed in the app) ----------
router = APIRouter(prefix="/auth", tags=["auth"])


class Credentials(BaseModel):
    email: str
    password: str


class Refresh(BaseModel):
    refresh_token: str


def _session_out(session, user):
    return {"token": session.access_token, "access_token": session.access_token, "token_type": "bearer",
            "refresh_token": session.refresh_token, "expires_in": session.expires_in,
            "user": {"id": user.id, "email": user.email}, "mode": "supabase"}


@router.post("/login")
def login(body: Credentials):
    if mode() == "local":
        password = os.environ.get("LIVEBETTER_PASSWORD", "demo1234")
        if body.email.strip().lower() != _local_email() or not hmac.compare_digest(body.password, password):
            err(401, "wrong_details", "Email or password is not correct.")
        return {"token": local_token(), "access_token": local_token(), "token_type": "bearer",
                "refresh_token": None, "expires_in": None, "user": {"id": "local-demo-user", "email": _local_email()},
                "mode": "local"}
    try:
        res = _supabase_client().auth.sign_in_with_password({"email": body.email.strip(), "password": body.password})
    except Exception:
        err(401, "wrong_details", "Email or password is not correct.")
    return _session_out(res.session, res.user)


@router.post("/signup")
def signup(body: Credentials):
    if mode() == "local":
        err(400, "local_mode", "Local mode has one demo account. Sign in with the demo email and password.")
    if len(body.password) < 6:
        err(422, "validation_error", "Password must have at least 6 characters.")
    try:
        res = _supabase_client().auth.sign_up({"email": body.email.strip(), "password": body.password})
    except Exception as exc:
        err(400, "signup_failed", f"Could not create the account: {exc}")
    if res.session is None:
        return {"token": None, "message": "Account created. Confirm your email, then sign in.", "mode": "supabase"}
    return _session_out(res.session, res.user)


@router.post("/refresh")
def refresh(body: Refresh):
    if mode() == "local":
        return {"token": local_token(), "access_token": local_token(), "mode": "local"}
    try:
        res = _supabase_client().auth.refresh_session(body.refresh_token)
    except Exception:
        err(401, "unauthorized", "Session expired. Log in again.")
    return _session_out(res.session, res.user)


@router.get("/me")
def me():
    ctx = require_context()
    h = household(ctx)
    return {"mode": ctx.mode, "user": {"id": ctx.user_id, "email": ctx.email}, "household": h,
            "onboarding_required": h is None}
