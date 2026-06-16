"""Pure helpers ported from intelligence-engine.js (utilities section).

Kept dependency-free and deterministic so the parity tests can pin exact values.
"""
from __future__ import annotations

import math
import re
from typing import Iterable

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "as", "is", "are", "was", "were", "be", "been", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "this", "that", "it", "its",
    "we", "you", "he", "she", "they", "our", "your", "their", "i", "me", "my",
}

_NON_ALNUM = re.compile(r"[^a-z0-9\s]")
_WS = re.compile(r"\s+")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|[\n]+")
_QUESTION_START = re.compile(
    r"^(what|why|how|when|where|who|which|can|could|should|is|are|do|does|will|would)\b",
    re.IGNORECASE,
)

_POS = ["breakthrough", "revolutionary", "transformative", "success", "growth",
        "adoption", "improve", "opportunity", "innovative", "leader", "efficient"]
_NEG = ["fail", "failure", "hype", "overhyped", "broken", "risk", "struggle",
        "concern", "disappointment", "unreliable", "bias", "problem", "challenge"]


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def normalize(v: float, lo: float, hi: float) -> float:
    return 0.0 if hi == lo else clamp((v - lo) / (hi - lo))


def tokenize(text: str | None) -> list[str]:
    text = (text or "").lower()
    text = _NON_ALNUM.sub(" ", text)
    return [t for t in _WS.split(text) if len(t) > 2]


def extract_questions(text: str | None) -> list[str]:
    out = []
    for s in _SENT_SPLIT.split(text or ""):
        t = s.strip()
        if t.endswith("?") or _QUESTION_START.match(t):
            t = t.strip()
            if len(t) > 10:
                out.append(t)
    return out


def question_fingerprint(question: str) -> str:
    toks = sorted(t for t in tokenize(question) if t not in STOPWORDS)
    return "|".join(toks[:8])


def jaccard_sim(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    inter = len(sa & sb)
    union = len(sa) + len(sb) - inter
    return 0.0 if union == 0 else inter / union


def simple_sentiment(text: str | None) -> float:
    tokens = tokenize(text)
    pos = sum(1 for t in tokens if any(p in t for p in _POS))
    neg = sum(1 for t in tokens if any(n in t for n in _NEG))
    total = (pos + neg) or 1
    return (pos - neg) / total


def js_round(x: float) -> int:
    """Round half *up* to match JavaScript Math.round (Python's round is banker's)."""
    return math.floor(x + 0.5)


def log2_eng_weight(points: float) -> int:
    """Engagement weight: max(1, round(log2(1 + points))) — matches the JS log2 scale."""
    return max(1, js_round(math.log2(1 + points)))
