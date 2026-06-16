"""FastAPI application entry point.

Mounts the API routers and serves the built Next.js static export from the same
origin (so the front-end is pure presentation calling /api). Falls back to
index.html for client-side routes. The SQLite schema is initialized on startup.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .api.auth_routes import router as auth_router
from .api.routes import router as api_router
from .storage import database as db


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Signal Scout", version="1.0.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(api_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "name": "Signal Scout", "version": "1.0.0",
            "auth_required": config.auth_enabled(),
            "llm": "live" if config.ANTHROPIC_API_KEY else "template"}


def _mount_static() -> None:
    static_dir = config.STATIC_DIR
    if not static_dir.exists():
        return

    # Serve Next.js static assets and fall back to index.html for SPA routes.
    next_dir = static_dir / "_next"
    if next_dir.exists():
        app.mount("/_next", StaticFiles(directory=next_dir), name="next-assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        candidate = static_dir / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        html = candidate.with_suffix(".html")
        if full_path and html.is_file():
            return FileResponse(html)
        index = static_dir / "index.html"
        if index.is_file():
            return FileResponse(index)
        return JSONResponse({"detail": "Frontend not built"}, status_code=404)


_mount_static()
