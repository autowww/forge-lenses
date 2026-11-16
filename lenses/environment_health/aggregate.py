"""Aggregate environment health from app /health JSON envelopes."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


def probe_health_url(url: str, *, bearer: str = "", timeout: float = 8.0) -> dict[str, Any]:
    req = urllib.request.Request(url, method="GET")
    if bearer:
        req.add_header("Authorization", f"Bearer {bearer}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            data = json.loads(body) if body.strip() else {}
            return {
                "ok": True,
                "url": url,
                "http_status": resp.status,
                "envelope": data,
                "status": data.get("status") or ("ok" if data.get("ok") else "unknown"),
                "summary": data.get("summary") or "",
                "checks": data.get("checks") or [],
            }
    except urllib.error.HTTPError as exc:
        return {"ok": False, "url": url, "http_status": exc.code, "error": str(exc)[:200]}
    except (OSError, json.JSONDecodeError, TimeoutError) as exc:
        return {"ok": False, "url": url, "error": str(exc)[:200]}


def rollup_environment_health(
  probes: list[dict[str, Any]],
) -> dict[str, Any]:
    if not probes:
        return {"status": "unknown", "summary": "No probes", "environments": []}
    down = [p for p in probes if not p.get("ok") or p.get("status") == "down"]
    degraded = [p for p in probes if p.get("status") == "degraded"]
    if down:
        return {
            "status": "down",
            "summary": f"{len(down)} environment(s) down",
            "environments": probes,
        }
    if degraded:
        return {
            "status": "degraded",
            "summary": f"{len(degraded)} environment(s) degraded",
            "environments": probes,
        }
    return {
        "status": "ok",
        "summary": f"All {len(probes)} environment(s) healthy",
        "environments": probes,
    }
