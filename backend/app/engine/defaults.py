"""Default engine configuration — niche-agnostic blank slate.

The engine reads everything from an injected config dict (see engine.py); this
module supplies only the *defaults* used to seed a fresh install. All niche
specifics (thought leaders, domain terms, competitors, sources, source-trust
seeds, conference calendar) ship **blank** so Signal Scout is domain-agnostic
out of the box — an operator fills them in via the Config tabs.

What is intentionally NOT blank:
  - Mechanical scoring scaffolding (scoring_weights, routing_thresholds,
    queue_threshold, platform_baselines, heat_multipliers) — the engine needs
    these to score at all, and they are domain-independent.
  - Generic, domain-agnostic vocab (noise_patterns, hype/trough/practical/
    plateau hype-cycle words) — useful for any niche, editable in the UI.

Every top-level key is kept present (the engine reads keys with bare access),
just emptied where the value is niche-specific. The original Hakkoda-tuned
values live in tests/parity/reference_config.py for the parity gate.
"""
from __future__ import annotations

import copy
from typing import Any

DEFAULT_ENGINE_CONFIG: dict[str, Any] = {
    # ── Layer 2: Thought Leader Watchlist (names/handles/domains blank) ────
    "thought_leaders": {
        "tier0": {"weight": 0.97, "names": [], "handles": []},
        "tier1": {"weight": 0.92, "names": [], "domains": []},
    },

    # ── Layer 4: source classification ─────────────────────────────────────
    "analyst_orgs": [],
    "practitioner_domains": [],

    # ── Layer 5: Competitive Gap ───────────────────────────────────────────
    "competitors": [],

    # ── Layer 6: Temporal / conference calendar ([month, day], 1-indexed) ──
    "conference_calendar": [],

    # ── Scoring formula weights ────────────────────────────────────────────
    # Base weights (must sum to 1.0) plus the L1/L4 and L10/L5 input splits.
    "scoring_weights": {
        "emergence_position": 0.30,
        "relevance_depth": 0.25,
        "source_authority": 0.20,
        "question_gap_bonus": 0.15,
        "velocity_trajectory": 0.10,
        # emergenceInput = L1 * ei_l1 + L4 * ei_l4
        "ei_l1": 0.60,
        "ei_l4": 0.40,
        # relevanceInput = L10 * ri_l10 + L5 * ri_l5
        "ri_l10": 0.60,
        "ri_l5": 0.40,
    },

    # ── Routing thresholds ─────────────────────────────────────────────────
    "routing_thresholds": {"IMMEDIATE": 0.85, "ROUTE": 0.70, "DIGEST": 0.50},

    # Signals scoring below this are hidden from the Signal Queue.
    "queue_threshold": 0.40,

    # ── Layer 8: Engagement Velocity baselines (per-platform, 24h figures) ─
    "platform_baselines": {
        "linkedin": {"reactions": 150, "comments": 25, "shares": 30},
        "youtube":  {"reactions": 500, "comments": 80, "shares": 50},
        "reddit":   {"reactions": 200, "comments": 60, "shares": 0},
        "hn":       {"reactions": 100, "comments": 40, "shares": 0},
        "twitter":  {"reactions": 300, "comments": 30, "shares": 80},
        "blog":     {"reactions": 50,  "comments": 10, "shares": 20},
        "paper":    {"reactions": 20,  "comments": 5,  "shares": 15},
    },

    # ── Layer 7: Source Trust seeds (blank — add domains in the UI) ─────────
    "source_initial_trust": {},

    # ── Layer 10: domain relevance terms ───────────────────────────────────
    "domain_terms": [],
    # Extra terms used only by ingestion topic extraction.
    "tech_terms": [],

    # ── Layer 11: Noise Filter (generic spam/PR regexes, case-insensitive) ─
    "noise_patterns": [
        r"^(press release|for immediate release|we are pleased|proud to announce|introducing our)",
        r"\b(sponsored|advertisement|advertorial|partner content|paid promotion)\b",
    ],

    # ── Layer 12: Hype Cycle vocab + mainstream domains ────────────────────
    # mainstream_domains is niche (blank); the hype-cycle vocab is generic.
    "mainstream_domains": [],
    "hype_vocab": ["revolutionary", "game-changing", "unprecedented", "disrupts", "breakthrough",
                   "transforms everything", "next big thing", "game changer"],
    "trough_vocab": ["fails", "overhyped", "reality check", "not ready", "limited", "disappointing",
                     "hype died", "struggled", "fell short"],
    "practical_vocab": ["tutorial", "how to", "implementation", "best practice", "case study",
                        "lessons learned", "production", "step by step", "hands-on", "deploying", "building"],
    "plateau_vocab": ["standard", "established", "commodity", "table stakes", "baseline",
                      "widely adopted", "mature", "expected", "de facto"],

    # ── Layer 9: Cross-Platform Heat multipliers (index = platform count) ──
    "heat_multipliers": [1.0, 1.0, 1.30, 1.60, 2.0],
}


def default_engine_config() -> dict[str, Any]:
    """Return a deep copy so callers can mutate freely."""
    return copy.deepcopy(DEFAULT_ENGINE_CONFIG)
