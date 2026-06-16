"""LLM prompt/template builder tests — structure and key-content assertions.

These verify the ported prompt/template logic produces the expected sections
without calling Anthropic (no network, no API key).
"""
from app.llm import client as C
from app.llm import prompt as P
from app import config

CTX = {
    "signal": {
        "url": "https://example.com/post", "title": "Small models, big context",
        "author": "Andrej Karpathy", "platform": "twitter", "domain": "frugal ai",
        "org": "", "text": "Most AI budget goes to the wrong layer.",
        "talking_points": "Tie to context layer\nUse as cold open",
    },
    "framework": {"name": "SPARK", "beats": ["Signal", "Position", "Argument", "Reinforcement", "Kicker"]},
    "output_type": {"id": "social-post", "name": "Social Post"},
    "social_platform": "linkedin",
    "score": 0.9, "tier": "IMMEDIATE",
    "layers": {"l1": 0.9, "l2": True, "l3": 0.7, "l7": 0.9, "l10": 0.85},
    "active_lenses": [{"name": "Frugal AI", "keywords": ["frugal ai", "inference cost", "slm", "quantization", "x"]}],
    "input_mode": {"name": "Market Signal", "desc": "Automated ingestion."},
    "personas": [{"name": "Enterprise CDO", "archetype": "Executive Buyer", "description": "C-level.",
                  "painPoints": ["ROI", "governance"], "tone": "Executive", "formatPref": "Article",
                  "platform": "LinkedIn", "ctaType": "Book a call"}],
    "povs": [{"name": "Disagree", "desc": "Contrarian"}],
    "pov_custom": "",
    "web_research": True,
}


def test_prompt_has_core_sections():
    prompt = P.build_prompt(CTX, "social-post")
    assert "SIGNAL DETAILS:" in prompt
    assert "Title: Small models, big context" in prompt
    assert "L2 Thought Leader Override: ACTIVE" in prompt
    assert "ACTIVE LENS(ES): Frugal AI" in prompt
    assert "TARGET PERSONA(S):" in prompt
    assert "POSITIONING / POV: Disagree" in prompt
    assert "WEB RESEARCH ENRICHMENT: ON" in prompt
    assert "Zero em dashes" in prompt
    assert "Generate the Social Post now:" in prompt


def test_template_linkedin_structure():
    tmpl = P.build_template(CTX, "social-post")
    assert tmpl.startswith("[TEMPLATE | SOCIAL POST | SPARK FRAMEWORK | 0.90 / IMMEDIATE]")
    assert "URGENT: Publish within 24 hours." in tmpl
    assert "POST BODY (SPARK):" in tmpl
    assert "SIGNAL:" in tmpl
    assert "#frugalai" in tmpl


def test_api_body_includes_web_search_tool_when_enabled():
    body = C.build_api_body(CTX, "social-post")
    assert body["messages"][0]["content"].endswith("Generate the Social Post now:")
    assert body["tools"][0]["name"] == "web_search"


def test_api_body_omits_tool_when_disabled():
    ctx = {**CTX, "web_research": False}
    body = C.build_api_body(ctx, "social-post")
    assert "tools" not in body


def test_api_body_omits_web_search_tool_on_gateway(monkeypatch):
    # Gateways (e.g. Snowflake Cortex) reject the web_search server tool, so it
    # must be omitted even when web_research is requested.
    monkeypatch.setattr(config, "ANTHROPIC_BASE_URL", "https://gw.example.com/api/v2/cortex")
    monkeypatch.setattr(config, "ANTHROPIC_WEB_SEARCH", "")
    body = C.build_api_body(CTX, "social-post")
    assert "tools" not in body


def test_web_search_env_override(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_BASE_URL", "https://gw.example.com/api/v2/cortex")
    monkeypatch.setattr(config, "ANTHROPIC_WEB_SEARCH", "true")
    assert config.web_search_supported() is True
    monkeypatch.setattr(config, "ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    monkeypatch.setattr(config, "ANTHROPIC_WEB_SEARCH", "false")
    assert config.web_search_supported() is False


def test_citation_extraction_appends_sources():
    data = {"content": [
        {"type": "text", "text": "Body text.", "citations": [
            {"url": "https://a.com", "title": "A"}, {"url": "https://a.com", "title": "A dup"}]},
        {"type": "text", "text": "More.", "citations": [{"url": "https://b.com"}]},
    ]}
    out = C.extract_content_with_citations(data)
    assert "Body text.\nMore." in out
    assert "SOURCES (via web search):" in out
    assert "1. A -- https://a.com" in out
    assert "2. https://b.com -- https://b.com" in out


def test_variant_adds_differentiation_note():
    body = C.build_api_body(CTX, "social-post", "\n\nThis is variant 2.")
    assert "This is variant 2." in body["messages"][0]["content"]


def test_default_endpoint_and_api_key_auth(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    monkeypatch.setattr(config, "ANTHROPIC_AUTH_TOKEN", "")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "sk-test")
    assert C._messages_url() == "https://api.anthropic.com/v1/messages"
    headers = C._request_headers()
    assert headers["x-api-key"] == "sk-test"
    assert "authorization" not in headers
    assert headers["anthropic-version"] == "2023-06-01"


def test_gateway_base_url_and_bearer_auth(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_BASE_URL", "https://gw.example.com/api/v2/cortex")
    monkeypatch.setattr(config, "ANTHROPIC_AUTH_TOKEN", "tok-123")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    assert C._messages_url() == "https://gw.example.com/api/v2/cortex/v1/messages"
    headers = C._request_headers()
    assert headers["authorization"] == "Bearer tok-123"
    assert "x-api-key" not in headers


def test_llm_enabled_with_token_only(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(config, "ANTHROPIC_AUTH_TOKEN", "tok-123")
    assert config.llm_enabled() is True

    monkeypatch.setattr(config, "ANTHROPIC_AUTH_TOKEN", "")
    assert config.llm_enabled() is False
