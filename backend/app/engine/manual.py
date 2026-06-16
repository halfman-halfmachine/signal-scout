"""Manual / slider-driven scoring — ported from ssc-app.js computeScore().

The Engine tab and manually-added queue items score directly from raw layer
values (the sliders) rather than from content. This mirrors the original client
formula exactly, including the L2 override flooring at 0.80 when final >= 0.60
(note: distinct from the content engine's 0.90 thought-leader floor).
"""
from __future__ import annotations

from typing import Any


def score_from_layers(layers: dict, cfg: dict) -> dict:
    L = layers
    if L.get("l11"):
        return {"score": 0.0, "tier": "LOG", "formula": "L11 Noise Filter active -> score zeroed out."}

    l1 = _num(L.get("l1"))
    l3 = _num(L.get("l3"))
    l4 = _num(L.get("l4"))
    l5 = _num(L.get("l5"))
    l6 = _num(L.get("l6"), 1.0)
    l7 = _num(L.get("l7"))
    l8 = _num(L.get("l8"))
    l9 = _num(L.get("l9"), 1.0)
    l10 = _num(L.get("l10"))
    l12 = _num(L.get("l12"), 1.0)

    w = cfg["scoring_weights"]
    t = cfg["routing_thresholds"]

    eI = l1 * w["ei_l1"] + l4 * w["ei_l4"]
    rI = l10 * w["ri_l10"] + l5 * w["ri_l5"]
    base = (eI * w["emergence_position"] + rI * w["relevance_depth"]
            + l7 * w["source_authority"] + l3 * w["question_gap_bonus"] + l8 * w["velocity_trajectory"])
    fin = base * l6 * l9 * l12

    if L.get("l2") and fin >= 0.60:
        fin = max(fin, 0.80)
    fin = min(fin, 1.0)

    tier = ("IMMEDIATE" if fin >= t["IMMEDIATE"]
            else "ROUTE" if fin >= t["ROUTE"]
            else "DIGEST" if fin >= t["DIGEST"] else "LOG")

    formula = (
        f"emergenceIn = {eI:.3f}  (L1x{w['ei_l1']} + L4x{w['ei_l4']})\n"
        f"relevanceIn = {rI:.3f}  (L10x{w['ri_l10']} + L5x{w['ri_l5']})\n"
        f"base        = {base:.3f}  (eIx{w['emergence_position']} + rIx{w['relevance_depth']} "
        f"+ L7x{w['source_authority']} + L3x{w['question_gap_bonus']} + L8x{w['velocity_trajectory']})\n"
        f"final       = {fin:.3f}  (base x L6:{l6} x L9:{l9} x L12:{l12})"
        + ("\n[L2 override applied: boosted to 0.80+ floor]" if (L.get("l2") and fin >= 0.80) else "")
    )
    return {"score": fin, "tier": tier, "formula": formula}


def _num(v: Any, default: float = 0.0) -> float:
    try:
        n = float(v)
        return n if n else default
    except (TypeError, ValueError):
        return default
