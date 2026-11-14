"""Shared login (same rule in every LiveBetter module, see backend/MODULE_CONTRACT.md).

One household account. The token is HMAC-SHA256(secret, email), so every module that knows the same
LIVEBETTER_SECRET accepts the same token: the user signs in once and can use water, electricity and food.
"""
import hashlib
import hmac
import os

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

EMAIL = os.environ.get("LIVEBETTER_EMAIL", "demo@livebetter.mu")
PASSWORD = os.environ.get("LIVEBETTER_PASSWORD", "demo1234")
SECRET = os.environ.get("LIVEBETTER_SECRET", "change-me")
TOKEN = hmac.new(SECRET.encode(), EMAIL.lower().encode(), hashlib.sha256).hexdigest()

router = APIRouter(tags=["auth"])


def err(status, code, message, details=None):
    raise HTTPException(status, {"code": code, "message": message, "details": details or {}})


def require_login(authorization: str = Header(default="")):
    if os.environ.get("LIVEBETTER_NO_AUTH") == "1":
        return
    try:                                   # merged backend: core/identity.py already checked the token
        from core.identity import CURRENT, require_household
        if CURRENT.get() is not None:
            require_household()
            return
    except ImportError:
        pass
    if not hmac.compare_digest(authorization, f"Bearer {TOKEN}"):
        err(401, "unauthorised", "Please log in to continue.")


class Login(BaseModel):
    email: str
    password: str


@router.post("/auth/login")
def login(b: Login):
    if b.email.strip().lower() != EMAIL.lower() or not hmac.compare_digest(b.password, PASSWORD):
        err(401, "wrong_details", "Email or password is not correct.")
    return {"token": TOKEN, "token_type": "bearer"}
