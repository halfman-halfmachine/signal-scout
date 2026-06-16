"""Signal ingestion — ported from signal-scout.js.

Seven concurrent fetchers (HN Algolia, Reddit JSON, arXiv/analyst/competitor/
news RSS, Google News) normalized into the engine's signal shape. Source lists
come from the `ingestion` config section (DB), so the UI drives ingestion.
RSS parsing uses feedparser instead of the original regex parser; no Workers CPU
budget here, so per-feed caps are relaxed.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any
from urllib.parse import quote

import feedparser
import httpx

from .. import config

GOOGLE_NEWS_BASE = "https://news.google.com/rss/search"
_HEADERS = {"User-Agent": config.USER_AGENT}


# ── Topic extraction ─────────────────────────────────────────────────────────

def extract_topics(text: str, cfg_engine: dict, extras: list[str] | None = None) -> list[str]:
    lower = (text or "").lower()
    matched = [t for t in cfg_engine["domain_terms"] if t in lower]
    for t in cfg_engine["tech_terms"]:
        if t in lower and t not in matched:
            matched.append(t)
    seen, out = set(), []
    for t in [*(extras or []), *matched]:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:8]


def _ms(struct_time) -> int:
    if not struct_time:
        return int(time.time() * 1000)
    import calendar
    # feedparser returns UTC struct_time; timegm treats it as UTC (mktime would not).
    return int(calendar.timegm(struct_time) * 1000)


def _slug(*candidates: str) -> str:
    raw = next((c for c in candidates if c), "")
    return "".join(ch for ch in raw if ch.isalnum())[-14:]


# ── HN Algolia ───────────────────────────────────────────────────────────────

async def fetch_hn(client: httpx.AsyncClient, queries: list[str], cfg_engine: dict) -> list[dict]:
    seven_days_ago = int(time.time()) - 7 * 86400
    seen, results = set(), []

    async def one(q: str):
        url = (f"https://hn.algolia.com/api/v1/search?query={quote(q)}&tags=story"
               f"&hitsPerPage=12&numericFilters=created_at_i>{seven_days_ago}")
        r = await client.get(url, headers=_HEADERS)
        if r.status_code != 200:
            return
        for hit in r.json().get("hits", []):
            oid = hit.get("objectID")
            if not hit.get("title") or oid in seen:
                continue
            seen.add(oid)
            author = hit.get("author") or ""
            results.append({
                "id": f"hn-{oid}",
                "title": hit["title"], "body": hit.get("story_text") or "",
                "author": {"name": author, "handle": f"@{author}" if author else ""},
                "source": {"name": "Hacker News", "domain": "news.ycombinator.com", "type": "tech_community", "platform": "hn"},
                "engagement": {"platform": "hn", "reactions": hit.get("points") or 0, "comments": hit.get("num_comments") or 0, "shares": 0},
                "topics": extract_topics(hit["title"], cfg_engine),
                "timestamp": _iso_ms(hit.get("created_at")),
                "url": hit.get("url") or f"https://news.ycombinator.com/item?id={oid}",
            })

    await asyncio.gather(*(one(q) for q in queries), return_exceptions=True)
    return results


def _iso_ms(date_str: str | None) -> int:
    """Parse an ISO-8601 timestamp (HN Algolia created_at) to epoch ms."""
    if not date_str:
        return int(time.time() * 1000)
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except ValueError:
        return int(time.time() * 1000)


# ── Reddit JSON ──────────────────────────────────────────────────────────────

async def fetch_reddit(client: httpx.AsyncClient, subs: str, cfg_engine: dict) -> list[dict]:
    url = f"https://www.reddit.com/r/{subs}/hot.json?limit=30&raw_json=1&t=week"
    r = await client.get(url, headers={"User-Agent": f"{config.USER_AGENT} (thought-leadership-radar)"})
    r.raise_for_status()
    children = r.json().get("data", {}).get("children", [])
    out = []
    for c in children:
        p = c.get("data", {})
        if (p.get("score") or 0) <= 10 or p.get("is_video"):
            continue
        author = p.get("author") or ""
        out.append({
            "id": f"reddit-{p.get('id')}",
            "title": p.get("title"), "body": p.get("selftext") or "",
            "author": {"name": author, "handle": f"u/{author}" if author else ""},
            "source": {"name": f"r/{p.get('subreddit')}", "domain": "reddit.com", "type": "community", "platform": "reddit"},
            "engagement": {"platform": "reddit", "reactions": p.get("score") or 0, "comments": p.get("num_comments") or 0, "shares": 0},
            "topics": extract_topics(f"{p.get('title')} {p.get('selftext') or ''}", cfg_engine),
            "timestamp": int((p.get("created_utc") or 0) * 1000),
            "url": f"https://reddit.com{p.get('permalink')}",
        })
    return out


# ── Generic RSS fetcher (arXiv / analyst / competitor / news) ────────────────

async def _fetch_rss(client: httpx.AsyncClient, url: str, *, id_prefix: str, name: str,
                     domain: str, source_type: str, platform: str, cfg_engine: dict,
                     limit: int | None, strip_categories: bool) -> list[dict]:
    r = await client.get(url, headers=_HEADERS)
    if r.status_code != 200:
        return []
    feed = feedparser.parse(r.content)
    entries = feed.entries[:limit] if limit else feed.entries
    out = []
    for item in entries:
        title = item.get("title")
        if not title:
            continue
        clean = _strip_cat(title) if strip_categories else title
        desc = item.get("summary") or item.get("description") or ""
        author = item.get("author") or name
        out.append({
            "id": f"{id_prefix}-{_slug(item.get('id'), item.get('link'))}",
            "title": clean, "body": desc,
            "author": {"name": author, "handle": ""},
            "source": {"name": name, "domain": domain, "type": source_type, "platform": platform},
            "engagement": {"platform": platform, "reactions": 0, "comments": 0, "shares": 0},
            "topics": extract_topics(f"{clean} {desc}", cfg_engine),
            "timestamp": _ms(item.get("published_parsed") or item.get("updated_parsed")),
            "url": item.get("link") or "",
        })
    return out


def _strip_cat(title: str) -> str:
    import re
    return re.sub(r"\[[\w.]+\]", "", title).strip()


async def fetch_arxiv(client, feeds: list[str], cfg_engine: dict) -> list[dict]:
    tasks = [_fetch_rss(client, u, id_prefix="arxiv", name="arXiv", domain="arxiv.org",
                        source_type="academic", platform="paper", cfg_engine=cfg_engine,
                        limit=30, strip_categories=True) for u in feeds]
    return _flatten(await asyncio.gather(*tasks, return_exceptions=True))


async def fetch_feeds(client, feeds: list[dict], *, id_prefix: str, source_type: str,
                      platform: str, cfg_engine: dict, limit: int | None) -> list[dict]:
    tasks = [_fetch_rss(client, f["url"], id_prefix=id_prefix, name=f["name"], domain=f["domain"],
                        source_type=source_type, platform=platform, cfg_engine=cfg_engine,
                        limit=limit, strip_categories=True) for f in feeds]
    return _flatten(await asyncio.gather(*tasks, return_exceptions=True))


# ── Google News RSS search ───────────────────────────────────────────────────

async def fetch_google_news(client: httpx.AsyncClient, queries: list[str], cfg_engine: dict) -> list[dict]:
    seen, results = set(), []

    async def one(q: str):
        url = f"{GOOGLE_NEWS_BASE}?q={quote(q)}&hl=en-US&gl=US&ceid=US:US"
        r = await client.get(url, headers=_HEADERS)
        if r.status_code != 200:
            return
        feed = feedparser.parse(r.content)
        for item in feed.entries[:8]:
            title = item.get("title")
            if not title:
                continue
            slug = _slug(item.get("id"), item.get("link"))
            if slug in seen:
                continue
            seen.add(slug)
            sep = title.rfind(" - ")
            clean = title[:sep].strip() if sep > -1 else title
            publisher = title[sep + 3:].strip() if sep > -1 else "Google News"
            desc = item.get("summary") or ""
            results.append({
                "id": f"gnews-{slug}",
                "title": clean, "body": desc,
                "author": {"name": publisher, "handle": ""},
                "source": {"name": publisher, "domain": "news.google.com", "type": "press", "platform": "news"},
                "engagement": {"platform": "news", "reactions": 0, "comments": 0, "shares": 0},
                "topics": extract_topics(f"{clean} {desc}", cfg_engine),
                "timestamp": _ms(item.get("published_parsed")),
                "url": item.get("link") or "",
            })

    await asyncio.gather(*(one(q) for q in queries), return_exceptions=True)
    return results


def _flatten(results: list[Any]) -> list[dict]:
    out = []
    for r in results:
        if isinstance(r, list):
            out.extend(r)
    return out


# ── Orchestrator ─────────────────────────────────────────────────────────────

async def ingest(ingestion_cfg: dict, engine_cfg: dict, topic: str | None = None) -> dict:
    """Run all sources concurrently and return {raw_signals, meta}."""
    preset = (ingestion_cfg.get("presets") or {}).get(topic) if topic else None
    hn_queries = preset["hn"] if preset else ingestion_cfg["hn_queries"]
    reddit_subs = preset["reddit"] if preset else ingestion_cfg["reddit_subs"]

    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        results = await asyncio.gather(
            fetch_hn(client, hn_queries, engine_cfg),
            fetch_reddit(client, reddit_subs, engine_cfg),
            fetch_arxiv(client, ingestion_cfg["arxiv_feeds"], engine_cfg),
            fetch_feeds(client, ingestion_cfg["analyst_feeds"], id_prefix="analyst",
                        source_type="analyst", platform="blog", cfg_engine=engine_cfg, limit=None),
            fetch_feeds(client, ingestion_cfg["competitor_feeds"], id_prefix="comp",
                        source_type="competitor", platform="blog", cfg_engine=engine_cfg, limit=None),
            fetch_feeds(client, ingestion_cfg["news_feeds"], id_prefix="news",
                        source_type="press", platform="news", cfg_engine=engine_cfg, limit=12),
            fetch_google_news(client, hn_queries, engine_cfg),
            return_exceptions=True,
        )

    keys = ["hn", "reddit", "arxiv", "analyst", "competitor", "news", "gnews"]
    raw, counts, errors = [], {}, []
    for key, res in zip(keys, results):
        if isinstance(res, Exception):
            counts[key] = 0
            errors.append(f"{key}: {res}")
        else:
            counts[key] = len(res)
            raw.extend(res)

    return {
        "raw": raw,
        "meta": {
            "mode": "focused" if preset else "general",
            "topic": {"key": topic, "label": preset["label"]} if preset else None,
            "sources": counts,
            "errors": errors,
        },
    }
