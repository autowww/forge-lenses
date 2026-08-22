"""Forge Platform Self-Host: read and lightly mutate `.forge/runs/` bundles."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_FORGE_RUN_ID = re.compile(r"^frun_[A-Za-z0-9_.:-]+$")

DECISION_STATES = frozenset(
    {"draft", "proposed", "approved", "rejected", "deferred", "superseded"}
)


def _safe_run_dir(repo_root: Path, forge_run_id: str) -> Path | None:
    if not _FORGE_RUN_ID.match(forge_run_id):
        return None
    root = repo_root.resolve()
    run_dir = (root / ".forge" / "runs" / forge_run_id).resolve()
    try:
        run_dir.relative_to(root)
    except ValueError:
        return None
    if not run_dir.is_dir():
        return None
    return run_dir


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_if_present(path: Path) -> Any | None:
    if not path.is_file():
        return None
    try:
        return _read_json(path)
    except Exception:
        return None


def list_forge_runs(repo_root: Path) -> dict[str, Any]:
    runs_root = repo_root / ".forge" / "runs"
    if not runs_root.is_dir():
        return {"ok": True, "runs": [], "runs_root": ".forge/runs"}
    out = []
    for p in sorted(runs_root.iterdir()):
        if not p.is_dir() or not _FORGE_RUN_ID.match(p.name):
            continue
        summary = None
        fr = p / "forge_run.json"
        if fr.is_file():
            try:
                summary = _read_json(fr)
            except Exception:
                summary = {"error": "invalid_forge_run_json"}
        out.append({"forge_run_id": p.name, "forge_run": summary})
    return {"ok": True, "runs": out, "runs_root": ".forge/runs"}


def load_forge_run_bundle(repo_root: Path, forge_run_id: str) -> dict[str, Any]:
    run_dir = _safe_run_dir(repo_root, forge_run_id)
    if run_dir is None:
        return {"ok": False, "error": "run_not_found"}
    approvals_dir = run_dir / "approvals"
    approvals = {}
    if approvals_dir.is_dir():
        for ap in sorted(approvals_dir.glob("*.json")):
            data = _load_if_present(ap)
            if isinstance(data, dict) and data.get("approval_id"):
                approvals[str(data["approval_id"])] = data
    bundle = {
        "forge_run_id": forge_run_id,
        "forge_run": _load_if_present(run_dir / "forge_run.json"),
        "approvals": approvals,
        "evidence_packet": _load_if_present(run_dir / "evidence" / "evidence_packet.json"),
        "local_runner_result": _load_if_present(run_dir / "local-runner" / "result.json"),
        "follow_on_sparks": _load_if_present(run_dir / "follow_on_sparks.json"),
        "events_tail": _tail_ndjson(run_dir / "events.ndjson", max_lines=40),
    }
    return {"ok": True, "bundle": bundle, "run_dir": str(run_dir.relative_to(repo_root))}


def _tail_ndjson(path: Path, *, max_lines: int) -> list[Any]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out: list[Any] = []
    for line in lines[-max_lines:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            out.append({"raw": line[:500]})
    return out


def patch_for_decision(
    repo_root: Path,
    forge_run_id: str,
    *,
    state: str,
    human_owner: str | None = None,
) -> dict[str, Any]:
    if state not in DECISION_STATES:
        return {"ok": False, "error": "invalid_decision_state"}
    run_dir = _safe_run_dir(repo_root, forge_run_id)
    if run_dir is None:
        return {"ok": False, "error": "run_not_found"}
    fr_path = run_dir / "forge_run.json"
    if not fr_path.is_file():
        return {"ok": False, "error": "missing_forge_run"}
    try:
        fr = _read_json(fr_path)
    except Exception as exc:
        return {"ok": False, "error": f"invalid_forge_run_json:{exc}"}
    dec = fr.get("decision")
    if not isinstance(dec, dict):
        dec = {}
    dec["state"] = state
    if human_owner is not None:
        dec["human_owner"] = human_owner
    fr["decision"] = dec
    fr_path.write_text(json.dumps(fr, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "forge_run": fr}
