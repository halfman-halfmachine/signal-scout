# Signal Scout

Self-hostable, niche-agnostic **market-signal intelligence + content engine**.

Signal Scout ingests items from public sources (Hacker News, Reddit, arXiv,
analyst/competitor/news RSS, Google News), scores each one through a 12-layer
intelligence engine, routes the high-value signals into a review queue, and turns
any signal into structured content (LinkedIn posts, video scripts, podcast
outlines, and more) across 14 narrative frameworks.

It ships as a **single Docker image**: a FastAPI backend that serves both the API
and a Next.js front-end from one origin, with embedded SQLite for persistence. No
external database, no cloud lock-in.

> Originally a Hakkoda-tuned Cloudflare Worker, rebuilt as an open, self-hostable
> app. The engine is **config-driven** — the domain terms, sources, thought
> leaders, competitors, weights, and thresholds are all editable in the UI, so the
> same engine works for any niche, not just enterprise AI/data.

## Quickstart

```bash
cp .env.example .env        # optional: set SCOUT_PASSWORD / ANTHROPIC_API_KEY
docker compose up -d
open http://localhost:8000
```

`docker compose up` pulls the prebuilt multi-arch image from GHCR (amd64 + arm64).
Your queue, learned engine state, config, and generated outputs persist in
`./data` (a mounted volume), so they survive restarts.

### Build from source

```bash
docker compose up -d --build
```

## Configuration

All settings are optional environment variables (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `SCOUT_PASSWORD` | _(unset)_ | Shared password. Unset = open access; set = login required. |
| `ANTHROPIC_API_KEY` | _(unset)_ | Enables live LLM generation. Unset = structured template fallback. The key stays server-side. |
| `ANTHROPIC_MODEL` | `claude-opus-4-5` | Claude model used for generation. |
| `SECRET_KEY` | _(random)_ | Signs session cookies. Set a stable value to keep logins valid across restarts. |
| `DATA_DIR` | `/data` | Where the SQLite database lives (the mounted volume). |
| `PORT` | `8000` | Host port to expose. |

## Retuning for your niche

Signal Scout ships seeded for enterprise AI / data engineering, but nothing is
hardcoded. In the UI:

- **Ingestion Config** — point the sources (HN queries, subreddits, RSS feeds) at
  your domain.
- **Engine / Config** — edit `domain_terms`, `thought_leaders`, `competitors`,
  source-trust seeds, the conference calendar, scoring weights, and routing
  thresholds.
- **Lenses** — define keyword lenses to bias scoring toward sub-topics.

Changes are stored in SQLite and take effect on the next ingest — no code changes,
no redeploy.

## How it works

```
Sources ──> Ingestion ──> 12-layer engine ──> Signal Queue ──> Generation
 (HN, RSS,   (httpx +      (emergence,         (scored,         (Claude or
  Reddit,     feedparser)   authority,          tiered:          template)
  arXiv,                    velocity, hype       IMMEDIATE/
  Google)                   cycle, ...)          ROUTE/DIGEST/LOG)
```

- **Thick server / thin client.** All logic and secrets live server-side; the
  front-end is pure presentation calling `/api`.
- **Persistence.** Embedded SQLite under `DATA_DIR`: the queue, the engine's
  adaptive learned state (source trust, concept history, etc.), config, and output
  history.
- **Adaptive.** Routing/dismissing signals feeds back into per-source trust.

## Local development

Backend:

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
TZ=UTC python -m pytest -q          # run the test suite (incl. engine parity)
DATA_DIR=./data uvicorn app.main:app --reload --port 8000
```

Front-end:

```bash
cd frontend
npm install
npm run dev                          # dev server (proxy /api to the backend)
npm run build                        # static export -> frontend/out
```

### Engine parity

The Python engine is a faithful port of the original `intelligence-engine.js`.
`backend/tests/test_engine_parity.py` asserts identical scores, tiers, and ranking
against golden values generated from the original JS:

```bash
cd backend
TZ=UTC node tests/parity/gen_golden.mjs > tests/parity/golden.json
TZ=UTC python -m pytest tests/test_engine_parity.py -q
```

## Running behind a reverse proxy (TLS)

Signal Scout serves plain HTTP on port 8000. For public deployment, terminate TLS
at a reverse proxy. Example Caddy config:

```
scout.example.com {
    reverse_proxy localhost:8000
}
```

Or with nginx, proxy `https://scout.example.com` to `http://127.0.0.1:8000` and
forward cookies (the session cookie is `SameSite=Lax`, HttpOnly). Always set
`SCOUT_PASSWORD` when exposing the app publicly.

## License

Open source. See repository for details.
