"""Run Doc Management hydration pipeline: v1 agent + v2 workcell."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from lenses.doc_management import session_store as store

_AGENT_SCRIPT = "scripts/doc_hydration_agent.py"


def _find_platform_root(workspace_root: Path) -> Path:
    p = workspace_root / "forge-platform"
    if not (p / _AGENT_SCRIPT).is_file():
        raise FileNotFoundError("forge-platform doc_hydration_agent missing")
    return p


def _find_workcells_cmd(workspace_root: Path) -> tuple[Path, list[str], dict[str, str]]:
    wc_root = workspace_root / "forge-workcells"
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(wc_root / "src")
        + os.pathsep
        + str(workspace_root / "forge-lcdl" / "src")
        + os.pathsep
        + env.get("PYTHONPATH", "")
    )
    venv_cli = wc_root / ".venv" / "bin" / "forge-workcells"
    if venv_cli.is_file():
        return wc_root, [str(venv_cli)], env
    py = _python_for_repo(workspace_root, "forge-workcells")
    return wc_root, [py, "-m", "forge_workcells.cli"], env


def _python_for_repo(workspace_root: Path, repo_name: str) -> str:
    venv = workspace_root / repo_name / ".venv" / "bin" / "python3"
    if venv.is_file():
        return str(venv)
    return sys.executable


def _run_subprocess(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _seed_paths(session: dict[str, Any], workspace_root: Path, session_id: str) -> list[Path]:
    intake = session.get("intake") if isinstance(session.get("intake"), dict) else {}
    seeds = intake.get("seeds") if isinstance(intake.get("seeds"), list) else []
    root = store.session_dir(workspace_root, session_id)
    out: list[Path] = []
    for row in seeds:
        if not isinstance(row, dict):
            continue
        rel = str(row.get("path") or "").strip()
        if not rel:
            continue
        p = root / rel
        if p.is_file():
            out.append(p)
    return out


def run_hydration_pipeline(workspace_root: Path, session_id: str) -> dict[str, Any]:
    sess = store.load_session(workspace_root, session_id)
    if not sess:
        raise ValueError("session_not_found")
    if sess.get("status") == "cancelled":
        raise ValueError("session_cancelled")

    seeds = _seed_paths(sess, workspace_root, session_id)
    if not seeds:
        raise ValueError("no_seeds")

    platform = _find_platform_root(workspace_root)
    pack_root = store.pack_dir(workspace_root, session_id)
    pack_root.mkdir(parents=True, exist_ok=True)
    wizard = sess.get("wizard") if isinstance(sess.get("wizard"), dict) else {}
    use_llm = bool(wizard.get("use_llm"))
    persona = str(wizard.get("persona") or "architect")
    surfaces = wizard.get("target_surfaces") if isinstance(wizard.get("target_surfaces"), list) else []
    target_surface = str(surfaces[0]) if surfaces else "forge_platform_architecture"

    sess["status"] = "running"
    workflow = sess.setdefault("workflow", {})
    if not isinstance(workflow, dict):
        workflow = {}
        sess["workflow"] = workflow
    workflow["stage"] = "route_and_draft"
    store.append_event(sess, {"type": "run_start", "title": "Hydration pipeline started", "seed_count": len(seeds)})
    store.save_session(workspace_root, sess)

    agent_py = _python_for_repo(workspace_root, "forge-platform")
    metrics: list[dict[str, Any]] = []
    run_dirs: list[str] = []

    for seed in seeds:
        slug = seed.stem
        out_dir = pack_root / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [agent_py, str(platform / _AGENT_SCRIPT), str(seed), "--out-dir", str(out_dir)]
        code, stdout, stderr = _run_subprocess(cmd, cwd=platform)
        metrics.append(
            {
                "step": "route_and_draft",
                "seed": seed.name,
                "exit_code": code,
                "elapsed_ms": 0,
            }
        )
        store.append_event(
            sess,
            {
                "type": "agent_step",
                "title": f"Route & draft: {seed.name}",
                "exit_code": code,
                "stdout_tail": (stdout or "")[-2000:],
                "stderr_tail": (stderr or "")[-2000:],
            },
        )
        if code != 0:
            sess["status"] = "failed"
            workflow["stage"] = "route_and_draft"
            sess["step_metrics"] = metrics
            store.save_session(workspace_root, sess)
            raise RuntimeError(f"doc_hydration_agent failed for {seed.name}: {stderr[-500:]}")

        # Workcell: claims + brief
        workflow["stage"] = "extract_claims"
        store.save_session(workspace_root, sess)
        request = {
            "schema": "forge.workcell_request.v1",
            "forge_run_id": sess.get("forge_run_id"),
            "workcell": "doc_hydration_worker",
            "role": "implementation_worker",
            "mode": "proposal",
            "launch_pack": {
                "seed_path": str(seed),
                "target_surface": target_surface,
                "persona": persona,
                "use_llm": use_llm,
            },
        }
        req_path = out_dir / "workcell-request.json"
        req_path.write_text(json.dumps(request, indent=2), encoding="utf-8")
        wc_root, wc_argv, env = _find_workcells_cmd(workspace_root)
        wc_out = out_dir / "workcell-out"
        wc_out.mkdir(parents=True, exist_ok=True)
        wc_cmd = wc_argv + [
            "run",
            "--workcell",
            "doc_hydration_worker",
            "--request",
            str(req_path),
            "--out-dir",
            str(wc_out),
        ]
        code2, stdout2, stderr2 = _run_subprocess(wc_cmd, cwd=wc_root, env=env)
        metrics.append({"step": "extract_claims", "seed": seed.name, "exit_code": code2, "elapsed_ms": 0})
        store.append_event(
            sess,
            {
                "type": "workcell_step",
                "title": f"Claim extraction: {seed.name}",
                "exit_code": code2,
                "stderr_tail": (stderr2 or "")[-2000:],
            },
        )
        if code2 != 0:
            sess["status"] = "failed"
            sess["step_metrics"] = metrics
            store.save_session(workspace_root, sess)
            raise RuntimeError(f"doc_hydration_worker failed for {seed.name}: {stderr2[-500:]}")
        run_dirs.append(str(out_dir.relative_to(store.session_dir(workspace_root, session_id))))

    workflow["stage"] = "review"
    workflow["stages_completed"] = ["intake", "route_and_draft", "extract_claims"]
    sess["status"] = "awaiting_approval"
    sess["step_metrics"] = metrics
    sess["pack_runs"] = run_dirs
    store.append_event(sess, {"type": "awaiting_approval", "title": "Ready for reviewer decisions"})
    store.save_session(workspace_root, sess)
    return sess
