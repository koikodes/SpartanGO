"""Password hashing, login tokens, and the rotating QR ride pass.

Ride pass design (replaces showing a physical ID):
  token = "<user_id>.<time_window>.<HMAC-SHA256(user_id.window, PASS_SECRET)>"
  - The window advances every PASS_WINDOW_SECONDS, so the QR changes constantly and a
    screenshot shared with a friend expires within seconds.
  - Only the server holds PASS_SECRET, so a token can't be forged.
  - Each token can be scanned once (replay protection).
"""
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import db
from .config import settings
from .models import Role, UserOut

# ---------- passwords (scrypt, stdlib) ----------

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    return hmac.compare_digest(digest.hex(), digest_hex)

# ---------- login tokens (JWT) ----------

def create_access_token(user_id: int, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": str(user_id), "role": role, "exp": exp}, settings.jwt_secret, algorithm="HS256")


_bearer = HTTPBearer(auto_error=False)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> UserOut:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    with db.connect() as c:
        row = c.execute("SELECT id, email, name, role, active FROM users WHERE id = ?", (int(payload["sub"]),)).fetchone()
    if not row or not row["active"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account not active")
    return UserOut(id=row["id"], email=row["email"], name=row["name"], role=row["role"])


def require_role(*roles: Role):
    def checker(user: UserOut = Depends(current_user)) -> UserOut:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed for your role")
        return user
    return checker

# ---------- rotating QR ride pass ----------

def _sign(user_id: int, window: int) -> str:
    msg = f"{user_id}.{window}".encode()
    return hmac.new(settings.pass_secret.encode(), msg, hashlib.sha256).hexdigest()[:32]


def issue_pass(user_id: int, now: float | None = None) -> tuple[str, int]:
    now = time.time() if now is None else now
    w = settings.pass_window_seconds
    window = int(now // w)
    expires_in = int(w - (now % w))
    return f"{user_id}.{window}.{_sign(user_id, window)}", expires_in


_used_tokens: dict[str, float] = {}


def check_pass(token: str, now: float | None = None) -> tuple[int | None, str | None]:
    """Return (user_id, None) if valid, else (None, reason)."""
    now = time.time() if now is None else now
    try:
        uid_s, window_s, sig = token.split(".")
        user_id, window = int(uid_s), int(window_s)
    except ValueError:
        return None, "Malformed pass"
    if not hmac.compare_digest(sig, _sign(user_id, window)):
        return None, "Pass signature invalid"
    current = int(now // settings.pass_window_seconds)
    if window not in (current, current - 1):  # allow one window of clock skew
        return None, "Pass expired - refresh the app"
    # forget tokens older than a few windows, then block replays
    cutoff = now - 4 * settings.pass_window_seconds
    for t, ts in list(_used_tokens.items()):
        if ts < cutoff:
            del _used_tokens[t]
    if token in _used_tokens:
        return None, "Pass already scanned"
    _used_tokens[token] = now
    return user_id, None
