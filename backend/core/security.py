"""Safeguards for the surprise card "Misuse".

MISUSE: the app stays signed in. Someone else with the unlocked phone (a child playing, a housemate, a controlling
partner) could reset the account, delete or change bills, change the household details, or switch the protection
off - wiping the household's records and evidence, or making the forecasts and advice wrong.

SAFEGUARDS (all checked on the server, so the app cannot be bypassed):
  1. Security pattern (3x3 grid, at least 4 dots), required before every sensitive action. Stored as a salted
     PBKDF2 hash. Setting or changing it needs the account password (or the authenticator / a recovery code).
  2. Microsoft / Google Authenticator (TOTP, RFC 6238), optional: offered at registration and in Settings.
     The secret is created here, encrypted (Fernet, MFA_ENCRYPTION_KEY) and never shown again after setup;
     a code is required once to switch it on; 30 s of clock difference allowed; a code works only once.
     8 one-time recovery codes (hashed) in case the phone is lost.
  3. Limits: 5 wrong patterns or codes -> locked for 5 minutes.
  4. A sensitive action gets a one-time permission (step-up token) valid 5 minutes for that action only.
  5. Every failure, lock and sensitive action is recorded and shown to the owner (Home alert, Activity).
  (6. Reset is undoable for 24 hours: integration/account.py.)
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

from . import accounts

SENSITIVE = {"reset_account": "reset the account", "restore_account": "restore the account",
             "delete_bill": "delete or change a bill", "edit_household": "change the household details",
             "security_off": "switch security off"}
MAX_TRIES = 5
LOCK_SECONDS = 300
STEP_UP_SECONDS = 300
MIN_DOTS = 4


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.isoformat(timespec="seconds")


class SecurityError(Exception):
    def __init__(self, status, code, message, details=None):
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details or {}


# ---------- storage helpers ----------
def load(ctx):
    return accounts.load_security(ctx.user_id, ctx.db, ctx.mode)


def save(ctx, sec):
    accounts.save_security(ctx.user_id, sec, ctx.db, ctx.mode)


def record(ctx, sec, event, **details):
    """Keep the last 50 security events for the owner, and copy them to the household activity log."""
    sec.setdefault("events", []).append({"at": _iso(_now()), "event": event, **details})
    sec["events"] = sec["events"][-50:]
    try:
        from .identity import household
        h = household(ctx)
        if h:
            ctx.db.table("activity_logs").insert({"household_id": h["id"], "event_type": f"security.{event}",
                                                  "details": {"module": "security", **details}}).execute()
    except Exception:
        pass


# ---------- encryption of the authenticator secret ----------
def _fernet():
    from cryptography.fernet import Fernet
    key = os.environ.get("MFA_ENCRYPTION_KEY", "").strip()
    if not key:
        from .identity import mode
        if mode() != "local":
            raise SecurityError(503, "mfa_not_configured", "Two-step login is not configured on the server "
                                                          "(MFA_ENCRYPTION_KEY missing in backend/.env).")
        path = os.path.join(accounts._root(), "mfa.key")       # local mode: one key file, git-ignored
        if not os.path.exists(path):
            with open(path, "wb") as fh:
                fh.write(Fernet.generate_key())
        with open(path, "rb") as fh:
            key = fh.read().decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def _encrypt(text):
    return _fernet().encrypt(text.encode()).decode()


def _decrypt(token):
    return _fernet().decrypt(token.encode()).decode()


# ---------- lockouts ----------
def _check_lock(sec, kind):
    lock = (sec.get("locks") or {}).get(kind)
    if lock and _now() < datetime.fromisoformat(lock):
        left = int((datetime.fromisoformat(lock) - _now()).total_seconds())
        raise SecurityError(423, "locked", f"Too many wrong attempts. Try again in {left // 60} min {left % 60} s.",
                            {"seconds_left": left, "locked_until": lock})


def _fail(ctx, sec, kind, action=None):
    fails = sec.setdefault("fails", {})
    fails[kind] = fails.get(kind, 0) + 1
    left = MAX_TRIES - fails[kind]
    record(ctx, sec, f"{kind}_failed", action=action, attempts_left=max(left, 0))
    if left <= 0:
        until = _iso(_now() + timedelta(seconds=LOCK_SECONDS))
        sec.setdefault("locks", {})[kind] = until
        fails[kind] = 0
        record(ctx, sec, f"{kind}_locked", action=action, locked_until=until)
        save(ctx, sec)
        raise SecurityError(423, "locked", "Too many wrong attempts. Locked for 5 minutes. The owner can see this "
                                           "attempt in Activity.", {"seconds_left": LOCK_SECONDS, "locked_until": until})
    save(ctx, sec)
    return left


def _ok(sec, kind):
    sec.setdefault("fails", {})[kind] = 0
    (sec.get("locks") or {}).pop(kind, None)


# ---------- pattern ----------
def _valid_pattern(pattern):
    if not isinstance(pattern, list) or not all(isinstance(p, int) and 1 <= p <= 9 for p in pattern):
        raise SecurityError(422, "validation_error", "A pattern is a list of dots numbered 1 to 9.")
    if len(pattern) < MIN_DOTS or len(set(pattern)) != len(pattern):
        raise SecurityError(422, "validation_error", f"Connect at least {MIN_DOTS} different dots.")
    return "-".join(map(str, pattern))


def _hash_pattern(text, salt):
    return base64.b64encode(hashlib.pbkdf2_hmac("sha256", text.encode(), salt, 200_000)).decode()


def set_pattern(ctx, pattern, proof):
    """proof = {'password': ...} or {'code': ...} (authenticator) or {'recovery_code': ...}."""
    text = _valid_pattern(pattern)
    sec = load(ctx)
    prove_owner(ctx, sec, proof, purpose="set_pattern")
    salt = secrets.token_bytes(16)
    first = not sec.get("pattern")
    sec["pattern"] = {"hash": _hash_pattern(text, salt), "salt": base64.b64encode(salt).decode(), "set_at": _iso(_now())}
    _ok(sec, "pattern")
    record(ctx, sec, "pattern_set" if first else "pattern_changed")
    save(ctx, sec)
    return status(ctx)


def verify_pattern(ctx, pattern, action):
    if action not in SENSITIVE:
        raise SecurityError(422, "validation_error", f"Unknown action. One of: {', '.join(SENSITIVE)}")
    sec = load(ctx)
    if not sec.get("pattern"):
        raise SecurityError(428, "pattern_required", "Set a security pattern first (Settings -> Security). "
                                                     f"It is needed to {SENSITIVE[action]}.")
    _check_lock(sec, "pattern")
    try:
        text = _valid_pattern(pattern)
    except SecurityError:
        text = "invalid"
    expected = sec["pattern"]["hash"]
    got = _hash_pattern(text, base64.b64decode(sec["pattern"]["salt"]))
    if not hmac.compare_digest(expected, got):
        left = _fail(ctx, sec, "pattern", action)
        raise SecurityError(401, "wrong_pattern", f"Wrong pattern. {left} attempt{'s' if left != 1 else ''} left "
                                                  "before a 5-minute lock.", {"attempts_left": left})
    _ok(sec, "pattern")
    jti = secrets.token_hex(8)
    exp = int(time.time()) + STEP_UP_SECONDS
    sec.setdefault("step_up", {})[jti] = {"action": action, "exp": exp}
    sec["step_up"] = {k: v for k, v in sec["step_up"].items() if v["exp"] > time.time()}
    record(ctx, sec, "pattern_ok", action=action)
    save(ctx, sec)
    return {"step_up_token": _sign(f"{ctx.user_id}|{action}|{exp}|{jti}"), "action": action,
            "expires_in": STEP_UP_SECONDS}


def _sign(payload):
    sig = hmac.new(os.environ.get("LIVEBETTER_SECRET", "change-me").encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(payload.encode()).decode() + "." + sig


def require_step_up(ctx, action, token):
    """Called by every sensitive endpoint. Raises unless a fresh, unused permission for this action is given."""
    sec = load(ctx)
    if not token:
        record(ctx, sec, "blocked", action=action, reason="no pattern given")
        save(ctx, sec)
        raise SecurityError(403, "pattern_required" if sec.get("pattern") else "pattern_not_set",
                            f"Draw your security pattern to {SENSITIVE[action]}." if sec.get("pattern") else
                            f"Set a security pattern first (Settings -> Security). It is needed to {SENSITIVE[action]}.",
                            {"action": action})
    try:
        raw, sig = token.rsplit(".", 1)
        payload = base64.urlsafe_b64decode(raw.encode()).decode()
        uid, act, exp, jti = payload.split("|")
        good = hmac.compare_digest(_sign(payload).rsplit(".", 1)[1], sig)
    except Exception:
        good, uid, act, exp, jti = False, "", "", "0", ""
    entry = (sec.get("step_up") or {}).get(jti)
    if not good or uid != ctx.user_id or act != action or int(exp) < time.time() or not entry:
        record(ctx, sec, "blocked", action=action, reason="invalid or used permission")
        save(ctx, sec)
        raise SecurityError(403, "pattern_required", f"Draw your security pattern again to {SENSITIVE[action]}.",
                            {"action": action})
    sec["step_up"].pop(jti, None)                       # one use only
    record(ctx, sec, "allowed", action=action)
    save(ctx, sec)


def guard(action, token):
    """For module routes (water, electricity): enforce the pattern when called through the merged backend."""
    from .identity import CURRENT
    ctx = CURRENT.get()
    if ctx is not None:
        require_step_up(ctx, action, token)


# ---------- proving it is the owner (password / authenticator / recovery code) ----------
def _check_password(ctx, password):
    if ctx.mode == "local":
        user = accounts.local_user(ctx.user_id)
        return bool(user) and accounts.check_password(password or "", user["password_hash"])
    try:
        from .identity import _supabase_client
        _supabase_client().auth.sign_in_with_password({"email": ctx.email, "password": password or ""})
        return True
    except Exception:
        return False


def prove_owner(ctx, sec, proof, purpose):
    proof = proof or {}
    if (sec.get("totp") or {}).get("enabled"):
        if proof.get("code"):
            return verify_totp(ctx, sec, proof["code"], purpose)
        if proof.get("recovery_code"):
            return use_recovery_code(ctx, sec, proof["recovery_code"], purpose)
        raise SecurityError(401, "code_required", "Enter the 6-digit code from Microsoft Authenticator "
                                                  "(or a recovery code).")
    _check_lock(sec, "password")
    if not _check_password(ctx, proof.get("password")):
        left = _fail(ctx, sec, "password", purpose)
        raise SecurityError(401, "wrong_password", f"Password is not correct. {left} attempts left.")
    _ok(sec, "password")
    return True


# ---------- authenticator (TOTP) ----------
def totp_setup(ctx):
    import pyotp
    import segno
    sec = load(ctx)
    if (sec.get("totp") or {}).get("enabled"):
        raise SecurityError(409, "already_enabled", "Microsoft Authenticator is already on.")
    secret = pyotp.random_base32()
    label = ctx.email or ctx.user_id
    uri = pyotp.TOTP(secret).provisioning_uri(name=label, issuer_name="LiveBetter")
    sec["totp"] = {"enabled": False, "secret": _encrypt(secret), "created_at": _iso(_now())}
    save(ctx, sec)
    qr = segno.make(uri, error="m").png_data_uri(scale=6, border=2)
    return {"otpauth_uri": uri, "qr_png": qr, "manual_key": secret,
            "note": "Scan with Microsoft or Google Authenticator, then enter the 6-digit code to switch it on. "
                    "This key is shown only now."}


def verify_totp(ctx, sec, code, purpose):
    import pyotp
    t = sec.get("totp") or {}
    if not t.get("secret"):
        raise SecurityError(409, "not_set_up", "Microsoft Authenticator is not set up.")
    _check_lock(sec, "code")
    code = str(code or "").replace(" ", "")
    totp = pyotp.TOTP(_decrypt(t["secret"]))
    now_step = int(time.time() // 30)
    matched = None
    for step in (now_step - 1, now_step, now_step + 1):                 # +-30 s clock difference
        if hmac.compare_digest(totp.at(step * 30), code):
            matched = step
    if matched is None or matched <= t.get("last_step", -1):           # a code can only be used once
        _fail(ctx, sec, "code", purpose)
        raise SecurityError(401, "wrong_code", "That code is not correct or was already used. Wait for the next code.")
    t["last_step"] = matched
    _ok(sec, "code")
    return True


def totp_confirm(ctx, code):
    sec = load(ctx)
    t = sec.get("totp") or {}
    if t.get("enabled"):
        raise SecurityError(409, "already_enabled", "Microsoft Authenticator is already on.")
    verify_totp(ctx, sec, code, "totp_setup")
    t["enabled"], t["enabled_at"] = True, _iso(_now())
    codes = ["-".join(secrets.token_hex(2) for _ in range(2)) for _ in range(8)]
    sec["recovery_codes"] = [hashlib.sha256(c.encode()).hexdigest() for c in codes]
    record(ctx, sec, "authenticator_on")
    save(ctx, sec)
    return {"enabled": True, "recovery_codes": codes,
            "note": "Keep these 8 recovery codes somewhere safe. Each works once if you lose your phone."}


def use_recovery_code(ctx, sec, code, purpose):
    _check_lock(sec, "code")
    h = hashlib.sha256(str(code or "").strip().lower().encode()).hexdigest()
    if h not in (sec.get("recovery_codes") or []):
        _fail(ctx, sec, "code", purpose)
        raise SecurityError(401, "wrong_code", "That recovery code is not valid or was already used.")
    sec["recovery_codes"].remove(h)
    _ok(sec, "code")
    record(ctx, sec, "recovery_code_used", purpose=purpose, left=len(sec["recovery_codes"]))
    return True


def totp_disable(ctx, code, step_up_token, recovery_code=None):
    """Turning the authenticator off needs BOTH the pattern (step-up) and a code: a misuser with only one cannot."""
    require_step_up(ctx, "security_off", step_up_token)
    sec = load(ctx)
    if not (sec.get("totp") or {}).get("enabled"):
        raise SecurityError(409, "not_set_up", "Microsoft Authenticator is not on.")
    prove_owner(ctx, sec, {"code": code, "recovery_code": recovery_code}, "authenticator_off")
    sec["totp"], sec["recovery_codes"] = {}, []
    record(ctx, sec, "authenticator_off")
    save(ctx, sec)
    return status(ctx)


def login_needs_code(user_id, db, mode):
    return bool((accounts.load_security(user_id, db, mode).get("totp") or {}).get("enabled"))


def status(ctx):
    sec = load(ctx)
    since = _now() - timedelta(hours=24)
    recent = [e for e in sec.get("events", []) if datetime.fromisoformat(e["at"]) >= since]
    failures = [e for e in recent if e["event"].endswith("_failed") or e["event"].endswith("_locked")
                or e["event"] == "blocked"]
    locks = {k: v for k, v in (sec.get("locks") or {}).items() if datetime.fromisoformat(v) > _now()}
    alert = None
    if failures:
        last = failures[-1]
        alert = {"count": len(failures), "last_at": last["at"],
                 "message": f"{len(failures)} blocked or wrong security attempt{'s' if len(failures) != 1 else ''} "
                            f"in the last 24 hours (last: {last['event'].replace('_', ' ')}"
                            + (f" while trying to {SENSITIVE.get(last.get('action'), last.get('action'))}" if last.get("action") else "")
                            + "). If this was not you, change your pattern."}
    return {"pattern_set": bool(sec.get("pattern")), "pattern_set_at": (sec.get("pattern") or {}).get("set_at"),
            "authenticator_on": bool((sec.get("totp") or {}).get("enabled")),
            "recovery_codes_left": len(sec.get("recovery_codes") or []), "locks": locks, "alert": alert,
            "recent_events": list(reversed(sec.get("events", [])))[:15],
            "protected_actions": SENSITIVE}


def mfa_token(payload):
    """Short-lived, encrypted ticket between the password step and the authenticator step of login."""
    return _encrypt(json.dumps({**payload, "exp": int(time.time()) + 300}))


def read_mfa_token(token):
    try:
        data = json.loads(_decrypt(token))
    except Exception:
        raise SecurityError(401, "login_expired", "Login expired. Enter your email and password again.")
    if data["exp"] < time.time():
        raise SecurityError(401, "login_expired", "Login expired. Enter your email and password again.")
    return data
