"""Durable append-only event log per TaskletRun (JSONL)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from lenses.docs_health import store as dh_store


def run_events_path(workspace_root: Path, run_id: str) -> Path:
    safe = str(run_id or "").strip().replace(os.sep, "_").replace("/", "_")
    if not safe or ".." in safe:
        raise ValueError("invalid_tasklet_run_id")
    d = workspace_root.resolve() / ".lenses-local" / "tasklet-runs" / safe
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d.parent.parent, 0o700)
        os.chmod(d.parent, 0o700)
        os.chmod(d, 0o700)
    except OSError:
        pass
    return d / "events.jsonl"


def append_session_events(
    workspace_root: Path,
    run_id: str,
    *,
    base_seq: int,
    events: list[dict[str, Any]],
) -> int:
    """Append timeline rows; each ``events`` item is merged into SessionEvent. Returns next seq."""
    if not events:
        return base_seq
    p = run_events_path(workspace_root, run_id)
    next_seq = base_seq
    with p.open("a", encoding="utf-8") as fh:
        for raw in events:
            if not isinstance(raw, dict):
                continue
            next_seq += 1
            row = {
                "seq": next_seq,
                "ts": str(raw.get("ts") or dh_store.now_iso()),
                "kind": str(raw.get("kind") or "timeline"),
                "payload": {k: v for k, v in raw.items() if k not in ("seq", "ts", "kind")},
            }
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    return next_seq


def load_session_events(workspace_root: Path, run_id: str) -> list[dict[str, Any]]:
    p = run_events_path(workspace_root, run_id)
    if not p.is_file():
        return []
    out: list[dict[str, Any]] = []
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                out.append(obj)
    except OSError:
        return []
    out.sort(key=lambda x: int(x.get("seq") or 0))
    return out


def timeline_payloads_for_docs_health(session_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten JSONL rows into docs-health timeline shape (payload + seq/ts)."""
    merged: list[dict[str, Any]] = []
    for ev in session_events:
        if not isinstance(ev, dict):
            continue
        kind = str(ev.get("kind") or "")
        pl = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
        if kind == "timeline" or "type" in pl:
            row = dict(pl)
            row.setdefault("ts", ev.get("ts"))
            merged.append(row)
    return merged
