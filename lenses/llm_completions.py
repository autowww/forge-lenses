"""Provider-level HTTP completions (multi-provider transport). Used by ``llm_chat.chat()`` orchestration."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from lenses.llm_http import http_post_json, http_post_json_plain
from lenses.llm_settings_store import merge_key

DEFAULT_ANTHROPIC_MODEL = "claude-3-5-haiku-20241022"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_OLLAMA_MODEL = "llama3.2"
DEFAULT_COMPAT_MODEL = "gpt-4o-mini"


def _env_trim(key: str) -> str:
    return (os.environ.get(key) or "").strip()


OLLAMA_HEALTH_TIMEOUT_SEC = 2.0


def ollama_daemon_status() -> dict[str, Any]:
    """Whether the Ollama HTTP API responds at ``GET {base}/api/tags`` (Studio health indicator).

    On success, parses the JSON body and returns ``models`` as a list of model name strings
    (Ollama ``/api/tags`` ``models[].name``).
    """
    base_raw = _env_trim("OLLAMA_BASE_URL")
    if not base_raw:
        return {"reachable": False, "base": "", "configured": False, "models": [], "model_catalog": []}
    base = base_raw.rstrip("/")
    url = f"{base}/api/tags"
    try:
        req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=OLLAMA_HEALTH_TIMEOUT_SEC) as resp:
            code = getattr(resp, "status", None)
            if code is None and hasattr(resp, "getcode"):
                code = resp.getcode()
            if code == 200:
                models: list[str] = []
                catalog: list[dict[str, Any]] = []
                try:
                    raw_body = resp.read()
                    j = json.loads(raw_body.decode("utf-8"))
                    if isinstance(j, dict) and isinstance(j.get("models"), list):
                        for m in j["models"]:
                            if isinstance(m, dict):
                                n = str(m.get("name", "") or "").strip()
                                if n:
                                    models.append(n)
                                    catalog.append(
                                        {
                                            "name": n,
                                            "size": int(m.get("size") or 0),
                                            "modified_at": str(m.get("modified_at") or ""),
                                            "digest": str(m.get("digest") or "")[:24],
                                        }
                                    )
                except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
                    pass
                return {"reachable": True, "base": base, "configured": True, "models": models, "model_catalog": catalog}
    except (OSError, urllib.error.HTTPError, urllib.error.URLError):
        pass
    return {"reachable": False, "base": base, "configured": True, "models": [], "model_catalog": []}


def _ollama_transport_detail(base: str, raw: str) -> str:
    """Append a short setup hint when the local Ollama daemon is not reachable."""
    low = raw.lower()
    if "connection refused" not in low and "errno 111" not in low:
        return raw
    return (
        f"{raw} | Ollama not listening at {base}. Start the Ollama application or "
        "`ollama serve`, or set OLLAMA_BASE_URL to the correct HTTP(S) origin. "
        "Run `ollama pull <model>` for the model in "
        "LENSES_OLLAMA_MODEL / AI Setup / model override."
    )


def _usage_from_openai_response(out: dict[str, Any]) -> dict[str, int] | None:
    u = out.get("usage")
    if not isinstance(u, dict):
        return None
    pt = int(u.get("prompt_tokens") or 0)
    ct = int(u.get("completion_tokens") or 0)
    tt = int(u.get("total_tokens") or 0)
    if tt == 0 and (pt or ct):
        tt = pt + ct
    return {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": tt}


def _usage_from_anthropic_response(out: dict[str, Any]) -> dict[str, int] | None:
    u = out.get("usage")
    if not isinstance(u, dict):
        return None
    pt = int(u.get("input_tokens") or 0)
    ct = int(u.get("output_tokens") or 0)
    return {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct}


def _usage_from_gemini_response(out: dict[str, Any]) -> dict[str, int] | None:
    um = out.get("usageMetadata")
    if not isinstance(um, dict):
        return None
    pt = int(um.get("promptTokenCount") or 0)
    ct = int(um.get("candidatesTokenCount") or 0)
    tt = int(um.get("totalTokenCount") or 0)
    if tt == 0:
        tt = pt + ct
    return {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": tt}


def _usage_from_ollama_response(out: dict[str, Any]) -> dict[str, int] | None:
    pe = out.get("prompt_eval_count")
    ee = out.get("eval_count")
    if pe is None and ee is None:
        return None
    pt = int(pe or 0)
    ct = int(ee or 0)
    return {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct}


def _gemini_api_key_file(file_keys: dict[str, str] | None) -> str:
    if file_keys:
        g = merge_key(_env_trim("GOOGLE_API_KEY") or _env_trim("GEMINI_API_KEY"), file_keys.get("gemini", ""))
        if g:
            return g
    return _env_trim("GOOGLE_API_KEY") or _env_trim("GEMINI_API_KEY")


def _anthropic(
    message: str,
    model_override: str | None,
    *,
    api_key: str | None = None,
) -> dict[str, Any]:
    key = (api_key or "").strip() or _env_trim("ANTHROPIC_API_KEY")
    if not key:
        return {"ok": False, "error": "llm_not_configured", "detail": "ANTHROPIC_API_KEY"}
    model = (model_override or "").strip() or _env_trim("LENSES_ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL
    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": message}],
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    }
    out = http_post_json("https://api.anthropic.com/v1/messages", payload, headers)
    if out.get("_transport_error"):
        return {"ok": False, "error": "llm_transport", "detail": str(out["_transport_error"])}
    if "content" in out and isinstance(out["content"], list):
        parts: list[str] = []
        for block in out["content"]:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        text = "".join(parts).strip()
        if text:
            u = _usage_from_anthropic_response(out)
            r: dict[str, Any] = {"ok": True, "text": text}
            if u:
                r["usage"] = u
            return r
    err = out.get("error")
    if isinstance(err, dict):
        msg = str(err.get("message", "anthropic_error"))
        return {"ok": False, "error": "llm_provider_error", "detail": msg[:500]}
    return {"ok": False, "error": "llm_provider_error", "detail": "unexpected_response"}


def _openai(
    message: str,
    model_override: str | None,
    *,
    api_key: str | None = None,
) -> dict[str, Any]:
    key = (api_key or "").strip() or _env_trim("OPENAI_API_KEY")
    if not key:
        return {"ok": False, "error": "llm_not_configured", "detail": "OPENAI_API_KEY"}
    model = (model_override or "").strip() or _env_trim("LENSES_OPENAI_MODEL") or DEFAULT_OPENAI_MODEL
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {key}",
    }
    out = http_post_json("https://api.openai.com/v1/chat/completions", payload, headers)
    if out.get("_transport_error"):
        return {"ok": False, "error": "llm_transport", "detail": str(out["_transport_error"])}
    choices = out.get("choices")
    if isinstance(choices, list) and choices:
        ch0 = choices[0]
        if isinstance(ch0, dict):
            msg = ch0.get("message")
            if isinstance(msg, dict) and msg.get("content"):
                text = str(msg["content"]).strip()
                u = _usage_from_openai_response(out)
                r: dict[str, Any] = {"ok": True, "text": text}
                if u:
                    r["usage"] = u
                return r
    err = out.get("error")
    if isinstance(err, dict):
        msg = str(err.get("message", "openai_error"))
        return {"ok": False, "error": "llm_provider_error", "detail": msg[:500]}
    return {"ok": False, "error": "llm_provider_error", "detail": "unexpected_response"}


def _gemini_with_key(
    message: str,
    model_override: str | None,
    api_key: str | None,
    file_keys: dict[str, str] | None,
) -> dict[str, Any]:
    key = (api_key or "").strip() or _gemini_api_key_file(file_keys)
    if not key:
        return {"ok": False, "error": "llm_not_configured", "detail": "GOOGLE_API_KEY or GEMINI_API_KEY"}
    model = (model_override or "").strip() or _env_trim("LENSES_GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
    if not model.startswith("models/"):
        model_path = f"models/{model}"
    else:
        model_path = model
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent"
        f"?key={urllib.parse.quote(key)}"
    )
    payload = {"contents": [{"parts": [{"text": message}]}]}
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    out = http_post_json(url, payload, headers)
    if out.get("_transport_error"):
        return {"ok": False, "error": "llm_transport", "detail": str(out["_transport_error"])}
    cands = out.get("candidates")
    if isinstance(cands, list) and cands:
        c0 = cands[0]
        if isinstance(c0, dict):
            content = c0.get("content")
            if isinstance(content, dict):
                parts = content.get("parts")
                if isinstance(parts, list) and parts:
                    p0 = parts[0]
                    if isinstance(p0, dict) and "text" in p0:
                        text = str(p0["text"]).strip()
                        u = _usage_from_gemini_response(out)
                        r: dict[str, Any] = {"ok": True, "text": text}
                        if u:
                            r["usage"] = u
                        return r
    err = out.get("error")
    if isinstance(err, dict):
        msg = str(err.get("message", "gemini_error"))
        return {"ok": False, "error": "llm_provider_error", "detail": msg[:500]}
    return {"ok": False, "error": "llm_provider_error", "detail": "unexpected_response"}


def _ollama(
    message: str,
    model_override: str | None,
) -> dict[str, Any]:
    base_raw = _env_trim("OLLAMA_BASE_URL")
    if not base_raw:
        return {"ok": False, "error": "llm_not_configured", "detail": "OLLAMA_BASE_URL"}
    base = base_raw.rstrip("/")
    model = (model_override or "").strip() or _env_trim("LENSES_OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL
    url = f"{base}/api/chat"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "stream": False,
    }
    out = http_post_json_plain(url, payload, None)
    if out.get("_transport_error"):
        raw = str(out["_transport_error"])
        return {"ok": False, "error": "llm_transport", "detail": _ollama_transport_detail(base, raw)}
    msg = out.get("message")
    if isinstance(msg, dict) and "content" in msg:
        text = str(msg["content"]).strip()
        u = _usage_from_ollama_response(out)
        r: dict[str, Any] = {"ok": True, "text": text}
        if u:
            r["usage"] = u
        return r
    err = out.get("error")
    if err:
        return {"ok": False, "error": "llm_provider_error", "detail": str(err)[:500]}
    return {"ok": False, "error": "llm_provider_error", "detail": "unexpected_response"}


def _openai_compatible(
    message: str,
    model_override: str | None,
    *,
    api_key: str | None = None,
    base_url_override: str | None = None,
) -> dict[str, Any]:
    env_base = _env_trim("LENSES_OPENAI_COMPAT_BASE_URL").rstrip("/")
    bo = (base_url_override or "").strip().rstrip("/")
    base = bo if bo else env_base
    if not base:
        return {"ok": False, "error": "llm_not_configured", "detail": "LENSES_OPENAI_COMPAT_BASE_URL"}
    key = merge_key(_env_trim("LENSES_OPENAI_COMPAT_KEY"), (api_key or "").strip())
    model = (model_override or "").strip() or _env_trim("LENSES_OPENAI_COMPAT_MODEL") or DEFAULT_COMPAT_MODEL
    url = f"{base}/v1/chat/completions"
    payload = {"model": model, "messages": [{"role": "user", "content": message}]}
    auth_headers: dict[str, str] = {}
    if key:
        auth_headers["Authorization"] = f"Bearer {key}"
    if base.startswith("https://"):
        full_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **auth_headers,
        }
        out = http_post_json(url, payload, full_headers)
    else:
        out = http_post_json_plain(url, payload, auth_headers or None)
    if out.get("_transport_error"):
        return {"ok": False, "error": "llm_transport", "detail": str(out["_transport_error"])}
    choices = out.get("choices")
    if isinstance(choices, list) and choices:
        ch0 = choices[0]
        if isinstance(ch0, dict):
            msg = ch0.get("message")
            if isinstance(msg, dict) and msg.get("content"):
                text = str(msg["content"]).strip()
                u = _usage_from_openai_response(out)
                r: dict[str, Any] = {"ok": True, "text": text}
                if u:
                    r["usage"] = u
                return r
    err = out.get("error")
    if isinstance(err, dict):
        msg = str(err.get("message", "compat_error"))
        return {"ok": False, "error": "llm_provider_error", "detail": msg[:500]}
    return {"ok": False, "error": "llm_provider_error", "detail": "unexpected_response"}


_COMPLETION_PROVIDERS = frozenset(
    ("anthropic", "openai", "gemini", "ollama", "openai_compatible"),
)


def complete_user_message(
    provider: str,
    message: str,
    model: str | None,
    file_keys: dict[str, str],
    *,
    openai_compat_base_url: str | None = None,
) -> dict[str, Any]:
    """Run one user message through the given provider (env + optional file keys)."""
    pid = (provider or "").strip().lower()
    if pid not in _COMPLETION_PROVIDERS:
        return {"ok": False, "error": "invalid_provider", "detail": pid or "(empty)"}
    fk = file_keys
    if pid == "anthropic":
        return _anthropic(message, model, api_key=fk.get("anthropic") or None)
    if pid == "openai":
        return _openai(message, model, api_key=fk.get("openai") or None)
    if pid == "gemini":
        return _gemini_with_key(message, model, fk.get("gemini") or None, fk)
    if pid == "ollama":
        return _ollama(message, model)
    return _openai_compatible(
        message,
        model,
        api_key=fk.get("openai_compatible") or None,
        base_url_override=openai_compat_base_url,
    )
