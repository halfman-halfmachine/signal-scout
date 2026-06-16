"""Runtime configuration sourced from environment variables.

All settings are read once at import time. Defaults make the app run with zero
configuration: open access, an ephemeral-friendly data dir, template-only
generation when no Anthropic key is present.
"""
from __future__ import annotations

import os
from pathlib import Path

# Directory holding the SQLite database (and any future state). Mounted as a
# volume in Docker so data survives container restarts.
DATA_DIR = Path(os.environ.get("DATA_DIR", "./data")).expanduser().resolve()

# Optional shared password. When unset/empty the app is fully open.
SCOUT_PASSWORD = os.environ.get("SCOUT_PASSWORD", "").strip()

# Anthropic API key. When unset, /api/generate falls back to template output.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

# Claude model + token budget (kept overridable for cost control).
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-5").strip()
ANTHROPIC_MAX_TOKENS = int(os.environ.get("ANTHROPIC_MAX_TOKENS", "2800"))

# Secret used to sign session cookies. Auto-generated per-process if unset,
# which logs everyone out on restart but keeps things zero-config.
SECRET_KEY = os.environ.get("SECRET_KEY", "").strip() or os.urandom(32).hex()

# Where the built Next.js static export lives (populated in the Docker image).
STATIC_DIR = Path(os.environ.get("STATIC_DIR", "./static")).expanduser().resolve()

DB_PATH = DATA_DIR / "signal_scout.db"

# Common User-Agent for outbound ingestion requests.
USER_AGENT = os.environ.get("SCOUT_USER_AGENT", "signal-scout/1.0")


def auth_enabled() -> bool:
    return bool(SCOUT_PASSWORD)


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
