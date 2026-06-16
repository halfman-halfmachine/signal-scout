# CLAUDE.md

Guidance for AI agents (and humans) working in this repository.

## What this is

**Signal Scout** — a self-hostable, niche-agnostic market-signal intelligence +
content engine. It ingests items from public sources, scores them through a
12-layer engine, routes high-value signals into a queue, and generates content
(social posts, video scripts, podcast outlines) across narrative frameworks.

It is a ground-up rebuild of an original Cloudflare Worker app. The original JS
files are **not in this repo** — they live in `../sig-scout-cloudflare-original/`
as the behavioral spec, plus a vendored copy at
`backend/tests/parity/reference_engine.mjs` (see Engine parity below).

## Architecture

- **Thick server / thin client.** All logic and secrets live server-side. The
  front-end is pure presentation calling `/api`.
- **Backend:** FastAPI (Python 3.11) in `backend/app/`. Serves the API *and* the
  built front-end from one origin.
- **Frontend:** Next.js static export (`output: 'export'`) in `frontend/`. Build
  output goes to `frontend/out/`, copied into the image as `/app/static`.
- **Persistence:** embedded SQLite (stdlib `sqlite3`) under `DATA_DIR`. No
  external database. Stores the queue, learned engine state, config, and outputs.
- **Distribution:** one multi-arch Docker image (GHCR); `docker compose up`.

```
backend/app/
  config.py            # env-driven settings (DATA_DIR, SCOUT_PASSWORD, ANTHROPIC_API_KEY, ...)
  defaults_app.py      # seed for app_settings + ingestion config (ported from ssc-data.js)
  engine/
    defaults.py        # DEFAULT_ENGINE_CONFIG — all niche constants as config
    engine.py          # IntelligenceEngine orchestrator + StateStore + scoring/routing/ranking
    layers.py          # the 12 detection layers
    manual.py          # slider-driven scoring (Engine tab / manual queue) — 0.80 L2 floor
    utils.py           # tokenize, sentiment, js_round, etc.
  ingestion/sources.py # 7 concurrent fetchers (httpx + feedparser), config-driven
  llm/
    prompt.py          # build_prompt + build_template (ported from ssc-app.js)
    client.py          # Anthropic call + citation extraction + generate orchestrator
  storage/database.py  # schema, connection mgmt, CRUD for signals/config/learned_state/outputs
  services.py          # bridges routers <-> engine <-> storage
  api/                 # routes.py (main), auth_routes.py, schemas.py
  main.py              # app entry: mounts routers + serves static export with SPA fallback
frontend/              # Next.js app: lib/api.ts (typed client) + 8 tab components
```

## Core principles (do not violate)

1. **Config-driven engine.** The engine takes an injected `config` dict; all
   niche specifics (domain terms, thought leaders, competitors, sources, weights,
   thresholds, conference calendar) come from the `engine_config` table, seeded
   from `engine/defaults.py`. **Never hardcode niche values in engine logic.**
2. **Server-side secrets.** The Anthropic key lives in the server environment,
   never the browser. Generation falls back to templates when no key is set.
3. **Thin client.** No business logic or persistent state in the front-end. No
   `localStorage` for app/engine state (transient UI only). No direct calls to
   external APIs from the browser.
4. **Niche-agnostic.** Don't reintroduce Hakkoda/AI-data assumptions into code.
   Defaults are a starting point; the engine must work for any domain via config.

## Engine parity (the key correctness gate)

The Python engine is a faithful port of the original `intelligence-engine.js`.
`backend/tests/test_engine_parity.py` asserts identical scores, tiers, ranking,
noise zeroing, and the thought-leader floor against golden values generated from
the vendored reference engine.

If you change `engine/`:
```bash
cd backend
TZ=UTC node tests/parity/gen_golden.mjs > tests/parity/golden.json   # regenerate from reference
TZ=UTC python -m pytest tests/test_engine_parity.py -q               # must pass
```
The golden values must only change if you *intend* to change engine behavior. If
parity breaks unexpectedly, your port diverged from the reference — fix the port,
not the golden file.

## Commands

Backend:
```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
TZ=UTC python -m pytest -q                                  # full suite (26 tests)
DATA_DIR=./data uvicorn app.main:app --reload --port 8000   # dev server
```
Always run tests with `TZ=UTC` — Layer 6 (temporal/conference) and parity depend
on UTC.

Frontend:
```bash
cd frontend
npm install
npm run dev          # dev server
npm run build        # static export -> frontend/out
```

Docker (full stack):
```bash
docker compose up -d --build      # build from source
docker compose up -d              # pull prebuilt image from GHCR
```

## Conventions & gotchas

- **Timestamps are epoch milliseconds** throughout the engine (JS convention).
- **JS-parity math:** use `utils.js_round` (round half up) where the original used
  `Math.round`; `feedparser` returns UTC `struct_time` — convert with
  `calendar.timegm`, not `time.mktime`.
- **Two scoring paths, intentionally different:**
  - `engine/engine.py` (content-based) — full 12 layers; L2 thought-leader floor
    is **0.90**.
  - `engine/manual.py` (slider-based, Engine tab / manual queue) — floors L2 at
    **0.80** when final ≥ 0.60. This mirrors the original client `computeScore`.
- **Config sections** are exactly `engine`, `ingestion`, `app_settings`. Routers
  reject anything else.
- **Ingestion is best-effort:** failures are captured per-source in `meta.errors`
  and never abort the run. Reddit commonly returns 403 (needs OAuth from server
  IPs); HN uses a 7-day recency filter so niche queries may return 0 — both are
  expected, not bugs.
- **Persistence is the headline feature** over the original (which was ephemeral).
  Don't add in-memory-only state that should survive restarts; put it in SQLite.

## Auth

Optional shared password via `SCOUT_PASSWORD`. Unset = fully open. When set,
`/api/auth/login` issues a signed cookie (`itsdangerous`); the main API router
requires it. `/api/auth/*` and static assets stay public.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `SCOUT_PASSWORD` | _(unset)_ | Shared password; unset = open access |
| `ANTHROPIC_API_KEY` | _(unset)_ | Live generation; unset = template fallback |
| `ANTHROPIC_MODEL` | `claude-opus-4-5` | Claude model |
| `SECRET_KEY` | _(random/process)_ | Signs session cookies; set for stable logins |
| `DATA_DIR` | `/data` (`./data` local) | SQLite location |
| `STATIC_DIR` | `/app/static` | Built front-end location |

## Before you finish a change

- Run `TZ=UTC python -m pytest -q` in `backend/` — all green.
- If you touched `engine/`, regenerate + re-verify parity (above).
- If you touched the API contract, update `frontend/lib/api.ts` and
  `frontend/lib/types.ts` to match.
- Rebuild the frontend (`npm run build`) if you changed it; the backend serves
  `frontend/out`.
