"""Shared stdlib HTTP helpers for LLM API calls."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from typing import Any

HTTP_TIMEOUT_SEC = 60
CLASSIFIER_TIMEOUT_SEC = 25
DISCOVERY_TIMEOUT_SEC = 20.0


def http_post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    *,
    timeout: float = HTTP_TIMEOUT_SEC,
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers=headers,
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {"error": {"message": e.reason or str(e.code)}}
    except OSError as e:
        return {"_transport_error": str(e)}

    try:
        out = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"error": {"message": "invalid_json_response"}}
    return out if isinstance(out, dict) else {}


def http_post_json_plain(
    url: str,
    payload: dict[str, Any],
    extra_headers: dict[str, str] | None = None,
    *,
    timeout: float = HTTP_TIMEOUT_SEC,
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    hdrs = {"Content-Type": "application/json", "Accept": "application/json"}
    if extra_headers:
        hdrs.update(extra_headers)
    req = urllib.request.Request(url, data=data, method="POST", headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {"error": {"message": e.reason or str(e.code)}}
    except OSError as e:
        return {"_transport_error": str(e)}

    try:
        out = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"error": {"message": "invalid_json_response"}}
    return out if isinstance(out, dict) else {}


def http_get_json(
    url: str,
    headers: dict[str, str] | None = None,
    *,
    timeout: float = DISCOVERY_TIMEOUT_SEC,
) -> dict[str, Any]:
    """GET JSON (discovery / health). Returns ``{_transport_error: …}`` on failure."""
    hdrs = dict(headers or {})
    if "Accept" not in hdrs:
        hdrs["Accept"] = "application/json"
    req = urllib.request.Request(url, method="GET", headers=hdrs)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {"error": {"message": e.reason or str(e.code)}}
    except OSError as e:
        return {"_transport_error": str(e)}

    try:
        out = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"error": {"message": "invalid_json_response"}}
    return out if isinstance(out, dict) else {}


def http_post_json_classifier(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
) -> dict[str, Any]:
    """Shorter timeout for classifier hop."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers=headers,
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=CLASSIFIER_TIMEOUT_SEC, context=ctx) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {"error": {"message": e.reason or str(e.code)}}
    except OSError as e:
        return {"_transport_error": str(e)}

    try:
        out = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"error": {"message": "invalid_json_response"}}
    return out if isinstance(out, dict) else {}
