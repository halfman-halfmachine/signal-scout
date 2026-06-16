"""Engine parity test — the key correctness gate for the JS→Python port.

Loads golden values produced by the original intelligence-engine.js
(tests/parity/golden.json) and asserts the Python engine reproduces the same
final scores, tiers, ranking order, and per-layer sub-scores for identical
fixtures with a frozen clock.

Regenerate golden values with:
    TZ=UTC node tests/parity/gen_golden.mjs > tests/parity/golden.json
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.engine.engine import IntelligenceEngine

from parity.reference_config import reference_engine_config

GOLDEN = json.loads((Path(__file__).parent / "parity" / "golden.json").read_text())


def _ts(y: int, m: int, d: int) -> int:
    return int(datetime(y, m, d, 12, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)


# Fixtures must match tests/parity/gen_golden.mjs exactly.
FIXTURES = [
    {
        "id": "fx-tl", "title": "Andrej Karpathy on small models and big context",
        "body": "Why do most enterprise AI budgets go to model size instead of the context layer? How should teams rebalance?",
        "author": {"name": "Andrej Karpathy", "handle": "@karpathy"},
        "source": {"name": "Twitter", "domain": "twitter.com", "type": "social", "platform": "twitter"},
        "engagement": {"platform": "twitter", "reactions": 1200, "comments": 300, "shares": 150},
        "topics": ["agentic ai", "frugal ai", "context layer"], "timestamp": _ts(2026, 6, 10),
    },
    {
        "id": "fx-snowflake", "title": "Snowflake Cortex adds context engineering for enterprise AI agents",
        "body": "Snowflake announced governed data context for agents, framed as context engineering between raw data and agent reasoning.",
        "author": {"name": "Snowflake Newsroom", "handle": ""},
        "source": {"name": "Snowflake", "domain": "snowflake.com", "type": "press", "platform": "press"},
        "engagement": {"platform": "blog", "reactions": 40, "comments": 8, "shares": 5},
        "topics": ["data engineering", "snowflake", "enterprise ai"], "timestamp": _ts(2026, 6, 9),
    },
    {
        "id": "fx-hn", "title": "Show HN: cutting LLM inference cost with small language models",
        "body": "A practical tutorial on deploying quantized small language models in production. Lessons learned building a lean RAG pipeline.",
        "author": {"name": "devuser", "handle": "@devuser"},
        "source": {"name": "Hacker News", "domain": "news.ycombinator.com", "type": "tech_community", "platform": "hn"},
        "engagement": {"platform": "hn", "reactions": 220, "comments": 95, "shares": 0},
        "topics": ["frugal ai", "small language model", "rag", "llm"], "timestamp": _ts(2026, 6, 12),
    },
    {
        "id": "fx-noise", "title": "For immediate release: Vendor announces AI-powered dashboard",
        "body": "Sponsored. We are pleased to announce a revolutionary new dashboard.",
        "author": {"name": "Vendor PR", "handle": ""},
        "source": {"name": "Example Vendor", "domain": "example-vendor.com", "type": "press", "platform": "news"},
        "engagement": {"platform": "news", "reactions": 2, "comments": 0, "shares": 0},
        "topics": [], "timestamp": _ts(2026, 6, 11),
    },
    {
        "id": "fx-analyst", "title": "McKinsey: enterprise AI adoption accelerates across data platforms",
        "body": "Analysts report strong growth and opportunity in enterprise AI and data governance investments.",
        "author": {"name": "McKinsey & Company", "handle": ""},
        "source": {"name": "McKinsey & Company", "domain": "mckinsey.com", "type": "competitor", "platform": "blog"},
        "engagement": {"platform": "blog", "reactions": 30, "comments": 4, "shares": 10},
        "topics": ["enterprise ai", "data governance"], "timestamp": _ts(2026, 6, 8),
    },
]

NUMERIC_FIELDS = [
    "final", "base", "emergencePosition", "relevanceInput", "emergenceInput",
    "sourceAuthority", "questionGapBonus", "engagementVelocity", "keywords",
    "divergenceScore", "competitiveGap", "temporalMultiplier", "crossPlatformHeat",
    "hypeCycleMultiplier",
]
EXACT_FIELDS = ["tier_via_routing", "emergenceStage", "hypeCyclePhase", "thoughtLeaderTier", "noiseFilter"]
TOL = 1e-9


def _run():
    # Inject the frozen reference config: production defaults are now blank,
    # so parity must run against the Hakkoda config golden.json was built from.
    engine = IntelligenceEngine(config=reference_engine_config())
    return engine.process_batch(FIXTURES, now_ms=GOLDEN["now"])


def test_ranking_order_matches():
    scored = _run()
    assert [s["id"] for s in scored] == GOLDEN["order"]


def test_per_signal_scores_match():
    scored = {s["id"]: s for s in _run()}
    golden = {g["id"]: g for g in GOLDEN["signals"]}

    for sid, g in golden.items():
        s = scored[sid]
        sc = s["scores"]
        for field in NUMERIC_FIELDS:
            assert abs(sc[field] - g[field]) < TOL, f"{sid}.{field}: {sc[field]} != {g[field]}"
        assert s["routing"]["tier"] == g["tier"], f"{sid} tier"
        assert sc["emergenceStage"] == g["emergenceStage"], f"{sid} stage"
        assert sc["hypeCyclePhase"] == g["hypeCyclePhase"], f"{sid} hype phase"
        assert sc["thoughtLeaderTier"] == g["thoughtLeaderTier"], f"{sid} TL tier"
        assert sc["noiseFilter"] == g["noiseFilter"], f"{sid} noise"


def test_noise_signal_zeroed():
    scored = {s["id"]: s for s in _run()}
    assert scored["fx-noise"]["scores"]["final"] == 0
    assert scored["fx-noise"]["routing"]["tier"] == "LOG"


def test_thought_leader_floor():
    scored = {s["id"]: s for s in _run()}
    assert scored["fx-tl"]["scores"]["final"] >= 0.90
