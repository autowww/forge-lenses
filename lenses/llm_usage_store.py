"""Local LLM usage / analytics under ``<workspace_root>/.lenses-local/llm-usage.json``."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

USAGE_FILENAME = "llm-usage.json"
CURRENT_VERSION = 1
_DETAIL_MAX = 500
_DEFAULT_MAX_EVENTS = 500


def _max_events() -> int:
    v = (os.environ.get("LENSES_LLM_USAGE_MAX_EVENTS") or "").strip()
    if v.isdigit():
        return max(50, min(10_000, int(v)))
    return _DEFAULT_MAX_EVENTS


_DEFAULT: dict[str, Any] = {
    "version": CURRENT_VERSION,
    "totals": {},
    "last_ok": {},
    "events": [],
    "probe_log": [],
}


def usage_path(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / USAGE_FILENAME


def _normalize_totals_legacy(totals: dict[str, Any]) -> None:
    """Backfill attempts/failures for files written before analytics fields existed."""
    for _pid, t in list(totals.items()):
        if not isinstance(t, dict):
            continue
        if "attempts" not in t and "requests" in t:
            t["attempts"] = int(t.get("requests") or 0)
        if "failures" not in t:
            t["failures"] = 0


def _load(workspace_root: Path) -> dict[str, Any]:
    p = usage_path(workspace_root)
    if not p.is_file():
        return json.loads(json.dumps(_DEFAULT))
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return json.loads(json.dumps(_DEFAULT))
    if not isinstance(data, dict):
        return json.loads(json.dumps(_DEFAULT))
    out = json.loads(json.dumps(_DEFAULT))
    for k, v in data.items():
        if k in out:
            out[k] = v
    if not isinstance(out.get("totals"), dict):
        out["totals"] = {}
    if not isinstance(out.get("last_ok"), dict):
        out["last_ok"] = {}
    if not isinstance(out.get("events"), list):
        out["events"] = []
    if not isinstance(out.get("probe_log"), list):
        out["probe_log"] = []
    _normalize_totals_legacy(out["totals"])
    return out


def _save(workspace_root: Path, data: dict[str, Any]) -> None:
    p = usage_path(workspace_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p.parent, 0o700)
    except OSError:
        pass
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(p)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def record_chat_completion(
    workspace_root: Path,
    provider: str,
    usage: dict[str, Any] | None,
) -> None:
    """Backward-compatible wrapper: successful completion only."""
    record_llm_chat_result(
        workspace_root,
        (provider or "").strip().lower(),
        ok=True,
        result={"ok": True, "usage": usage or {}},
        message="",
        refine=False,
        routing_debug={},
        model_id=None,
    )


def record_llm_chat_result(
    workspace_root: Path,
    provider: str,
    *,
    ok: bool,
    result: dict[str, Any],
    message: str,
    refine: bool,
    routing_debug: dict[str, Any],
    model_id: str | None,
) -> None:
    """Append one LLM chat row for analytics (success or failure). User message is not stored."""
    pid = (provider or "").strip().lower()
    if not pid:
        return

    data = _load(workspace_root)
    now = datetime.now(timezone.utc).isoformat()

    usage = result.get("usage") if isinstance(result.get("usage"), dict) else None
    err_code = result.get("error")
    err_code_s = str(err_code).strip() if err_code is not None else ""
    detail_raw = result.get("detail")
    detail_s = (str(detail_raw).strip()[:_DETAIL_MAX] if detail_raw is not None else "") or None

    pt = ct = tt = 0
    if ok and usage and isinstance(usage, dict):
        pt = int(usage.get("prompt_tokens") or 0)
        ct = int(usage.get("completion_tokens") or 0)
        tt = int(usage.get("total_tokens") or 0)
        if tt == 0 and (pt or ct):
            tt = pt + ct

    totals: dict[str, Any] = data.setdefault("totals", {})
    cur = totals.get(pid) if isinstance(totals.get(pid), dict) else {}
    cur_pt = int(cur.get("prompt_tokens") or 0)
    cur_ct = int(cur.get("completion_tokens") or 0)
    cur_tt = int(cur.get("total_tokens") or 0)
    cur_okreq = int(cur.get("requests") or 0)
    cur_attempts = int(cur.get("attempts") or cur_okreq)
    cur_fail = int(cur.get("failures") or 0)

    cur_attempts += 1
    if not ok:
        cur_fail += 1
    if ok:
        cur_pt += pt
        cur_ct += ct
        cur_tt += tt if tt else pt + ct
        cur_okreq += 1

    totals[pid] = {
        "prompt_tokens": cur_pt,
        "completion_tokens": cur_ct,
        "total_tokens": cur_tt,
        "requests": cur_okreq,
        "attempts": cur_attempts,
        "failures": cur_fail,
    }

    if ok:
        data.setdefault("last_ok", {})[pid] = now

    route_src = None
    route_model = None
    fallback_from = None
    studio_task_id = None
    if isinstance(routing_debug, dict):
        s = routing_debug.get("source")
        route_src = str(s) if s is not None else None
        m = routing_debug.get("model")
        route_model = str(m) if m is not None else None
        fb = routing_debug.get("fallback_from")
        fallback_from = str(fb).strip().lower() if fb is not None and str(fb).strip() else None
        st = routing_debug.get("studio_task_id")
        studio_task_id = str(st).strip() if st is not None and str(st).strip() else None

    mid = (model_id or "").strip() or None
    if ok and not mid:
        m2 = result.get("model")
        mid = str(m2).strip() if m2 is not None else None

    msg_chars = len(message or "")

    ev = data.setdefault("events", [])
    ev.append(
        {
            "ts": now,
            "provider": pid,
            "source": "chat",
            "ok": ok,
            "model": mid,
            "refine": bool(refine),
            "message_chars": msg_chars,
            "routing_source": route_src,
            "routing_model": route_model,
            "fallback_from": fallback_from,
            "studio_task_id": studio_task_id,
            "prompt_tokens": pt if ok else 0,
            "completion_tokens": ct if ok else 0,
            "total_tokens": (tt if tt else pt + ct) if ok else 0,
            "error": err_code_s if not ok else None,
            "detail": detail_s if not ok else None,
        }
    )
    cap = _max_events()
    if len(ev) > cap:
        data["events"] = ev[-cap:]

    _save(workspace_root, data)


def record_provider_probe(
    workspace_root: Path,
    provider: str,
    action: str,
    result: dict[str, Any],
) -> None:
    """Append one provider discovery / health row (UI probes)."""
    pid = (provider or "").strip().lower()
    act = (action or "").strip().lower() or "models"
    if not pid:
        return
    data = _load(workspace_root)
    now = datetime.now(timezone.utc).isoformat()
    ok = bool(result.get("ok"))
    healthy = result.get("healthy")
    if healthy is not None:
        ok = bool(ok) and bool(healthy)
    err = result.get("error")
    err_s = str(err).strip() if err is not None else ""
    det_raw = result.get("detail")
    det_s = (str(det_raw).strip()[:_DETAIL_MAX] if det_raw is not None else "") or None
    log = data.setdefault("probe_log", [])
    if not isinstance(log, list):
        log = []
        data["probe_log"] = log
    log.append(
        {
            "ts": now,
            "provider": pid,
            "action": act,
            "ok": ok,
            "error": err_s or None,
            "detail": det_s,
        }
    )
    cap = _max_events()
    if len(log) > cap:
        data["probe_log"] = log[-cap:]
    _save(workspace_root, data)


def get_usage_summary(workspace_root: Path) -> dict[str, Any]:
    """Return totals, last_ok timestamps, and recent events for GET /api/llm/usage."""
    data = _load(workspace_root)
    events = data.get("events") if isinstance(data.get("events"), list) else []
    recent = events[-100:] if len(events) > 100 else events
    probes = data.get("probe_log") if isinstance(data.get("probe_log"), list) else []
    recent_probes = probes[-50:] if len(probes) > 50 else probes
    return {
        "totals": data.get("totals") or {},
        "last_ok": data.get("last_ok") or {},
        "recent_events": recent,
        "probe_log": recent_probes,
    }


def ollama_model_last_used_iso(workspace_root: Path) -> dict[str, str]:
    """Latest successful Studio chat timestamp (ISO) per Ollama ``model`` id from analytics events."""
    data = _load(workspace_root)
    events = data.get("events") if isinstance(data.get("events"), list) else []
    out: dict[str, str] = {}
    for ev in reversed(events):
        if not isinstance(ev, dict):
            continue
        if str(ev.get("provider", "") or "").strip().lower() != "ollama":
            continue
        if ev.get("ok") is not True:
            continue
        mid = str(ev.get("model") or "").strip()
        if not mid:
            continue
        ts = str(ev.get("ts") or "").strip()
        if ts and mid not in out:
            out[mid] = ts
    return out
