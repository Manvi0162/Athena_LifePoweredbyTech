"""Per-request Supabase client acting as the logged-in user.

The app logs in with Supabase Auth and sends `Authorization: Bearer <access token>`.
We attach that token to the database client, so every query and RPC runs as that
user: row-level security and auth.uid() in her SQL functions work unchanged.
"""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client

from .config import get_settings


@dataclass
class UserContext:
    user_id: str
    db: Client


@dataclass
class HouseholdContext:
    user_id: str
    db: Client
    household: dict

    @property
    def household_id(self) -> str:
        return self.household["id"]


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(status_code=401, detail={"code": "unauthorized", "message": message})


# Gives /docs an "Authorize" button: paste the access token once.
bearer = HTTPBearer(auto_error=False, description="Supabase access token from the app's login")


def get_user_context(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> UserContext:
    if creds is None or not creds.credentials:
        raise _unauthorized("Log in first: send 'Authorization: Bearer <access token>'.")
    token = creds.credentials.strip()

    settings = get_settings()
    db = create_client(settings.supabase_url, settings.supabase_key)
    try:
        response = db.auth.get_user(token)
    except Exception:
        raise _unauthorized("Session expired or invalid. Log in again.")
    if not response or not response.user:
        raise _unauthorized("Session expired or invalid. Log in again.")

    db.postgrest.auth(token)
    return UserContext(user_id=response.user.id, db=db)


def get_household_context(
    user: UserContext = Depends(get_user_context),
    household_id: str | None = Query(default=None,
                                     description="Optional. Defaults to the user's first household."),
) -> HouseholdContext:
    query = (user.db.table("households")
             .select("id,name,members,currency,preferences,budget_goals")
             .eq("owner_id", user.user_id))
    if household_id:
        query = query.eq("id", household_id)
    rows = query.order("created_at").limit(1).execute().data or []
    if not rows:
        raise HTTPException(status_code=404, detail={
            "code": "no_household", "message": "No household found for this user."})
    return HouseholdContext(user_id=user.user_id, db=user.db, household=rows[0])
