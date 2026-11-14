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


def local_token(user_id="local-demo-user"):
    from .accounts import _load, make_token
    _load()                                            # makes sure the demo account exists
    return make_token(user_id)


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
    if token.startswith("lb1."):
        from .accounts import local_user, read_token
        uid = read_token(token)
        if uid and mode() == "local":
            return RequestContext(uid, local_db(uid), "local", local_user(uid)["email"])
        return None
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
    """The caller's household (the newest one they own, e.g. the database team's seeded demo household),
    or None before onboarding. Cached per request."""
    if ctx is None:
        return None
    if not ctx._looked_up:
        rows = (ctx.db.table("households").select("id,name,members,currency,preferences,budget_goals,created_at")
                .eq("owner_id", ctx.user_id).order("created_at", desc=True).limit(1).execute().data or [])
        ctx._household, ctx._looked_up = (rows[0] if rows else None), True
    return ctx._household


def forget_household(ctx):
    ctx._looked_up, ctx._household = False, None


def err(status, code, message, details=None):
    raise HTTPException(status, {"code": code, "message": message, "details": details or {}})


def require_context():
    ctx = CURRENT.get()
    if ctx is None:
        err(401, "unauthorized", "Please log in to continue.")
    return ctx


def require_household():
    ctx = require_context()
    h = household(ctx)
    if h is None:
        err(409, "onboarding_required", "Set up your household first: it takes about a minute.")
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


class Signup(BaseModel):
    email: str
    password: str
    name: str = ""


class MfaIn(BaseModel):
    mfa_token: str
    code: str | None = None
    recovery_code: str | None = None


class Refresh(BaseModel):
    refresh_token: str


_LOGIN_FAILS = {}                                       # email -> (count, locked_until); simple brute-force limit


def _login_guard(email):
    import time
    count, until = _LOGIN_FAILS.get(email, (0, 0))
    if until > time.time():
        err(423, "locked", f"Too many wrong passwords. Try again in {int(until - time.time()) // 60 + 1} min.")


def _login_failed(email):
    import time
    count, _ = _LOGIN_FAILS.get(email, (0, 0))
    count += 1
    _LOGIN_FAILS[email] = (0, time.time() + 300) if count >= 5 else (count, 0)
    err(401, "wrong_details", "Email or password is not correct.")


def _session_out(session, user):
    return {"token": session.access_token, "access_token": session.access_token, "token_type": "bearer",
            "refresh_token": session.refresh_token, "expires_in": session.expires_in,
            "user": {"id": user.id, "email": user.email,
                     "name": (getattr(user, "user_metadata", None) or {}).get("name")}, "mode": "supabase"}


def _local_out(user):
    from .accounts import make_token
    return {"token": make_token(user["id"]), "access_token": make_token(user["id"]), "token_type": "bearer",
            "refresh_token": None, "expires_in": None,
            "user": {"id": user["id"], "email": user["email"], "name": user.get("name")}, "mode": "local"}


def _needs_code(user_id, db, mode_):
    from .security import login_needs_code
    return login_needs_code(user_id, db, mode_)


@router.post("/login")
def login(body: Credentials):
    """Step 1: email + password. If the user switched on Microsoft Authenticator, the answer is
    {mfa_required: true, mfa_token} and the session is only given after POST /auth/mfa."""
    from .security import mfa_token
    email = body.email.strip().lower()
    _login_guard(email)
    if mode() == "local":
        from .accounts import check_password, local_user_by_email
        user = local_user_by_email(email)
        if not user or not check_password(body.password, user["password_hash"]):
            _login_failed(email)
        _LOGIN_FAILS.pop(email, None)
        if _needs_code(user["id"], None, "local"):
            return {"mfa_required": True, "mfa_token": mfa_token({"mode": "local", "uid": user["id"]}),
                    "message": "Enter the 6-digit code from Microsoft Authenticator."}
        return _local_out(user)
    try:
        res = _supabase_client().auth.sign_in_with_password({"email": email, "password": body.password})
    except Exception:
        _login_failed(email)
    _LOGIN_FAILS.pop(email, None)
    db = _supabase_client()
    db.postgrest.auth(res.session.access_token)
    if _needs_code(res.user.id, db, "supabase"):
        return {"mfa_required": True, "message": "Enter the 6-digit code from Microsoft Authenticator.",
                "mfa_token": mfa_token({"mode": "supabase", "uid": res.user.id, "email": email,
                                        "access": res.session.access_token, "refresh": res.session.refresh_token,
                                        "expires_in": res.session.expires_in})}
    return _session_out(res.session, res.user)


@router.post("/mfa")
def login_mfa(body: MfaIn):
    """Step 2 of login when Microsoft Authenticator is on: the code (or a recovery code) gives the session."""
    from . import security as S
    t = S.read_mfa_token(body.mfa_token)
    if t["mode"] == "local":
        from .accounts import local_user
        ctx = RequestContext(t["uid"], local_db(t["uid"]), "local", local_user(t["uid"])["email"])
    else:
        db = _supabase_client()
        db.postgrest.auth(t["access"])
        ctx = RequestContext(t["uid"], db, "supabase", t.get("email"))
    sec = S.load(ctx)
    S.prove_owner(ctx, sec, {"code": body.code, "recovery_code": body.recovery_code}, "login")
    S.record(ctx, sec, "login_with_authenticator")
    S.save(ctx, sec)
    if t["mode"] == "local":
        from .accounts import local_user
        return _local_out(local_user(t["uid"]))
    return {"token": t["access"], "access_token": t["access"], "token_type": "bearer", "refresh_token": t["refresh"],
            "expires_in": t["expires_in"], "user": {"id": t["uid"], "email": t.get("email")}, "mode": "supabase"}


@router.post("/signup")
def signup(body: Signup):
    if mode() == "local":
        from .accounts import create_local_user
        try:
            user = create_local_user(body.name, body.email, body.password)
        except FileExistsError as exc:
            err(409, "account_exists", str(exc))
        except ValueError as exc:
            err(422, "validation_error", str(exc))
        return {**_local_out(user), "message": "Account created."}
    if len(body.password) < 8:
        err(422, "validation_error", "Use at least 8 characters for the password.")
    try:
        res = _supabase_client().auth.sign_up({"email": body.email.strip(), "password": body.password,
                                               "options": {"data": {"name": body.name.strip()}}})
    except Exception as exc:
        err(400, "signup_failed", f"Could not create the account: {exc}")
    if res.session is None:
        return {"token": None, "message": "Account created. Confirm your email, then log in.", "mode": "supabase"}
    return {**_session_out(res.session, res.user), "message": "Account created."}


@router.post("/refresh")
def refresh(body: Refresh):
    if mode() == "local":
        err(400, "local_mode", "Local sessions do not expire; log in again if needed.")
    try:
        res = _supabase_client().auth.refresh_session(body.refresh_token)
    except Exception:
        err(401, "unauthorized", "Session expired. Log in again.")
    return _session_out(res.session, res.user)


@router.get("/me")
def me():
    ctx = require_context()
    h = household(ctx)
    name = None
    if ctx.mode == "local":
        from .accounts import local_user
        name = (local_user(ctx.user_id) or {}).get("name")
    return {"mode": ctx.mode, "user": {"id": ctx.user_id, "email": ctx.email, "name": name}, "household": h,
            "onboarding_required": h is None}
