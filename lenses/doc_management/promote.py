"""Promotion and rollback helpers — invoke forge-platform scripts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from lenses.doc_management import session_store as store

_PROMOTE_SCRIPT = "scripts/promote_session_pack.py"
_ROLLBACK_SCRIPT = "scripts/rollback_session_promotion.py"
_GATES_SCRIPT = "scripts/check_quality_gates.py"


def _platform_root(workspace_root: Path) -> Path:
    p = workspace_root / "forge-platform"
    if not p.is_dir():
        raise FileNotFoundError("forge-platform missing")
    return p


def _python(workspace_root: Path) -> str:
    venv = workspace_root / "forge-platform" / ".venv" / "bin" / "python3"
    return str(venv) if venv.is_file() else sys.executable


def _run(cmd: list[str], *, cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def check_manifest_gate(workspace_root: Path, session_id: str) -> tuple[bool, str]:
    platform = _platform_root(workspace_root)
    pack = store.pack_dir(workspace_root, session_id)
    py = _python(workspace_root)
    code, out, err = _run(
        [py, str(platform / _GATES_SCRIPT), "--pack-root", str(pack), "--gates", "G3"],
        cwd=platform,
    )
    if code != 0:
        return False, (err or out or "gate_failed")[-2000:]
    return True, out[-500:]


def promote_session(
    workspace_root: Path,
    session_id: str,
    *,
    dry_run: bool = True,
    surfaces: list[str] | None = None,
) -> dict[str, Any]:
    sess = store.load_session(workspace_root, session_id)
    if not sess:
        raise ValueError("session_not_found")
    ok, gate_msg = check_manifest_gate(workspace_root, session_id)
    if not ok:
        raise ValueError(f"quality_gate_failed:{gate_msg}")

    platform = _platform_root(workspace_root)
    pack = store.pack_dir(workspace_root, session_id)
    wizard = sess.get("wizard") if isinstance(sess.get("wizard"), dict) else {}
    surface_list = surfaces or wizard.get("target_surfaces") or []
    if not isinstance(surface_list, list):
        surface_list = []
    py = _python(workspace_root)
    cmd = [
        py,
        str(platform / _PROMOTE_SCRIPT),
        "--pack-root",
        str(pack),
        "--workspace-root",
        str(workspace_root),
        "--session-id",
        session_id,
    ]
    if surface_list:
        cmd.extend(["--surfaces", ",".join(str(s) for s in surface_list)])
    if dry_run:
        cmd.append("--dry-run")
    else:
        cmd.extend(["--apply", "--promotion-dir", str(store.promotion_dir(workspace_root, session_id))])
    code, stdout, stderr = _run(cmd, cwd=platform)
    result = {
        "ok": code == 0,
        "dry_run": dry_run,
        "exit_code": code,
        "stdout": stdout[-8000:],
        "stderr": stderr[-4000:],
    }
    try:
        lines = [ln for ln in stdout.splitlines() if ln.strip().startswith("{")]
        if lines:
            result["report"] = json.loads(lines[-1])
    except json.JSONDecodeError:
        pass
    if not dry_run and code == 0:
        workflow = sess.setdefault("workflow", {})
        if isinstance(workflow, dict):
            workflow["stage"] = "verify"
            completed = workflow.get("stages_completed")
            if isinstance(completed, list):
                for st in ("promote", "verify"):
                    if st not in completed:
                        completed.append(st)
        sess["status"] = "completed"
        store.append_event(sess, {"type": "promoted", "title": "Promotion applied"})
        store.save_session(workspace_root, sess)
    else:
        store.append_event(
            sess,
            {
                "type": "promote_dry_run" if dry_run else "promote_failed",
                "title": "Promotion dry-run" if dry_run else "Promotion failed",
                "exit_code": code,
            },
        )
        store.save_session(workspace_root, sess)
    return result


def rollback_session(workspace_root: Path, session_id: str) -> dict[str, Any]:
    sess = store.load_session(workspace_root, session_id)
    if not sess:
        raise ValueError("session_not_found")
    platform = _platform_root(workspace_root)
    promotion = store.promotion_dir(workspace_root, session_id)
    py = _python(workspace_root)
    cmd = [
        py,
        str(platform / _ROLLBACK_SCRIPT),
        "--promotion-dir",
        str(promotion),
        "--workspace-root",
        str(workspace_root),
    ]
    code, stdout, stderr = _run(cmd, cwd=platform)
    result = {"ok": code == 0, "exit_code": code, "stdout": stdout[-4000:], "stderr": stderr[-2000:]}
    if code == 0:
        sess["status"] = "rolled_back"
        store.append_event(sess, {"type": "rolled_back", "title": "Promotion rolled back"})
        store.save_session(workspace_root, sess)
    return result
