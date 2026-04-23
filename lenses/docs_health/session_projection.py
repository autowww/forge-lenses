"""Session view-model helpers: header stats, redaction, and response shaping."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

_LIVE_STATUSES = frozenset({"running", "awaiting_approval", "awaiting_input"})


def derive_session_display_name(session: dict[str, Any]) -> str:
    """Human-readable runner label for the session (stored on new sessions; derived for older files)."""
    existing = str(session.get("display_name") or "").strip()
    if existing:
        return existing
    proj = str(session.get("project") or "").strip() or "project"
    cluster = session.get("cluster") if isinstance(session.get("cluster"), dict) else {}
    cid = str(session.get("cluster_id") or "").strip()
    clabel = str(cluster.get("label") or "").strip()
    tail = clabel or cid or "cluster"
    return f"Docs remediation · {proj} · {tail}"

_REDACT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"sk-[A-Za-z0-9]{16,}", re.IGNORECASE), "[REDACTED:sk]"),
    (re.compile(r"Bearer\s+[A-Za-z0-9._\-]{10,}", re.IGNORECASE), "Bearer [REDACTED]"),
    (re.compile(r"(api[_-]?key|apikey|secret|token|password)\s*[:=]\s*[^\s\n]{4,}", re.IGNORECASE), r"\1=[REDACTED]"),
    (re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+PRIVATE KEY-----"), "[REDACTED:pem]"),
]


def redact_secrets(text: str, *, max_len: int = 200_000) -> str:
    """Best-effort redaction for command output shown in Studio."""
    if not text:
        return ""
    s = text if len(text) <= max_len else text[:max_len] + "\n…(truncated)"
    for pat, repl in _REDACT_PATTERNS:
        s = pat.sub(repl, s)
    return s


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts or not isinstance(ts, str):
        return None
    t = ts.strip()
    if not t:
        return None
    try:
        if t.endswith("Z"):
            t = t[:-1] + "+00:00"
        return datetime.fromisoformat(t)
    except ValueError:
        return None


def _elapsed_seconds(started_at: str | None) -> int | None:
    st = _parse_iso(started_at)
    if st is None:
        return None
    now = datetime.now(timezone.utc)
    if st.tzinfo is None:
        st = st.replace(tzinfo=timezone.utc)
    return max(0, int((now - st).total_seconds()))


def compute_header_stats(session: dict[str, Any]) -> dict[str, Any]:
    """Aggregates for Docs Health session header (live stats strip)."""
    usage = session.get("usage_session") if isinstance(session.get("usage_session"), dict) else {}
    events = session.get("events") if isinstance(session.get("events"), list) else []

    last_model: str | None = None
    last_verification: dict[str, Any] | None = None
    verification_pipeline: dict[str, Any] | None = None
    last_kpi: dict[str, Any] | None = None
    commands_run = 0
    file_changes = 0
    for ev in events:
        if not isinstance(ev, dict):
            continue
        t = str(ev.get("type") or "")
        if t == "token_stats" and ev.get("last_model"):
            last_model = str(ev.get("last_model"))
        if t == "verification":
            layer = str(ev.get("layer") or "")
            snap = {"ok": ev.get("ok"), "detail": str(ev.get("detail") or "")[:400], "layer": layer}
            if layer == "pipeline":
                verification_pipeline = snap
            else:
                last_verification = snap
        if t == "kpi_update":
            last_kpi = dict(ev)
        if t == "command":
            commands_run += 1
        if t == "file_change":
            file_changes += 1

    pt = int(usage.get("prompt_tokens") or 0) if isinstance(usage.get("prompt_tokens"), (int, float)) else 0
    ct = int(usage.get("completion_tokens") or 0) if isinstance(usage.get("completion_tokens"), (int, float)) else 0
    tt = int(usage.get("total_tokens") or 0) if isinstance(usage.get("total_tokens"), (int, float)) else 0
    if tt == 0 and (pt or ct):
        tt = pt + ct

    last_model_id = str(usage.get("last_model_id") or "").strip() or None
    if last_model_id:
        last_model = last_model_id

    baseline = session.get("baseline_score")
    score_delta: int | None = None
    if last_kpi is not None:
        sv = last_kpi.get("score")
        if isinstance(sv, (int, float)) and isinstance(baseline, (int, float)):
            score_delta = int(sv) - int(baseline)

    by_slot = usage.get("by_slot") if isinstance(usage.get("by_slot"), dict) else {}
    active_slot = None
    if isinstance(by_slot, dict) and by_slot:
        # last touched slot with calls > 0
        best = None
        best_calls = -1
        for k, v in by_slot.items():
            if not isinstance(v, dict):
                continue
            c = int(v.get("calls") or 0)
            if c > best_calls:
                best_calls = c
                best = str(k)
        active_slot = best

    hs: dict[str, Any] = {
        "elapsed_seconds": _elapsed_seconds(str(session.get("started_at") or "")),
        "status": str(session.get("status") or ""),
        "active_model": last_model,
        "last_model_id": last_model_id,
        "active_slot": active_slot,
        "last_provider": str(usage.get("last_chosen_provider") or "").strip() or None,
        "total_tokens": tt,
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "commands_run": commands_run,
        "files_changed": file_changes,
        "verification": last_verification,
        "verification_pipeline": verification_pipeline,
        "score_delta": score_delta,
        "baseline_score": baseline if isinstance(baseline, (int, float)) else None,
        "updated_at": str(session.get("updated_at") or ""),
    }
    mrp = session.get("model_routing_preview")
    if isinstance(mrp, dict):
        hs["model_routing_preview"] = mrp
    return hs


def session_public_view(session: dict[str, Any]) -> dict[str, Any]:
    """Copy of session dict with derived header_stats for API responses."""
    out = dict(session)
    if not str(out.get("display_name") or "").strip():
        out["display_name"] = derive_session_display_name(session)
    out["header_stats"] = compute_header_stats(session)
    return out


def is_live_status(status: str | None) -> bool:
    return str(status or "").strip().lower() in _LIVE_STATUSES
