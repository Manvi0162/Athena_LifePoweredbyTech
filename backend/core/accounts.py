"""Accounts and per-user security records.

LOCAL mode (no Supabase keys): real registration and login on this backend.
  - users are kept in backend/.localdata/accounts.json (git-ignored)
  - passwords: PBKDF2-SHA256, 200,000 rounds, random salt per user (never stored in clear)
  - session token: "lb1.<user id>.<signature>" signed with LIVEBETTER_SECRET (HMAC-SHA256)
  - the demo account (LIVEBETTER_EMAIL / LIVEBETTER_PASSWORD) is created automatically
SUPABASE mode: Supabase Auth owns accounts and passwords; this file only stores each user's security
  record (pattern, authenticator, lockouts) in the user_security table (sql/04_user_security.sql).
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import uuid
from datetime import datetime, timezone

_LOCK = threading.RLock()
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _root():
    from .localdb import ROOT
    os.makedirs(ROOT, exist_ok=True)
    return ROOT


def _path():
    return os.path.join(_root(), "accounts.json")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _secret():
    return os.environ.get("LIVEBETTER_SECRET", "change-me").encode()


# ---------- passwords ----------
def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return "pbkdf2$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def check_password(password, stored):
    try:
        _, salt, digest = stored.split("$")
        expected = hash_password(password, base64.b64decode(salt)).split("$")[2]
        return hmac.compare_digest(expected, digest)
    except Exception:
        return False


# ---------- local users ----------
def _load():
    with _LOCK:
        if os.path.exists(_path()):
            with open(_path(), encoding="utf-8") as fh:
                data = json.load(fh)
        else:
            data = {"users": {}, "emails": {}}
        demo_email = os.environ.get("LIVEBETTER_EMAIL", "demo@livebetter.mu").strip().lower()
        if demo_email not in data["emails"]:
            data["users"]["local-demo-user"] = {
                "id": "local-demo-user", "name": "Demo user", "email": demo_email,
                "password_hash": hash_password(os.environ.get("LIVEBETTER_PASSWORD", "demo1234")),
                "created_at": _now(), "security": {}}
            data["emails"][demo_email] = "local-demo-user"
            _save(data)
        return data


def _save(data):
    with _LOCK:
        tmp = _path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1)
        os.replace(tmp, _path())


def create_local_user(name, email, password):
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        raise ValueError("Enter a valid email address.")
    if len(password) < 8:
        raise ValueError("Use at least 8 characters for the password.")
    with _LOCK:
        data = _load()
        if email in data["emails"]:
            raise FileExistsError("An account with this email already exists. Log in instead.")
        uid = "u-" + uuid.uuid4().hex[:12]
        data["users"][uid] = {"id": uid, "name": (name or "").strip()[:80], "email": email,
                              "password_hash": hash_password(password), "created_at": _now(), "security": {}}
        data["emails"][email] = uid
        _save(data)
        return data["users"][uid]


def local_user_by_email(email):
    data = _load()
    uid = data["emails"].get(email.strip().lower())
    return data["users"].get(uid) if uid else None


def local_user(uid):
    return _load()["users"].get(uid)


# ---------- local session tokens ----------
def make_token(uid):
    sig = hmac.new(_secret(), f"lb1.{uid}".encode(), hashlib.sha256).hexdigest()
    return f"lb1.{uid}.{sig}"


def read_token(token):
    try:
        prefix, uid, sig = token.split(".", 2)
    except ValueError:
        return None
    if prefix != "lb1":
        return None
    expected = hmac.new(_secret(), f"lb1.{uid}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    return uid if local_user(uid) else None


# ---------- per-user security record (both modes) ----------
def load_security(user_id, db=None, mode="local"):
    if mode == "local":
        return (_load()["users"].get(user_id) or {}).get("security") or {}
    rows = db.table("user_security").select("data").eq("user_id", user_id).limit(1).execute().data or []
    return rows[0]["data"] if rows else {}


def save_security(user_id, sec, db=None, mode="local"):
    if mode == "local":
        with _LOCK:
            data = _load()
            data["users"][user_id]["security"] = sec
            _save(data)
        return
    db.table("user_security").upsert({"user_id": user_id, "data": sec, "updated_at": _now()},
                                     on_conflict="user_id").execute()
