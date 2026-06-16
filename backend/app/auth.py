"""Optional shared-password auth.

When SCOUT_PASSWORD is unset the app is fully open. When set, clients log in via
POST /api/auth/login to receive a signed, time-limited session cookie; protected
routes require it. Static assets and the auth/health endpoints stay public so the
login screen can load.
"""
from __future__ import annotations

import hmac

from fastapi import HTTPException, Request, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from . import config

COOKIE_NAME = "scout_session"
_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
_serializer = URLSafeTimedSerializer(config.SECRET_KEY, salt="scout-session")


def verify_password(password: str) -> bool:
    if not config.auth_enabled():
        return True
    return hmac.compare_digest(password or "", config.SCOUT_PASSWORD)


def issue_token() -> str:
    return _serializer.dumps({"ok": True})


def _token_valid(token: str | None) -> bool:
    if not token:
        return False
    try:
        _serializer.loads(token, max_age=_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def is_authenticated(request: Request) -> bool:
    if not config.auth_enabled():
        return True
    return _token_valid(request.cookies.get(COOKIE_NAME))


def require_auth(request: Request) -> None:
    """FastAPI dependency for protected API routes."""
    if not is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
