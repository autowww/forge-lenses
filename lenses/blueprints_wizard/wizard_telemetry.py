"""Opt-in local telemetry for the Blueprints Wizard (JSONL under ``.lenses-local/``)."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lenses.blueprints_wizard.feature_flag import experimental_blueprints_wizard_enabled

_TELEMETRY_ENV = "LENSES_BLUEPRINTS_WIZARD_TELEMETRY"
_MAX_FILE_BYTES = 2_000_000
_MAX_EVENT_STR = 128


def wizard_telemetry_enabled() -> bool:
    """Requires experimental wizard on and ``LENSES_BLUEPRINTS_WIZARD_TELEMETRY`` truthy."""
    if not experimental_blueprints_wizard_enabled():
        return False
    raw = (os.environ.get(_TELEMETRY_ENV) or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _telemetry_path(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / "blueprints-wizard" / "telemetry.jsonl"


def _trim(s: str, n: int) -> str:
    t = s.strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def _sanitize_session_id(raw: Any) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or len(s) > 200:
        return None
    return s


def _sanitize_event_name(raw: Any) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or len(s) > _MAX_EVENT_STR:
        return None
    # Allow alphanumerics and a small safe punctuation set
    ok = all(c.isalnum() or c in "._-/" for c in s)
    return s if ok else None


def append_event(workspace_root: Path, record: dict[str, Any]) -> None:
    """Append one JSON line. No prompts or path contents — metadata only."""
    if not wizard_telemetry_enabled():
        return
    path = _telemetry_path(workspace_root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(path.parent, 0o700)
        except OSError:
            pass
        line = json.dumps(record, separators=(",", ":"), sort_keys=True)
        if path.is_file() and path.stat().st_size > _MAX_FILE_BYTES:
            return
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        return


def record_http_api_result(
    workspace_root: Path,
    *,
    api: str,
    session_id: str | None,
    out: dict[str, Any],
    started_at_mono: float,
) -> None:
    """Record one wizard HTTP handler result (duration from ``time.monotonic()`` start)."""
    if not wizard_telemetry_enabled():
        return
    duration_ms = int((time.monotonic() - started_at_mono) * 1000)
    ok = bool(out.get("ok"))
    err_c = None
    if not ok:
        raw_e = str(out.get("error") or "").strip()
        err_c = raw_e[:120] if raw_e else "unknown"
    dry = out.get("dry_run")
    dry_b = dry if isinstance(dry, bool) else None
    record_api_event(
        workspace_root,
        api=api,
        session_id=session_id,
        ok=ok,
        error_code=err_c,
        duration_ms=duration_ms,
        dry_run=dry_b,
    )


def record_api_event(
    workspace_root: Path,
    *,
    api: str,
    session_id: str | None,
    ok: bool,
    error_code: str | None = None,
    duration_ms: int | None = None,
    dry_run: bool | None = None,
) -> None:
    ev = _sanitize_event_name(api)
    if not ev:
        return
    sid = _sanitize_session_id(session_id)
    row: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "kind": "api",
        "api": ev,
        "ok": bool(ok),
    }
    if sid:
        row["session_id"] = sid
    if error_code:
        row["error_code"] = _trim(str(error_code), 120)
    if duration_ms is not None and duration_ms >= 0:
        row["duration_ms"] = int(duration_ms)
    if dry_run is not None:
        row["dry_run"] = bool(dry_run)
    append_event(workspace_root, row)


def ingest_client_event(workspace_root: Path, body: dict[str, Any]) -> dict[str, Any]:
    """
    Client POST body: ``event`` (required), optional ``session_id``, ``step_index`` (int).
    """
    if not wizard_telemetry_enabled():
        return {"ok": False, "error": "telemetry_disabled"}
    ev = _sanitize_event_name(body.get("event"))
    if not ev:
        return {"ok": False, "error": "invalid_event"}
    sid = _sanitize_session_id(body.get("session_id"))
    row: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "kind": "client",
        "event": ev,
    }
    if sid:
        row["session_id"] = sid
    raw_step = body.get("step_index")
    if isinstance(raw_step, (int, float)) and raw_step == int(raw_step):
        si = int(raw_step)
        if 0 <= si <= 64:
            row["step_index"] = si
    mm = body.get("mission_mode")
    if isinstance(mm, str) and mm.strip():
        row["mission_mode"] = _trim(mm.strip(), 48)
    append_event(workspace_root, row)
    return {"ok": True}
