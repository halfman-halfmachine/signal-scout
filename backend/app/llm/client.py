"""Server-side generation — Anthropic call, citation extraction, orchestration.

Ported from ssc-app.js (buildApiBody / extractContentWithCitations / generate),
but the API key lives in the server environment, never the browser. Falls back
to template output when no key is configured.
"""
from __future__ import annotations

import uuid
from typing import Any

from .. import config
from . import prompt as P


def build_api_body(ctx: dict, output_type_id: str, extra: str = "") -> dict:
    body = {
        "model": config.ANTHROPIC_MODEL,
        "max_tokens": config.ANTHROPIC_MAX_TOKENS,
        "messages": [{"role": "user", "content": P.build_prompt(ctx, output_type_id) + (extra or "")}],
    }
    if ctx.get("web_research") and config.web_search_supported():
        body["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}]
    return body


def extract_content_with_citations(data: dict) -> str:
    blocks = data.get("content") or []
    text_blocks = [b for b in blocks if b.get("type") == "text"]
    content = "\n".join(b.get("text", "") for b in text_blocks)

    citations: list[dict] = []
    for b in text_blocks:
        for c in (b.get("citations") or []):
            url = c.get("url")
            if url and not any(x["url"] == url for x in citations):
                citations.append({"url": url, "title": c.get("title") or url})

    if citations:
        content += "\n\n---\nSOURCES (via web search):\n" + "\n".join(
            f"{i + 1}. {c['title']} -- {c['url']}" for i, c in enumerate(citations)
        )
    return content


def _messages_url() -> str:
    return f"{config.ANTHROPIC_BASE_URL}/v1/messages"


def _request_headers() -> dict:
    """Auth via bearer token when configured (gateways), else x-api-key."""
    headers = {"content-type": "application/json", "anthropic-version": "2023-06-01"}
    if config.ANTHROPIC_AUTH_TOKEN:
        headers["authorization"] = f"Bearer {config.ANTHROPIC_AUTH_TOKEN}"
    else:
        headers["x-api-key"] = config.ANTHROPIC_API_KEY
    return headers


async def _call_anthropic(body: dict) -> dict:
    """Call the Anthropic Messages API. Uses the SDK if available, else httpx."""
    import httpx
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
        r = await client.post(
            _messages_url(),
            headers=_request_headers(),
            json=body,
        )
        if r.status_code != 200:
            err = {}
            try:
                err = r.json()
            except Exception:  # noqa: BLE001
                pass
            msg = (err.get("error") or {}).get("message") or f"API error {r.status_code}"
            raise RuntimeError(msg)
        return r.json()


async def generate_one(ctx: dict, output_type_id: str, variant: int = 0) -> dict:
    """Generate a single output. Live (Anthropic) when key present, else template."""
    ot = ctx["output_type"]
    fw = ctx["framework"]
    extra = ("" if variant == 0 else
             f"\n\nThis is variant {variant + 1}. Produce a meaningfully different angle, "
             f"hook, or structure than a typical first attempt.")

    if config.llm_enabled():
        data = await _call_anthropic(build_api_body(ctx, output_type_id, extra))
        content = extract_content_with_citations(data)
        is_live = True
    else:
        content = P.build_template(ctx, output_type_id)
        is_live = False

    return {
        "id": uuid.uuid4().hex,
        "output_type": output_type_id,
        "output_type_name": ot["name"],
        "framework": fw["name"],
        "content": content,
        "is_live": is_live,
        "variant": variant,
    }
