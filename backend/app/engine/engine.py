"""IntelligenceEngine orchestrator — ported from intelligence-engine.js.

Runs a signal through all 12 layers, applies the weighted scoring formula and
post-formula multipliers, and returns a ScoredSignal. The engine is config-driven:
the niche constants live in `cfg` (seeded from defaults, editable in the UI) and
the learned accumulator state lives in the StateStore (persisted to SQLite).
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from . import layers as L
from .defaults import default_engine_config
from .utils import clamp

LEARNED_KEYS = [
    "conceptHistory", "questionClusters", "sourceTrust",
    "topicSentiment", "competitorCoverage", "platformTopicWindow",
]

STAGE_RANK = {"emergence": 3, "pre-emergence": 2, "mainstream": 1, "saturated": 0, "unknown": 0}


class StateStore:
    """Holds the 6 accumulator maps. snapshot()/restore() mirror the JS API."""

    def __init__(self, initial: dict | None = None):
        self._data: dict[str, Any] = {k: {} for k in LEARNED_KEYS}
        if initial:
            for k in LEARNED_KEYS:
                if k in initial and initial[k] is not None:
                    self._data[k] = initial[k]

    def get(self, key: str) -> Any:
        return self._data[key]

    def set(self, key: str, val: Any) -> None:
        self._data[key] = val

    def snapshot(self) -> dict[str, Any]:
        import copy
        return copy.deepcopy(self._data)

    def restore(self, snap: dict[str, Any]) -> None:
        self._data = {k: snap.get(k, {}) for k in LEARNED_KEYS}


def compute_score(inputs: dict, cfg: dict) -> dict:
    w = cfg["scoring_weights"]
    base = (
        inputs["emergenceInput"] * w["emergence_position"]
        + inputs["relevanceInput"] * w["relevance_depth"]
        + inputs["sourceAuthority"] * w["source_authority"]
        + inputs["questionGapBonus"] * w["question_gap_bonus"]
        + inputs["velocityTrajectory"] * w["velocity_trajectory"]
    )
    return {"base": clamp(base)}


def route_signal(final_score: float, cfg: dict) -> dict:
    t = cfg["routing_thresholds"]
    if final_score >= t["IMMEDIATE"]:
        return {"tier": "IMMEDIATE", "action": "Talk track within 24h", "priority": "P0", "sla": "24h"}
    if final_score >= t["ROUTE"]:
        return {"tier": "ROUTE", "action": "Route for talk track generation", "priority": "P1", "sla": "72h"}
    if final_score >= t["DIGEST"]:
        return {"tier": "DIGEST", "action": "Include in weekly digest", "priority": "P2", "sla": "7d"}
    return {"tier": "LOG", "action": "Logged, not surfaced", "priority": "P3", "sla": None}


def rank_signals(scored: list[dict]) -> list[dict]:
    import functools

    # Replicate the JS comparator exactly: a final-score gap under 0.01 is a tie
    # and falls through to stage rank, thought-leader tier, then recency.
    def cmp(a: dict, b: dict) -> int:
        sa, sb = a["scores"], b["scores"]
        score_diff = sb["final"] - sa["final"]
        if abs(score_diff) > 0.01:
            return -1 if score_diff < 0 else 1
        stage_diff = STAGE_RANK.get(sb.get("emergenceStage"), 0) - STAGE_RANK.get(sa.get("emergenceStage"), 0)
        if stage_diff != 0:
            return stage_diff
        tl_a = sa.get("thoughtLeaderTier") if sa.get("thoughtLeaderTier") is not None else 99
        tl_b = sb.get("thoughtLeaderTier") if sb.get("thoughtLeaderTier") is not None else 99
        if tl_a != tl_b:
            return tl_a - tl_b
        return b.get("timestamp", 0) - a.get("timestamp", 0)

    return sorted(scored, key=functools.cmp_to_key(cmp))


class IntelligenceEngine:
    def __init__(self, initial_state: dict | None = None, config: dict | None = None):
        self.store = StateStore(initial_state or {})
        self.cfg = config or default_engine_config()

    def process(self, signal: dict, now_ms: float | None = None) -> dict:
        now_ms = now_ms if now_ms is not None else time.time() * 1000
        s = dict(signal)
        s.setdefault("timestamp", now_ms)
        s.setdefault("id", uuid.uuid4().hex)
        cfg = self.cfg
        trace = []

        l1 = L.detect_emergence(s, self.store, cfg)
        trace.append({"layer": 1, "name": "Emergence Detection", "score": l1["score"], "meta": {"stage": l1["stage"]}})
        l2 = L.check_thought_leader(s, cfg)
        trace.append({"layer": 2, "name": "Thought Leader Watchlist", "score": l2["weight"], "meta": {"tier": l2["tier"], "matched": l2["matched"]}})
        l3 = L.detect_question_gaps(s, self.store, cfg)
        trace.append({"layer": 3, "name": "Question Gap Detector", "score": l3["score"], "meta": {"questions": len(l3["questions"])}})
        l4 = L.measure_divergence(s, self.store, cfg)
        trace.append({"layer": 4, "name": "Practitioner/Analyst Divergence", "score": l4["score"], "meta": {"sourceType": l4["sourceType"]}})
        l5 = L.score_competitive_gap(s, self.store, cfg)
        trace.append({"layer": 5, "name": "Competitive Gap Intelligence", "score": l5["score"]})
        l6 = L.get_temporal_multiplier(s, cfg)
        trace.append({"layer": 6, "name": "Temporal Intelligence", "score": l6["multiplier"], "meta": {"reasons": l6["reasons"]}})
        l7 = L.get_source_trust(s, self.store, cfg)
        trace.append({"layer": 7, "name": "Source Trust", "score": l7["score"], "meta": {"domain": l7["domain"]}})
        l8 = L.score_engagement_velocity(s, cfg, now_ms)
        trace.append({"layer": 8, "name": "Engagement Velocity", "score": l8["score"], "meta": {"platform": l8["platform"]}})
        l9 = L.measure_cross_platform_heat(s, self.store, cfg)
        trace.append({"layer": 9, "name": "Cross-Platform Heat", "score": l9["multiplier"], "meta": {"platforms": l9["platformCount"]}})
        l10 = L.score_relevance_depth(s, cfg)
        trace.append({"layer": 10, "name": "Keywords", "score": l10})
        l11 = L.detect_noise(s, self.store, cfg)
        trace.append({"layer": 11, "name": "Noise Filter", "score": 0 if l11["isNoise"] else 1, "meta": {"reasons": l11["reasons"]}})
        l12 = L.detect_hype_cycle_phase(s, self.store, cfg)
        trace.append({"layer": 12, "name": "Hype Cycle Position", "score": l12["multiplier"], "meta": {"phase": l12["phase"], "confidence": l12["confidence"]}})

        w = cfg["scoring_weights"]
        emergence_input = clamp(l1["score"] * w["ei_l1"] + l4["score"] * w["ei_l4"])
        relevance_input = clamp(l10 * w["ri_l10"] + l5["score"] * w["ri_l5"])

        scoring = compute_score({
            "emergenceInput": emergence_input,
            "relevanceInput": relevance_input,
            "sourceAuthority": l7["score"],
            "questionGapBonus": l3["score"],
            "velocityTrajectory": l8["score"],
        }, cfg)

        score = scoring["base"] * l6["multiplier"] * l9["multiplier"] * l12["multiplier"]
        if l2["elevate"]:
            score = max(score, 0.90)
        if l11["isNoise"]:
            score = 0

        final = clamp(score)
        routing = route_signal(final, cfg)

        return {
            **s,
            "scores": {
                "emergencePosition": l1["score"],
                "emergenceStage": l1["stage"],
                "thoughtLeaderBoost": l2["weight"],
                "thoughtLeaderTier": l2["tier"],
                "questionGapBonus": l3["score"],
                "divergenceScore": l4["score"],
                "competitiveGap": l5["score"],
                "temporalMultiplier": l6["multiplier"],
                "sourceAuthority": l7["score"],
                "engagementVelocity": l8["score"],
                "crossPlatformHeat": l9["multiplier"],
                "keywords": l10,
                "noiseFilter": l11["isNoise"],
                "hypeCyclePhase": l12["phase"],
                "hypeCycleMultiplier": l12["multiplier"],
                "emergenceInput": emergence_input,
                "relevanceInput": relevance_input,
                "base": scoring["base"],
                "final": final,
            },
            "routing": routing,
            "enrichment": {
                "emergenceTopics": l1["topics"],
                "gapQuestions": l3["questions"],
                "divergentTopics": l4["divergentTopics"],
                "competitorGaps": l5["topics"],
                "temporalReasons": l6["reasons"],
                "hotTopics": l9["hotTopics"],
                "noiseReasons": l11["reasons"],
                "hypeCycleSignals": l12["signals"],
            },
            "layerTrace": trace,
        }

    def process_batch(self, signals: list[dict], now_ms: float | None = None) -> list[dict]:
        return rank_signals([self.process(s, now_ms) for s in signals])

    def feedback(self, signal_id: str, scored: list[dict], was_valuable: bool) -> bool:
        signal = next((s for s in scored if s.get("id") == signal_id), None)
        domain = (signal or {}).get("source", {}).get("domain") if signal else None
        if not domain:
            return False
        L.update_source_trust(domain, was_valuable, self.store, self.cfg)
        return True

    def export_state(self) -> dict:
        return self.store.snapshot()

    def import_state(self, snapshot: dict) -> None:
        self.store.restore(snapshot)
