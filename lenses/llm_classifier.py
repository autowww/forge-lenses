"""Cheap LLM classifier hop for adaptive autoselection (Situ8-aligned prompt)."""

from __future__ import annotations

import json
import re
from typing import Any

from lenses.llm_http import http_post_json, http_post_json_classifier
from lenses.llm_routing import RequestClassification, TaskKind, Complexity

CLASSIFIER_USER_MAX_CHARS = 3000
CLASSIFIER_SYSTEM = """You are a classifier. Output ONLY a single JSON object with keys "task" and "complexity". No markdown, no other text.
Allowed task values: CHAT, CODE, REASONING, CREATIVE, SUMMARIZE, OTHER
Allowed complexity values: TRIVIAL, MODERATE, HEAVY"""


def _parse_json_object(text: str) -> dict[str, Any] | None:
    if not text or not text.strip():
        return None
    t = text.strip()
    m = re.search(r"\{[^{}]*\}", t, re.DOTALL)
    raw = m.group(0) if m else t
    try:
        o = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def classify_openai(api_key: str, user_prompt: str, model: str | None = None) -> RequestClassification | None:
    m = (model or "").strip() or "gpt-4o-mini"
    truncated = user_prompt[:CLASSIFIER_USER_MAX_CHARS]
    user_content = f"User request to classify:\n\n{truncated}"
    payload = {
        "model": m,
        "messages": [
            {"role": "system", "content": CLASSIFIER_SYSTEM},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": 128,
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    out = http_post_json_classifier(
        "https://api.openai.com/v1/chat/completions",
        payload,
        headers,
    )
    if out.get("_transport_error"):
        return None
    choices = out.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    ch0 = choices[0]
    if not isinstance(ch0, dict):
        return None
    msg = ch0.get("message")
    if not isinstance(msg, dict):
        return None
    content = msg.get("content")
    if not isinstance(content, str):
        return None
    return _classification_from_payload(_parse_json_object(content))


def classify_gemini(api_key: str, user_prompt: str, model: str | None = None) -> RequestClassification | None:
    m = (model or "").strip() or "gemini-2.0-flash"
    import urllib.parse

    truncated = user_prompt[:CLASSIFIER_USER_MAX_CHARS]
    user_content = f"{CLASSIFIER_SYSTEM}\n\nUser request to classify:\n\n{truncated}"
    model_path = m if m.startswith("models/") else f"models/{m}"
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent"
        f"?key={urllib.parse.quote(api_key)}"
    )
    payload = {"contents": [{"parts": [{"text": user_content}]}]}
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    out = http_post_json_classifier(url, payload, headers)
    if out.get("_transport_error"):
        return None
    cands = out.get("candidates")
    if not isinstance(cands, list) or not cands:
        return None
    c0 = cands[0]
    if not isinstance(c0, dict):
        return None
    content = c0.get("content")
    if not isinstance(content, dict):
        return None
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        return None
    p0 = parts[0]
    if not isinstance(p0, dict):
        return None
    text = p0.get("text")
    if not isinstance(text, str):
        return None
    return _classification_from_payload(_parse_json_object(text))


def _classification_from_payload(o: dict[str, Any] | None) -> RequestClassification | None:
    if not o:
        return None
    t = str(o.get("task", "OTHER")).upper()
    x = str(o.get("complexity", "MODERATE")).upper()
    try:
        task = TaskKind(t)
    except ValueError:
        task = TaskKind.OTHER
    try:
        comp = Complexity(x)
    except ValueError:
        comp = Complexity.MODERATE
    return RequestClassification(task=task, complexity=comp)
