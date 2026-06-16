"""The 12 detection layers, ported from intelligence-engine.js.

Each function takes the signal, the StateStore, and the engine `config` (so the
niche-specific constants are injected rather than hardcoded). Logic is a
faithful translation; only the constants moved into config.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from .utils import (
    clamp, extract_questions, log2_eng_weight, normalize,
    question_fingerprint, simple_sentiment, tokenize,
)

DAY_MS = 86_400_000
HOUR_MS = 3_600_000


def _author_fields(signal: dict) -> tuple[str, str]:
    raw = signal.get("author")
    if isinstance(raw, str):
        return raw.lower(), ""
    raw = raw or {}
    return (raw.get("name") or "").lower(), (raw.get("handle") or "").lower()


def _full_text(signal: dict) -> str:
    return " ".join(x for x in (signal.get("title"), signal.get("body")) if x)


# ── Layer 1 — Emergence Detection ───────────────────────────────────────────

def detect_emergence(signal: dict, store, cfg: dict) -> dict:
    history = store.get("conceptHistory")
    now = signal["timestamp"]
    topics = signal.get("topics") or []

    topic_scores = []
    for topic in topics:
        key = topic.lower().strip()
        history.setdefault(key, [])

        eng = signal.get("engagement") or {}
        eng_pts = (eng.get("reactions") if eng.get("reactions") is not None else eng.get("points") or 0) \
            + (eng.get("comments") or 0)
        eng_weight = log2_eng_weight(eng_pts)
        history[key].append({"ts": now, "count": eng_weight})

        cutoff90 = now - 90 * DAY_MS
        history[key] = [e for e in history[key] if e["ts"] > cutoff90]
        entries = history[key]

        if len(entries) < 3:
            topic_scores.append({"topic": key, "score": 0.62, "stage": "pre-emergence"})
            continue

        midpoint = now - 45 * DAY_MS
        recent = len([e for e in entries if e["ts"] >= midpoint])
        prior = len([e for e in entries if e["ts"] < midpoint]) or 1

        growth_rate = (recent - prior) / prior
        total_hits = sum(e["count"] for e in entries)
        peak_window = max(e["count"] for e in entries)
        saturation = clamp(total_hits / max(peak_window * len(entries), 1))

        if saturation < 0.20 and growth_rate > 0.5:
            stage, score = "pre-emergence", clamp(0.55 + growth_rate * 0.25)
        elif saturation < 0.50 and growth_rate > 0.2:
            stage, score = "emergence", clamp(0.80 + (0.50 - saturation) * 0.40)
        elif saturation < 0.85:
            stage, score = "mainstream", clamp(0.50 - (saturation - 0.50) * 0.60)
        else:
            stage, score = "saturated", 0.15

        topic_scores.append({"topic": key, "score": score, "stage": stage,
                             "growthRate": growth_rate, "saturation": saturation})

    store.set("conceptHistory", history)

    if not topic_scores:
        return {"score": 0.50, "stage": "unknown", "topics": []}

    best = max(topic_scores, key=lambda t: t["score"])
    avg = sum(t["score"] for t in topic_scores) / len(topic_scores)
    return {"score": clamp(best["score"] * 0.60 + avg * 0.40),
            "stage": best["stage"], "topics": topic_scores}


# ── Layer 2 — Thought Leader Watchlist ──────────────────────────────────────

def check_thought_leader(signal: dict, cfg: dict) -> dict:
    tl = cfg["thought_leaders"]
    name, handle = _author_fields(signal)
    src = signal.get("source") or {}
    domain = (src.get("domain") or "").lower()
    org = (src.get("name") or "").lower()

    for n in tl["tier0"]["names"]:
        if n in name or n.replace(" ", "") in handle:
            return {"tier": 0, "weight": tl["tier0"]["weight"], "matched": n, "elevate": True}
    for h in tl["tier0"]["handles"]:
        if handle == h or h.replace("@", "") in handle:
            return {"tier": 0, "weight": tl["tier0"]["weight"], "matched": h, "elevate": True}
    for n in tl["tier1"]["names"]:
        if n in name or n in org:
            return {"tier": 1, "weight": tl["tier1"]["weight"], "matched": n, "elevate": True}
    for d in tl["tier1"]["domains"]:
        if d in domain:
            return {"tier": 1, "weight": tl["tier1"]["weight"], "matched": d, "elevate": True}
    return {"tier": None, "weight": 0, "matched": None, "elevate": False}


# ── Layer 3 — Question Gap Detector ─────────────────────────────────────────

def detect_question_gaps(signal: dict, store, cfg: dict) -> dict:
    clusters = store.get("questionClusters")
    now = signal["timestamp"]
    cutoff7d = now - 7 * DAY_MS
    cutoff48 = now - 48 * HOUR_MS
    questions = extract_questions(_full_text(signal))

    max_gap = 0.0
    detected = []
    platform = (signal.get("source") or {}).get("platform") or "unknown"

    for q in questions:
        fp = question_fingerprint(q)
        if not fp:
            continue
        cluster = clusters.setdefault(fp, {"question": q, "count": 0, "sources": [], "answered": False})
        cluster["count"] += 1
        cluster["sources"].append({"platform": platform, "ts": now})
        cluster["sources"] = [s for s in cluster["sources"] if s["ts"] > cutoff7d]

        unique_platforms = len({s["platform"] for s in cluster["sources"]})
        recent_activity = 1.10 if any(s["ts"] > cutoff48 for s in cluster["sources"]) else 1.0

        freq_score = min(cluster["count"], 10) / 10
        platform_score = min(unique_platforms, 4) / 4
        unanswered = 0 if cluster["answered"] else 0.20
        gap_score = clamp((freq_score * 0.40 + platform_score * 0.40 + unanswered) * recent_activity)

        if gap_score > max_gap:
            max_gap = gap_score
        if gap_score > 0.30:
            detected.append({"question": q, "score": gap_score,
                            "platforms": unique_platforms, "count": cluster["count"]})

    store.set("questionClusters", clusters)
    detected.sort(key=lambda d: d["score"], reverse=True)
    return {"score": clamp(max_gap), "questions": detected[:5]}


# ── Layer 4 — Practitioner vs Analyst Divergence ────────────────────────────

def classify_source_type(signal: dict, cfg: dict) -> str:
    src = signal.get("source") or {}
    src_type = src.get("type")
    if src_type in ("analyst", "competitor"):
        return "analyst"
    if src_type in ("research", "academic"):
        return "research"

    domain = (src.get("domain") or "").lower()
    org = (src.get("name") or "").lower()
    if any(a in domain or a in org for a in cfg["analyst_orgs"]):
        return "analyst"
    if any(d in domain for d in cfg["practitioner_domains"]):
        return "practitioner"
    if domain.endswith(".edu") or "arxiv" in domain:
        return "research"
    return "practitioner"


def measure_divergence(signal: dict, store, cfg: dict) -> dict:
    sentiment = store.get("topicSentiment")
    source_type = classify_source_type(signal, cfg)
    sig = simple_sentiment(_full_text(signal))
    topics = signal.get("topics") or []

    for topic in topics:
        s = sentiment.setdefault(topic, {"analyst": [], "practitioner": []})
        bucket = "analyst" if source_type == "analyst" else "practitioner"
        s[bucket].append(sig)
        if len(s[bucket]) > 20:
            s[bucket].pop(0)

    store.set("topicSentiment", sentiment)

    max_div = 0.0
    divergent = []
    for topic in topics:
        s = sentiment.get(topic)
        if not s or len(s["analyst"]) < 2 or len(s["practitioner"]) < 2:
            continue
        avg_a = sum(s["analyst"]) / len(s["analyst"])
        avg_p = sum(s["practitioner"]) / len(s["practitioner"])
        divergence = abs(avg_a - avg_p)
        if divergence > max_div:
            max_div = divergence
        if divergence > 0.30:
            divergent.append({"topic": topic, "divergence": divergence,
                             "analystSentiment": avg_a, "practitionerSentiment": avg_p})

    divergent.sort(key=lambda d: d["divergence"], reverse=True)
    return {"score": clamp(max_div), "sourceType": source_type, "divergentTopics": divergent}


# ── Layer 5 — Competitive Gap Intelligence ──────────────────────────────────

def score_competitive_gap(signal: dict, store, cfg: dict) -> dict:
    coverage = store.get("competitorCoverage")
    topics = signal.get("topics") or []
    src = signal.get("source") or {}
    author = signal.get("author") or {}
    author_name = author.get("name", "") if isinstance(author, dict) else (author or "")
    source_org = (src.get("name") or author_name or "").lower()
    competitors = cfg["competitors"]

    for comp in competitors:
        if comp in source_org:
            for topic in topics:
                coverage.setdefault(topic, [])
                if comp not in coverage[topic]:
                    coverage[topic].append(comp)

    store.set("competitorCoverage", coverage)

    scores = []
    for topic in topics:
        covered_by = len(coverage.get(topic, []))
        gap_ratio = 1 - covered_by / len(competitors) if competitors else 1
        scores.append({"topic": topic, "gapRatio": gap_ratio, "coveredBy": covered_by})

    if not scores:
        return {"score": 0.50, "topics": []}

    max_gap = max(s["gapRatio"] for s in scores)
    avg_gap = sum(s["gapRatio"] for s in scores) / len(scores)
    return {"score": clamp(max_gap * 0.70 + avg_gap * 0.30), "topics": scores}


# ── Layer 6 — Temporal & Calendar Intelligence (multiplier) ─────────────────

def get_temporal_multiplier(signal: dict, cfg: dict) -> dict:
    date = datetime.fromtimestamp(signal["timestamp"] / 1000, tz=timezone.utc)
    month = date.month
    topics = [t.lower() for t in (signal.get("topics") or [])]

    multiplier = 1.0
    reasons = []

    if month >= 10:
        gov = ["governance", "compliance", "regulation", "policy", "risk", "audit", "security"]
        if any(g in t for t in topics for g in gov):
            multiplier = max(multiplier, 1.35)
            reasons.append("Q4 governance season")

    if month >= 11:
        pred = ["prediction", "trend", "forecast", "2025", "2026", "2027", "future", "outlook"]
        if any(p in t for t in topics for p in pred):
            multiplier = max(multiplier, 1.25)
            reasons.append("Year-end predictions window")

    for conf in cfg["conference_calendar"]:
        c_month, c_day = conf["start"]
        conf_date = datetime(date.year, c_month, c_day, tzinfo=timezone.utc)
        days_until = _ceil_days(conf_date, date)
        if 0 <= days_until <= 14:
            if any(ct in t or t in ct for ct in conf["topics"] for t in topics):
                boost = 1.0 + 0.30 * (1 - days_until / 14)
                multiplier = max(multiplier, boost)
                reasons.append(f"Pre-{conf['name']} ({days_until}d out)")

    return {"multiplier": clamp(multiplier, 1.0, 1.5), "reasons": reasons}


def _ceil_days(conf_date: datetime, date: datetime) -> int:
    import math
    return math.ceil((conf_date - date).total_seconds() * 1000 / DAY_MS)


# ── Layer 7 — Source Trust ──────────────────────────────────────────────────

def get_source_trust(signal: dict, store, cfg: dict) -> dict:
    trust = store.get("sourceTrust")
    domain = (signal.get("source") or {}).get("domain", "").lower()
    domain = re.sub(r"^www\.", "", domain)

    if domain not in trust:
        initial = cfg["source_initial_trust"].get(domain, 0.55)
        trust[domain] = {"score": initial, "hits": 0, "misses": 0, "signals": 0}

    entry = trust[domain]
    entry["signals"] += 1
    store.set("sourceTrust", trust)
    return {"score": clamp(entry["score"]), "domain": domain, "signals": entry["signals"]}


def update_source_trust(domain: str, was_valuable: bool, store, cfg: dict) -> None:
    trust = store.get("sourceTrust")
    key = re.sub(r"^www\.", "", domain)
    if key not in trust:
        initial = cfg["source_initial_trust"].get(key, 0.55)
        trust[key] = {"score": initial, "hits": 0, "misses": 0, "signals": 0}
    entry = trust[key]
    if was_valuable:
        entry["hits"] += 1
        entry["score"] = clamp(entry["score"] + 0.05, 0, 1.0)
    else:
        entry["misses"] += 1
        entry["score"] = clamp(entry["score"] - 0.02, 0.30, 1.0)
    store.set("sourceTrust", trust)


# ── Layer 8 — Engagement Velocity ───────────────────────────────────────────

def score_engagement_velocity(signal: dict, cfg: dict, now_ms: float) -> dict:
    platform = (signal.get("source") or {}).get("platform", "blog").lower()
    eng = signal.get("engagement") or {}
    baselines = cfg["platform_baselines"]
    baseline = baselines.get(platform, baselines["blog"])

    age_hours = max((now_ms - signal["timestamp"]) / HOUR_MS, 0.5)
    reaction_rate = (eng.get("reactions") or 0) / age_hours
    comment_rate = (eng.get("comments") or 0) / age_hours
    share_rate = (eng.get("shares") or 0) / age_hours

    expected_r = baseline["reactions"] / 24
    expected_c = baseline["comments"] / 24
    expected_s = max(baseline["shares"], 1) / 24

    r = normalize(reaction_rate, 0, expected_r * 3)
    c = normalize(comment_rate, 0, expected_c * 3)
    s = normalize(share_rate, 0, expected_s * 3)
    velocity = r * 0.40 + c * 0.40 + s * 0.20

    return {"score": clamp(velocity), "platform": platform,
            "rates": {"reactions": reaction_rate, "comments": comment_rate, "shares": share_rate},
            "expected": {"reactions": expected_r, "comments": expected_c, "shares": expected_s}}


# ── Layer 9 — Cross-Platform Heat (multiplier) ──────────────────────────────

def measure_cross_platform_heat(signal: dict, store, cfg: dict) -> dict:
    window = store.get("platformTopicWindow")
    now = signal["timestamp"]
    cutoff = now - 48 * HOUR_MS
    platform = (signal.get("source") or {}).get("platform", "unknown").lower()
    topics = signal.get("topics") or []
    heat = cfg["heat_multipliers"]

    max_count = 1
    hot = []
    for topic in topics:
        window.setdefault(topic, [])
        window[topic].append({"platform": platform, "ts": now})
        window[topic] = [e for e in window[topic] if e["ts"] > cutoff]
        platforms = list({e["platform"] for e in window[topic]})
        count = len(platforms)
        if count > max_count:
            max_count = count
        if count >= 2:
            hot.append({"topic": topic, "platforms": platforms, "count": count,
                       "sightings": len(window[topic])})

    store.set("platformTopicWindow", window)
    multiplier = heat[min(max_count, len(heat) - 1)]
    hot.sort(key=lambda h: h["count"], reverse=True)
    return {"multiplier": multiplier, "platformCount": max_count, "hotTopics": hot}


# ── Layer 10 — Keywords / Relevance Depth ───────────────────────────────────

def score_relevance_depth(signal: dict, cfg: dict) -> float:
    full_text = " ".join([signal.get("title") or "", signal.get("body") or "",
                          *(signal.get("topics") or [])]).lower()
    tokens = tokenize(full_text)

    matches = sum(1 for term in cfg["domain_terms"] if term in full_text)
    breadth = clamp(matches / 5)
    unique_ratio = (len(set(tokens)) / len(tokens)) if tokens else 0
    length_score = clamp((len(tokens) - 50) / 450)
    return clamp(breadth * 0.60 + unique_ratio * 0.20 + length_score * 0.20)


# ── Layer 11 — Noise Filter (override) ──────────────────────────────────────

def detect_noise(signal: dict, store, cfg: dict) -> dict:
    full_text = _full_text(signal)
    full_lc = full_text.lower()
    topics = signal.get("topics") or []
    domain = re.sub(r"^www\.", "", (signal.get("source") or {}).get("domain", "").lower())
    trust = store.get("sourceTrust")
    reasons = []

    patterns = [re.compile(p, re.IGNORECASE) for p in cfg["noise_patterns"]]
    if any(p.search(full_text) for p in patterns):
        reasons.append("promotional content")

    has_relevance = any(t in full_lc for t in cfg["domain_terms"]) or len(topics) > 0
    if not has_relevance:
        reasons.append("no domain relevance")

    entry = trust.get(domain)
    if entry and entry["score"] < 0.35 and entry["signals"] >= 5:
        reasons.append("chronically low-trust source")

    if len(tokenize(full_text)) < 8:
        reasons.append("insufficient content")

    return {"isNoise": len(reasons) >= 2, "reasons": reasons}


# ── Layer 12 — Hype Cycle Position (multiplier) ─────────────────────────────

def detect_hype_cycle_phase(signal: dict, store, cfg: dict) -> dict:
    topics = signal.get("topics") or []
    platform_window = store.get("platformTopicWindow")
    concept_history = store.get("conceptHistory")
    sentiment = store.get("topicSentiment")
    now = signal["timestamp"]
    cutoff7d = now - 7 * DAY_MS
    cutoff30d = now - 30 * DAY_MS

    full_lc = _full_text(signal).lower()
    source_domain = (signal.get("source") or {}).get("domain", "").lower()
    is_mainstream = any(d in source_domain for d in cfg["mainstream_domains"])

    hype = sum(1 for w in cfg["hype_vocab"] if w in full_lc)
    trough = sum(1 for w in cfg["trough_vocab"] if w in full_lc)
    pract = sum(1 for w in cfg["practical_vocab"] if w in full_lc)
    plateau = sum(1 for w in cfg["plateau_vocab"] if w in full_lc)

    max_platforms = 1
    for topic in topics:
        recent = [e for e in platform_window.get(topic, []) if e["ts"] > cutoff7d]
        n = len({e["platform"] for e in recent})
        if n > max_platforms:
            max_platforms = n

    total_a = total_p = 0
    for topic in topics:
        s = sentiment.get(topic)
        if s:
            total_a += len(s["analyst"])
            total_p += len(s["practitioner"])
    pract_ratio = total_p / (total_a + total_p) if (total_a + total_p) > 0 else 0.5

    growth_rate = 0.0
    saturation = 0.5
    for topic in topics:
        hist = [e for e in concept_history.get(topic.lower(), []) if e["ts"] > cutoff30d]
        if len(hist) >= 4:
            mid = now - 15 * DAY_MS
            recent = len([e for e in hist if e["ts"] >= mid])
            prior = max(len([e for e in hist if e["ts"] < mid]), 1)
            gr = (recent - prior) / prior
            if abs(gr) > abs(growth_rate):
                growth_rate = gr
            peak = max(e["count"] for e in hist)
            total = sum(e["count"] for e in hist)
            saturation = max(saturation, clamp(total / max(peak * len(hist), 1)))

    if not is_mainstream and max_platforms <= 2 and pract_ratio > 0.70 and growth_rate > 0:
        phase, multiplier = "Innovation Trigger", 1.5
        confidence = clamp(pract_ratio * min(growth_rate + 0.5, 1.0))
    elif max_platforms >= 3 and is_mainstream and hype > trough and growth_rate > 0.2:
        phase, multiplier = "Peak of Inflated Expectations", 0.7
        confidence = clamp(max_platforms / 5 * 0.8 + 0.2)
    elif trough > hype and (growth_rate < -0.1 or saturation > 0.65):
        phase, multiplier = "Trough of Disillusionment", 1.2
        confidence = clamp(trough / 4 + (0.2 if growth_rate < 0 else 0))
    elif pract > hype and pract > trough and pract_ratio > 0.55 and growth_rate > -0.2:
        phase, multiplier = "Slope of Enlightenment", 1.3
        confidence = clamp(min(pract, 5) / 5 * pract_ratio)
    elif saturation > 0.70 and plateau >= pract and growth_rate <= 0.05:
        phase, multiplier = "Plateau of Productivity", 0.8
        confidence = clamp(saturation)
    else:
        phase, multiplier, confidence = "Innovation Trigger", 1.1, 0.25

    return {"phase": phase, "multiplier": multiplier, "confidence": confidence,
            "signals": {"maxPlatforms": max_platforms, "practRatio": pract_ratio,
                        "growthRate": growth_rate, "saturation": saturation,
                        "hyypeScore": hype, "troughScore": trough,
                        "practScore": pract, "plateauScore": plateau,
                        "isMainstream": is_mainstream}}
