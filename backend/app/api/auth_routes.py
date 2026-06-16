"""Auth router — login / logout / status. Public (no auth dependency)."""
from __future__ import annotations

from fastapi import APIRouter, Request, Response

from .. import auth, config
from .schemas import LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
def status(request: Request) -> dict:
    return {
        "auth_required": config.auth_enabled(),
        "authenticated": auth.is_authenticated(request),
    }


@router.post("/login")
def login(body: LoginRequest, response: Response) -> dict:
    if not auth.verify_password(body.password):
        response.status_code = 401
        return {"ok": False, "error": "Invalid password"}
    if config.auth_enabled():
        response.set_cookie(
            auth.COOKIE_NAME, auth.issue_token(),
            httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30,
        )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(auth.COOKIE_NAME)
    return {"ok": True}
