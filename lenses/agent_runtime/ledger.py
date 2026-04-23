"""Append-only token ledger (JSON lines) + rollups."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lenses.agent_runtime.types import ModelCallRecord

LEDGER_NAME = "token-ledger.jsonl"


def _runtime_dir(workspace_root: Path) -> Path:
    d = workspace_root.resolve() / ".lenses-local" / "agent-runtime"
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d.parent, 0o700)
        os.chmod(d, 0o700)
    except OSError:
        pass
    return d


def ledger_path(workspace_root: Path) -> Path:
    return _runtime_dir(workspace_root) / LEDGER_NAME


def append_model_call(workspace_root: Path, record: ModelCallRecord) -> None:
    p = ledger_path(workspace_root)
    line = json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n"
    with p.open("a", encoding="utf-8") as fh:
        fh.write(line)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def merge_usage_into_session_file(workspace_root: Path, session_id: str, delta: dict[str, Any]) -> None:
    from lenses.agent_runtime import sessions as sess_mod  # noqa: PLC0415

    sess = sess_mod.load_session(workspace_root, session_id)
    if not sess:
        return
    u = sess.setdefault("usage", {})
    u["calls"] = int(u.get("calls") or 0) + int(delta.get("calls") or 0)
    u["prompt_tokens"] = int(u.get("prompt_tokens") or 0) + int(delta.get("prompt_tokens") or 0)
    u["completion_tokens"] = int(u.get("completion_tokens") or 0) + int(delta.get("completion_tokens") or 0)
    u["total_tokens"] = int(u.get("total_tokens") or 0) + int(delta.get("total_tokens") or 0)
    u["estimated"] = bool(u.get("estimated")) or bool(delta.get("estimated"))
    if delta.get("last_slot"):
        u["last_slot"] = delta.get("last_slot")
    if delta.get("last_endpoint"):
        u["last_endpoint"] = delta.get("last_endpoint")
    by_slot = u.setdefault("by_slot", {})
    slot = str(delta.get("last_slot") or "_")
    cur = by_slot.get(slot) if isinstance(by_slot.get(slot), dict) else {}
    by_slot[slot] = {
        "calls": int(cur.get("calls") or 0) + int(delta.get("calls") or 0),
        "prompt_tokens": int(cur.get("prompt_tokens") or 0) + int(delta.get("prompt_tokens") or 0),
        "completion_tokens": int(cur.get("completion_tokens") or 0) + int(delta.get("completion_tokens") or 0),
        "total_tokens": int(cur.get("total_tokens") or 0) + int(delta.get("total_tokens") or 0),
    }
    sess["updated_at"] = datetime.now(timezone.utc).isoformat()
    sess_mod.save_session(workspace_root, sess)


def read_ledger_tail(workspace_root: Path, *, max_lines: int = 800) -> list[dict[str, Any]]:
    p = ledger_path(workspace_root)
    if not p.is_file():
        return []
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in lines[-max_lines:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def summarize_ledger(
    workspace_root: Path,
    *,
    session_id: str | None = None,
    project_slug: str | None = None,
    scan_run_id: str | None = None,
) -> dict[str, Any]:
    rows = read_ledger_tail(workspace_root, max_lines=2000)
    tot = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "estimated_rows": 0}
    by_slot: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    matched: list[dict[str, Any]] = []
    for r in rows:
        if session_id and str(r.get("session_id") or "") != session_id:
            continue
        if project_slug and str(r.get("project_slug") or "") != project_slug:
            continue
        if scan_run_id and str(r.get("scan_run_id") or "") != scan_run_id:
            continue
        matched.append(r)
        if not r.get("ok", True):
            continue
        tot["calls"] += 1
        tot["prompt_tokens"] += int(r.get("input_tokens") or 0)
        tot["completion_tokens"] += int(r.get("output_tokens") or 0)
        tot["total_tokens"] += int(r.get("total_tokens") or 0)
        if str(r.get("token_counting_mode")) == "estimated":
            tot["estimated_rows"] += 1
        sl = str(r.get("model_slot") or "_")
        by_slot[sl]["calls"] += 1
        by_slot[sl]["prompt_tokens"] += int(r.get("input_tokens") or 0)
        by_slot[sl]["completion_tokens"] += int(r.get("output_tokens") or 0)
        by_slot[sl]["total_tokens"] += int(r.get("total_tokens") or 0)
    last = matched[-1] if matched else None
    return {
        "ok": True,
        "filter": {"session_id": session_id, "project_slug": project_slug, "scan_run_id": scan_run_id},
        "totals": tot,
        "by_slot": dict(by_slot),
        "last_record": last,
        "rows_considered": len(matched),
    }
