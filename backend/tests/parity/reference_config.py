"""Frozen reference engine config for parity + ingestion tests.

This is the original Hakkoda-tuned engine config that the vendored
`reference_engine.mjs` bakes in as JS constants, and that `golden.json` is
generated from. The production `engine/defaults.py` has since been blanked to
ship niche-agnostic, so the parity gate can no longer rely on it. Tests that
must reproduce the reference engine's behavior inject this config explicitly.

Keep this in sync with `reference_engine.mjs` ONLY — never with the (blank)
production defaults. If parity drifts, the port diverged; fix the port.
"""
from __future__ import annotations

import copy
from typing import Any

REFERENCE_ENGINE_CONFIG: dict[str, Any] = {
    # ── Layer 2: Thought Leader Watchlist ──────────────────────────────────
    "thought_leaders": {
        "tier0": {
            "weight": 0.97,
            "names": ["andrej karpathy", "karpathy", "andrew ng", "andrewng",
                      "jensen huang", "sam altman", "samaltman", "demis hassabis"],
            "handles": ["@karpathy", "@andrewng", "@jensenh", "@sama", "@demishassabis"],
        },
        "tier1": {
            "weight": 0.92,
            "names": ["ibm research", "snowflake", "databricks", "anthropic", "openai", "caroline roche"],
            "domains": ["research.ibm.com", "snowflake.com", "databricks.com",
                        "anthropic.com", "openai.com"],
        },
    },

    # ── Layer 4: source classification ─────────────────────────────────────
    "analyst_orgs": [
        "gartner", "forrester", "mckinsey", "idc", "everest group", "hfs research",
        "hbr", "technologyreview", "harvard business review",
    ],
    "practitioner_domains": [
        "news.ycombinator.com", "reddit.com", "stackoverflow.com",
        "medium.com", "substack.com", "dev.to",
    ],

    # ── Layer 5: Competitive Gap ───────────────────────────────────────────
    "competitors": ["accenture", "deloitte", "mckinsey", "bcg", "pwc"],

    # ── Layer 6: Temporal / conference calendar ([month, day], 1-indexed) ──
    "conference_calendar": [
        {"name": "IBM Think",        "start": [5, 5],   "end": [5, 8],   "topics": ["enterprise ai", "cloud", "data", "watson"]},
        {"name": "Google I/O",       "start": [5, 14],  "end": [5, 15],  "topics": ["ai", "ml", "gemini", "vertex"]},
        {"name": "Data+AI Summit",   "start": [6, 9],   "end": [6, 12],  "topics": ["databricks", "spark", "lakehouse", "mlops"]},
        {"name": "Snowflake Summit", "start": [6, 2],   "end": [6, 5],   "topics": ["snowflake", "data cloud", "analytics"]},
        {"name": "Dreamforce",       "start": [9, 16],  "end": [9, 19],  "topics": ["salesforce", "crm", "ai", "data cloud"]},
        {"name": "AWS re:Invent",    "start": [12, 1],  "end": [12, 5],  "topics": ["aws", "cloud", "data engineering"]},
        {"name": "NeurIPS",          "start": [12, 9],  "end": [12, 15], "topics": ["ml", "ai research", "deep learning", "neural"]},
    ],

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

    # ── Layer 7: Source Trust seeds ────────────────────────────────────────
    "source_initial_trust": {
        "hbr.org": 0.88, "mit.edu": 0.90, "stanford.edu": 0.90,
        "nature.com": 0.92, "arxiv.org": 0.85, "acm.org": 0.87,
        "gartner.com": 0.82, "forrester.com": 0.82, "mckinsey.com": 0.80,
        "news.ycombinator.com": 0.76, "reddit.com": 0.62, "medium.com": 0.58,
        "dev.to": 0.60, "substack.com": 0.60,
        "openai.com": 0.88, "anthropic.com": 0.88, "research.ibm.com": 0.87,
        "snowflake.com": 0.80, "databricks.com": 0.80, "deepmind.google": 0.90,
    },

    # ── Layer 10: domain relevance terms ───────────────────────────────────
    "domain_terms": [
        "snowflake", "databricks", "data engineering", "data platform", "lakehouse",
        "data mesh", "data fabric", "mlops", "feature store", "data governance",
        "ai governance", "enterprise ai", "ai implementation", "agentic ai",
        "llm", "rag", "fine-tuning", "prompt engineering", "frugal ai",
        "small language model", "data strategy", "modern data stack", "cloud data",
        "data migration", "dbt", "airflow", "data quality", "observability",
        "data catalog", "metadata management",
    ],
    # Extra terms used only by ingestion topic extraction.
    "tech_terms": [
        "llm", "gpt", "claude", "gemini", "copilot", "agent", "rag", "fine-tun",
        "snowflake", "databricks", "spark", "dbt", "airflow", "kafka",
        "mlops", "feature store", "lakehouse", "medallion architecture",
        "vector", "embedding", "inference", "quantization", "distillation",
        "governance", "compliance", "data mesh", "data fabric",
    ],

    # ── Layer 11: Noise Filter (case-insensitive regex strings) ────────────
    "noise_patterns": [
        r"^(press release|for immediate release|we are pleased|proud to announce|introducing our)",
        r"\b(sponsored|advertisement|advertorial|partner content|paid promotion)\b",
    ],

    # ── Layer 12: Hype Cycle vocab + mainstream domains ────────────────────
    "mainstream_domains": [
        "techcrunch.com", "forbes.com", "businessinsider.com", "wired.com", "theverge.com",
        "venturebeat.com", "wsj.com", "nytimes.com", "zdnet.com", "fortune.com", "bloomberg.com",
    ],
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


def reference_engine_config() -> dict[str, Any]:
    """Return a deep copy so callers can mutate freely."""
    return copy.deepcopy(REFERENCE_ENGINE_CONFIG)
