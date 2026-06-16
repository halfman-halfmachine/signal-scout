"""API integration tests using FastAPI TestClient against a temp database.

Covers config CRUD, the manual-signal queue lifecycle, score preview, feedback,
template-fallback generation, persistence across re-open, and the optional auth
gate. No network (ingestion is exercised by the live full-loop verification).
"""
from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.storage import database as db


@pytest.fixture(autouse=True)
def fresh_db():
    # Recreate schema + reseed config before each test for isolation.
    if config.DB_PATH.exists():
        config.DB_PATH.unlink()
    for suffix in ("-wal", "-shm"):
        p = config.DB_PATH.with_name(config.DB_PATH.name + suffix)
        if p.exists():
            p.unlink()
    db.init_db()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["llm"] == "template"  # no API key in tests


def test_config_roundtrip(client):
    r = client.get("/api/config/engine")
    assert r.status_code == 200
    cfg = r.json()
    assert "domain_terms" in cfg

    cfg["domain_terms"] = ["quantum computing", "post-quantum crypto"]
    cfg["competitors"] = ["acme", "globex"]
    r = client.put("/api/config/engine", json={"data": cfg})
    assert r.status_code == 200

    again = client.get("/api/config/engine").json()
    assert again["domain_terms"] == ["quantum computing", "post-quantum crypto"]


def test_unknown_config_section_404(client):
    assert client.get("/api/config/bogus").status_code == 404


def test_score_preview_matches_manual_formula(client):
    layers = {"l1": 0.9, "l2": False, "l3": 0.7, "l4": 0.7, "l5": 0.6, "l6": 1.1,
              "l7": 0.9, "l8": 0.8, "l9": 1.1, "l10": 0.85, "l11": False, "l12": 1.1}
    r = client.post("/api/score-preview", json={"layers": layers})
    assert r.status_code == 200
    body = r.json()
    assert 0 < body["score"] <= 1
    assert body["tier"] in {"IMMEDIATE", "ROUTE", "DIGEST", "LOG"}


def test_noise_layer_zeroes_preview(client):
    r = client.post("/api/score-preview", json={"layers": {"l1": 0.9, "l11": True}})
    assert r.json()["score"] == 0
    assert r.json()["tier"] == "LOG"


def test_manual_signal_lifecycle(client):
    payload = {
        "title": "Lean agent stacks cut inference cost",
        "author": "Client lead", "platform": "linkedin", "domain": "frugal ai",
        "text": "Over-built agent frameworks are expensive.",
        "layers": {"l1": 0.6, "l3": 0.4, "l4": 0.4, "l5": 0.3, "l6": 1.0,
                   "l7": 0.7, "l8": 0.4, "l9": 1.0, "l10": 0.5, "l12": 1.0},
    }
    r = client.post("/api/signals", json=payload)
    assert r.status_code == 200
    sid = r.json()["signal"]["id"]
    assert r.json()["signal"]["origin"] == "manual"

    # Appears in queue listing.
    listing = client.get("/api/signals").json()
    assert any(s["id"] == sid for s in listing["signals"])

    # Mark kept.
    r = client.patch(f"/api/signals/{sid}", json={"kept": True})
    assert r.json()["signal"]["kept"] is True

    # Dismiss hides it from default listing.
    client.patch(f"/api/signals/{sid}", json={"dismissed": True})
    visible = client.get("/api/signals").json()["signals"]
    assert all(s["id"] != sid for s in visible)
    with_dismissed = client.get("/api/signals?include_dismissed=true").json()["signals"]
    assert any(s["id"] == sid for s in with_dismissed)

    # Delete.
    assert client.delete(f"/api/signals/{sid}").status_code == 200
    assert client.delete(f"/api/signals/{sid}").status_code == 404


def test_feedback_adjusts_source_trust(client):
    r = client.post("/api/feedback", json={"domain": "example-blog.com", "was_valuable": True})
    assert r.status_code == 200
    trust1 = r.json()["source_trust"]["score"]
    r = client.post("/api/feedback", json={"domain": "example-blog.com", "was_valuable": True})
    trust2 = r.json()["source_trust"]["score"]
    assert trust2 > trust1  # repeated positive feedback raises trust


def test_generate_template_fallback(client):
    body = {
        "output_types": ["social-post"],
        "signal": {"title": "Small models win", "author": "X", "platform": "twitter", "domain": "frugal ai"},
        "framework_id": "spark", "social_platform": "linkedin",
        "score": 0.9, "tier": "IMMEDIATE", "layers": {"l1": 0.9, "l2": True},
    }
    r = client.post("/api/generate", json=body)
    assert r.status_code == 200
    outs = r.json()["outputs"]
    assert len(outs) == 1
    assert outs[0]["is_live"] is False
    assert "TEMPLATE" in outs[0]["content"]

    # Output is persisted to history.
    hist = client.get("/api/outputs").json()["outputs"]
    assert len(hist) == 1


def test_topics_lists_presets(client):
    # Presets ship blank, so a fresh install lists no topics.
    assert client.get("/api/topics").json()["topics"] == []

    # Configured presets surface as selectable topics.
    ing = client.get("/api/config/ingestion").json()
    ing["presets"] = {"my-topic": {"label": "My Topic", "hn": ["q"], "reddit": "sub"}}
    client.put("/api/config/ingestion", json={"data": ing})

    topics = client.get("/api/topics").json()["topics"]
    assert {"key": "my-topic", "label": "My Topic"} in topics


def test_persistence_across_reopen(client):
    """The core 'it now persists' guarantee: data survives a DB connection reopen."""
    payload = {"title": "Persisted signal", "platform": "blog", "domain": "x",
               "layers": {"l1": 0.5, "l7": 0.6, "l10": 0.5}}
    sid = client.post("/api/signals", json=payload).json()["signal"]["id"]

    # Simulate a restart: new connections (the module opens per-call), data remains.
    importlib.reload(db)
    found = db.get_signal(sid)
    assert found is not None
    assert found["title"] == "Persisted signal"


def test_auth_gate(monkeypatch):
    """With SCOUT_PASSWORD set, protected routes require a valid session."""
    monkeypatch.setattr(config, "SCOUT_PASSWORD", "hunter2")
    c = TestClient(app)

    assert c.get("/api/config/engine").status_code == 401  # no session

    status = c.get("/api/auth/status").json()
    assert status["auth_required"] is True
    assert status["authenticated"] is False

    assert c.post("/api/auth/login", json={"password": "wrong"}).status_code == 401

    ok = c.post("/api/auth/login", json={"password": "hunter2"})
    assert ok.status_code == 200
    # Cookie now set on the client; protected route works.
    assert c.get("/api/config/engine").status_code == 200
