"""Offline ingestion tests — topic extraction and normalization helpers.

Network fetchers are exercised by the live full-loop verification, not here.
"""
from app.ingestion.sources import _iso_ms, _slug, _strip_cat, extract_topics

from parity.reference_config import reference_engine_config

# Production defaults are blank; topic-extraction tests need a populated config.
CFG = reference_engine_config()


def test_extract_topics_matches_domain_then_tech_terms():
    topics = extract_topics("Snowflake and dbt power our lakehouse with vector embeddings", CFG)
    assert "snowflake" in topics
    assert "dbt" in topics
    assert "lakehouse" in topics
    assert len(topics) <= 8


def test_extract_topics_dedupes_and_honors_extras():
    topics = extract_topics("llm rag llm", CFG, extras=["preset-topic"])
    assert topics[0] == "preset-topic"
    assert topics.count("llm") == 1


def test_strip_category_tags():
    assert _strip_cat("A new method [cs.AI]") == "A new method"


def test_iso_ms_parses_z_suffix():
    assert _iso_ms("2026-06-10T12:00:00.000Z") == 1781092800000


def test_slug_takes_last_14_alnum():
    assert _slug("", "https://example.com/posts/abc123") == _slug("https://example.com/posts/abc123")
    assert len(_slug("https://example.com/some/really/long/path/item-99999")) <= 14
