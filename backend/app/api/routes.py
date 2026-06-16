"""Main API router: config, signals/queue, ingestion, feedback, generate, topics.

All routes here require auth when SCOUT_PASSWORD is set (via the router-level
dependency). The auth router itself stays public.
"""
from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import services
from ..auth import require_auth
from ..engine.manual import score_from_layers
from ..ingestion.sources import ingest as run_ingest
from ..llm import client as llm
from ..storage import database as db
from .schemas import (
    ConfigUpdate, FeedbackRequest, FlagUpdate, GenerateRequest,
    ManualSignal, ScorePreviewRequest,
)

router = APIRouter(prefix="/api", tags=["api"], dependencies=[Depends(require_auth)])

CONFIG_SECTIONS = {"engine", "ingestion", "app_settings"}


# ── Config ───────────────────────────────────────────────────────────────────

@router.get("/config/{section}")
def get_config(section: str) -> dict:
    if section not in CONFIG_SECTIONS:
        raise HTTPException(404, f"Unknown config section: {section}")
    return db.get_config(section)


@router.put("/config/{section}")
def put_config(section: str, body: ConfigUpdate) -> dict:
    if section not in CONFIG_SECTIONS:
        raise HTTPException(404, f"Unknown config section: {section}")
    db.set_config(section, body.data)
    return {"ok": True, "section": section}


# ── Topics (ingestion presets) ───────────────────────────────────────────────

@router.get("/topics")
def topics() -> dict:
    presets = (db.get_config("ingestion") or {}).get("presets", {})
    return {"topics": [{"key": k, "label": p.get("label", k)} for k, p in presets.items()]}


# ── Ingestion (live fetch + score + persist) ─────────────────────────────────

@router.post("/ingest")
async def ingest(topic: str | None = Query(default=None)) -> dict:
    ingestion_cfg = db.get_config("ingestion")
    engine_cfg = db.get_config("engine")
    result = await run_ingest(ingestion_cfg, engine_cfg, topic=topic)
    scored = services.score_and_persist(result["raw"], origin="automated")
    return {
        "signals": [_queue_view(s) for s in scored],
        "meta": {**result["meta"], "count": len(scored), "timestamp": int(time.time() * 1000)},
    }


# ── Queue (persisted signals) ─────────────────────────────────────────────────

@router.get("/signals")
def list_signals(
    include_dismissed: bool = Query(default=False),
    min_score: float | None = Query(default=None),
    limit: int = Query(default=200, le=1000),
) -> dict:
    signals = db.list_signals(include_dismissed=include_dismissed, min_score=min_score, limit=limit)
    return {"signals": [_queue_view(s) for s in signals], "count": len(signals)}


@router.post("/signals")
def add_manual_signal(body: ManualSignal) -> dict:
    cfg = db.get_config("engine")
    layers = body.layers or {}
    result = score_from_layers(layers, cfg)
    sid = body.id or f"manual-{uuid.uuid4().hex[:12]}"
    payload = {
        "id": sid, "title": body.title, "url": body.url, "author": body.author,
        "source": {"name": body.org or body.platform, "domain": body.domain, "platform": body.platform},
        "platform": body.platform, "domain": body.domain, "org": body.org,
        "text": body.text, "talking_points": body.talking_points,
        "layers": layers, "timestamp": int(time.time() * 1000),
        "scores": {"final": result["score"]},
        "routing": {"tier": result["tier"]},
        "formula": result["formula"], "kept": body.kept,
    }
    db.upsert_signal(payload, origin="manual")
    return {"ok": True, "signal": _queue_view(db.get_signal(sid))}


@router.patch("/signals/{sid}")
def update_signal(sid: str, body: FlagUpdate) -> dict:
    ok = db.update_signal_flags(sid, kept=body.kept, dismissed=body.dismissed)
    if not ok:
        raise HTTPException(404, "Signal not found")
    return {"ok": True, "signal": _queue_view(db.get_signal(sid))}


@router.delete("/signals/{sid}")
def delete_signal(sid: str) -> dict:
    if not db.delete_signal(sid):
        raise HTTPException(404, "Signal not found")
    return {"ok": True}


# ── Score preview (Engine tab live slider re-score) ──────────────────────────

@router.post("/score-preview")
def score_preview(body: ScorePreviewRequest) -> dict:
    return score_from_layers(body.layers, db.get_config("engine"))


# ── Feedback (adaptive source trust) ─────────────────────────────────────────

@router.post("/feedback")
def feedback(body: FeedbackRequest) -> dict:
    domain = body.domain
    if not domain and body.signal_id:
        sig = db.get_signal(body.signal_id)
        domain = (sig or {}).get("source", {}).get("domain") if sig else None
    if not domain:
        raise HTTPException(400, "domain or a resolvable signal_id is required")
    domain = domain.lower().lstrip("www.")
    trust = services.apply_feedback(domain, body.was_valuable)
    return {"ok": True, "domain": domain, "was_valuable": body.was_valuable, "source_trust": trust}


# ── Generation ────────────────────────────────────────────────────────────────

@router.post("/generate")
async def generate(body: GenerateRequest) -> dict:
    ctx = services.resolve_generate_context(body.model_dump())
    output_types = body.output_types or ["social-post"]
    outputs = []
    try:
        for ot_id in output_types:
            octx = services.ctx_for_output(ctx, ot_id)
            out = await llm.generate_one(octx, ot_id, variant=body.variant)
            db.save_output({
                "id": out["id"], "signal_id": body.signal_id, "output_type": ot_id,
                "framework": out["framework"], "content": out["content"],
                "is_live": out["is_live"], "meta": {"variant": out["variant"]},
            })
            outputs.append(out)
    except RuntimeError as e:
        raise HTTPException(502, f"Generation failed: {e}")
    return {"outputs": outputs}


@router.get("/outputs")
def outputs(limit: int = Query(default=100, le=500)) -> dict:
    return {"outputs": db.list_outputs(limit=limit)}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _queue_view(s: dict) -> dict:
    scores = s.get("scores", {})
    return {
        "id": s.get("id"),
        "title": s.get("title"),
        "url": s.get("url", ""),
        "author": (s.get("author", {}) or {}).get("name") if isinstance(s.get("author"), dict) else s.get("author", ""),
        "source": (s.get("source", {}) or {}).get("name", "") if isinstance(s.get("source"), dict) else s.get("source", ""),
        "domain": s.get("domain") or (s.get("source", {}) or {}).get("domain", ""),
        "platform": s.get("platform") or (s.get("source", {}) or {}).get("platform", ""),
        "score": scores.get("final", s.get("score", 0)),
        "tier": (s.get("routing", {}) or {}).get("tier", s.get("tier", "LOG")),
        "topics": s.get("topics", []),
        "text": s.get("text", ""),
        "talking_points": s.get("talking_points", ""),
        "layers": s.get("layers", {}),
        "kept": s.get("kept", False),
        "dismissed": s.get("dismissed", False),
        "origin": s.get("origin", "automated"),
        "scores": scores,
        "timestamp": s.get("timestamp"),
    }
