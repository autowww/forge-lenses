"""
OpenAI-compatible chat completion using Situ8 taxonomy LLM env vars only.
Mirrors Situ8/scripts/taxonomy_llm_openai.py behavior.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


def chat_url(base: str) -> str:
    b = base.rstrip("/")
    if b.endswith("/v1"):
        return f"{b}/chat/completions"
    return f"{b}/v1/chat/completions"


def _headers() -> dict[str, str]:
    h: dict[str, str] = {"Content-Type": "application/json"}
    api_key = os.environ.get("TAXONOMY_LLM_API_KEY", "").strip()
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    if os.environ.get("TAXONOMY_LLM_NGROK_BYPASS", "").strip() in ("1", "true", "yes"):
        h["ngrok-skip-browser-warning"] = "true"
    return h


@dataclass
class ChatResult:
    ok: bool
    text: str
    raw_http_body: str | None = None


def chat_completion(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.25,
    timeout_sec: int = 300,
) -> ChatResult:
    base = os.environ.get("TAXONOMY_LLM_BASE_URL", "").strip()
    if not base:
        return ChatResult(False, "Missing TAXONOMY_LLM_BASE_URL")

    try:
        from forge_composer.taxonomy_llm.thermal_guard import ensure_cool_before_chat

        ensure_cool_before_chat()
    except ImportError:
        pass

    m = model or os.environ.get("TAXONOMY_LLM_MODEL", "ibm/granite4:tiny-h")
    url = chat_url(base)
    body: dict[str, Any] = {"model": m, "temperature": temperature, "messages": messages}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return ChatResult(False, f"HTTP {e.code} {e.reason}\n{err_body}", err_body)
    except urllib.error.URLError as e:
        return ChatResult(False, str(e))

    try:
        payload: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError:
        return ChatResult(
            False,
            "Response was not JSON (tunnel HTML interstitial?). Try TAXONOMY_LLM_NGROK_BYPASS=1.",
            raw[:4000],
        )

    choices = payload.get("choices") or []
    if not choices:
        return ChatResult(False, "No choices in response: " + json.dumps(payload)[:800], raw[:4000])
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str):
        return ChatResult(False, "Missing message.content", raw[:4000])
    return ChatResult(True, content, None)
