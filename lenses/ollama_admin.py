"""Ollama HTTP admin: pull and delete models (same host as ``OLLAMA_BASE_URL``)."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from typing import Any

from lenses.llm_completions import _env_trim

_PULL_TIMEOUT_SEC = 900.0
_DELETE_TIMEOUT_SEC = 120.0


def _ollama_post_json(path: str, payload: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    base_raw = (_env_trim("OLLAMA_BASE_URL") or "").strip()
    if not base_raw:
        return {"ok": False, "error": "not_configured", "detail": "OLLAMA_BASE_URL"}
    base = base_raw.rstrip("/")
    url = f"{base}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    ctx = ssl.create_default_context() if url.startswith("https://") else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            j = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {"ok": False, "error": "http_error", "detail": str(e.code)}
        if isinstance(j, dict) and j.get("error"):
            return {"ok": False, "error": "ollama_error", "detail": str(j.get("error", ""))[:500]}
        return {"ok": False, "error": "http_error", "detail": str(e.code)}
    except OSError as e:
        return {"ok": False, "error": "transport", "detail": str(e)[:500]}

    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return {"ok": True, "detail": "empty_body"}
    if text.startswith("{") and "\n" not in text:
        try:
            j = json.loads(text)
            return {"ok": True, "result": j if isinstance(j, dict) else {}}
        except json.JSONDecodeError:
            return {"ok": True, "detail": "non_json"}
    last: dict[str, Any] | None = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            j = json.loads(line)
            if isinstance(j, dict):
                last = j
        except json.JSONDecodeError:
            continue
    return {"ok": True, "result": last or {}}


def ollama_pull(model: str, *, stream: bool = False) -> dict[str, Any]:
    """Pull or update a model tag (``stream=False`` waits for completion)."""
    name = (model or "").strip()
    if not name:
        return {"ok": False, "error": "missing_model"}
    return _ollama_post_json("/api/pull", {"name": name, "stream": stream}, timeout=_PULL_TIMEOUT_SEC)


def ollama_delete(model: str) -> dict[str, Any]:
    """Remove a model from the local Ollama library."""
    name = (model or "").strip()
    if not name:
        return {"ok": False, "error": "missing_model"}
    return _ollama_post_json("/api/delete", {"name": name}, timeout=_DELETE_TIMEOUT_SEC)
