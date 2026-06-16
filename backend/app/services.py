"""Service helpers bridging the API routers, the engine, and storage.

Centralizes engine construction (config + learned state from SQLite) and the
resolution of a generate-request payload into the ctx dict the llm module wants.
"""
from __future__ import annotations

from typing import Any

from .engine.engine import IntelligenceEngine
from .storage import database as db


def build_engine() -> IntelligenceEngine:
    return IntelligenceEngine(
        initial_state=db.load_learned_state(),
        config=db.get_config("engine"),
    )


def score_and_persist(raw_signals: list[dict], origin: str = "automated") -> list[dict]:
    """Run signals through the engine, persist learned state + the scored signals."""
    engine = build_engine()
    scored = engine.process_batch(raw_signals)
    db.save_learned_state(engine.export_state())
    for s in scored:
        db.upsert_signal(s, origin=origin)
    return scored


def apply_feedback(domain: str, was_valuable: bool) -> dict | None:
    """Update adaptive source trust for a domain and persist learned state."""
    from .engine import layers as L
    engine = build_engine()
    L.update_source_trust(domain, was_valuable, engine.store, engine.cfg)
    db.save_learned_state(engine.export_state())
    key = domain.lower().lstrip("www.")
    return engine.store.get("sourceTrust").get(key)


def resolve_generate_context(payload: dict) -> dict:
    """Build the llm ctx dict from a request payload + app_settings config.

    The frontend sends selection ids + signal fields; the server resolves the
    actual framework beats, output-type names, persona/POV/lens objects from the
    config so generation stays config-driven and the client stays thin.
    """
    app_settings = db.get_config("app_settings")
    frameworks = {f["id"]: f for f in app_settings.get("frameworks", [])}
    output_types = {o["id"]: o for o in app_settings.get("output_types", [])}
    lenses = {l["id"]: l for l in app_settings.get("lenses", [])}
    input_modes = {m["id"]: m for m in app_settings.get("input_modes", [])}
    personas = {p["id"]: p for p in app_settings.get("personas", [])}
    pov_options = {p["id"]: p for p in app_settings.get("pov_options", [])}

    fw = frameworks.get(payload.get("framework_id")) or next(iter(frameworks.values()), {"name": "SPARK", "beats": ["Signal"]})

    active_lens_ids = payload.get("active_lens_ids") or []
    active_lenses = [lenses[i] for i in active_lens_ids if i in lenses]

    im = input_modes.get(payload.get("input_mode_id"))
    ctx_personas = [personas[i] for i in (payload.get("persona_ids") or []) if i in personas]
    ctx_povs = [pov_options[i] for i in (payload.get("pov_ids") or []) if i in pov_options and i != "custom"]

    return {
        "signal": payload.get("signal", {}),
        "framework": fw,
        "output_types_resolved": output_types,
        "social_platform": payload.get("social_platform") or "linkedin",
        "score": payload.get("score", 0),
        "tier": payload.get("tier", "LOG"),
        "layers": payload.get("layers", {}),
        "active_lenses": active_lenses,
        "input_mode": im,
        "personas": ctx_personas,
        "povs": ctx_povs,
        "pov_custom": payload.get("pov_custom", ""),
        "web_research": bool(payload.get("web_research")),
    }


def ctx_for_output(ctx: dict, output_type_id: str) -> dict:
    """Attach the resolved output_type for a specific id."""
    ot = ctx.get("output_types_resolved", {}).get(output_type_id) or {"id": output_type_id, "name": output_type_id}
    return {**ctx, "output_type": ot}
