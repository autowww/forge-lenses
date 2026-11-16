"""Dispatch Docs Health steps: inline (default), subprocess, or Docker."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import lenses
from lenses.docs_health import store as dh_store
from lenses.docs_health.session_steps import execute_docs_health_session_step
from lenses.sandbox.active import clear_session_handles, register_subprocess
from lenses.sandbox.backends import docs_health_step_backend, docker_cli_available
import lenses.sandbox.fleet_client as fleet_cli
from lenses.sandbox.docker_runner import (
    build_docs_health_docker_argv,
    cleanup_cidfile,
    docker_inspect_status,
    patch_tasklet_sandbox,
    record_sandbox_step_outcome,
    sandbox_cidfile_path,
    spawn_cidfile_watcher,
    tasklet_checkpoint_dir,
    write_host_heartbeat,
)


def _lenses_repo_root() -> Path:
    return Path(lenses.__file__).resolve().parent.parent


def _fleet_job_poll_loop(
    workspace_root: Path,
    tasklet_run_id: str,
    *,
    fleet_base: str,
    fleet_token: str,
    job_id: str,
    step_lc: str,
    stop: threading.Event,
) -> None:
    """Poll Forge Fleet job JSON while the main thread blocks on ``wait_for_job`` — Studio sees live updates."""
    while not stop.wait(0.45):
        snap = fleet_cli.get_job_snapshot(fleet_base, fleet_token, job_id)
        st = str(snap.get("status") or "").strip().lower()
        patch_tasklet_sandbox(
            workspace_root,
            tasklet_run_id,
            {
                "phase": "fleet_job_poll",
                "fleet_job_status": snap.get("status"),
                "fleet_job_http": snap.get("http_status"),
                "container_id": snap.get("container_id"),
                "fleet_poll_at": dh_store.now_iso(),
                "step": step_lc,
                "backend": "fleet",
            },
        )
        if st in ("completed", "failed", "cancelled"):
            break


def run_docs_health_session_step(
    workspace_root: Path,
    child: Path,
    project_slug: str,
    sess: dict[str, Any],
    step: str,
    bundle: dict[str, Any],
) -> tuple[int, dict[str, Any]]:
    """
    Run one remediation step.

    **Apply** always runs **inline** on the host so the live repo is written with host paths
    and policy — never inside a Docker sandbox.
    """
    backend = docs_health_step_backend()
    sid = str(sess.get("id") or "").strip()
    step_lc = str(step or "").strip().lower()
    tr_id = str(sess.get("tasklet_run_id") or "").strip()

    if step_lc == "apply":
        return execute_docs_health_session_step(workspace_root, child, project_slug, sess, step_lc, bundle)

    if backend == "inline":
        return execute_docs_health_session_step(workspace_root, child, project_slug, sess, step_lc, bundle)

    if step_lc != "apply" and fleet_cli.fleet_configured(workspace_root):
        ck_tid = tr_id or sid
        if tr_id:
            patch_tasklet_sandbox(
                workspace_root,
                tr_id,
                {
                    "phase": "fleet_connecting",
                    "step": step_lc,
                    "backend": "fleet",
                    "updated_at": dh_store.now_iso(),
                },
            )
        try:
            cmd = build_docs_health_docker_argv(
                workspace_root=workspace_root,
                repo_root=child.resolve(),
                lenses_repo_root=_lenses_repo_root(),
                project_slug=project_slug,
                session_id=sid,
                tasklet_run_id=ck_tid,
                step=step_lc,
                cidfile=sandbox_cidfile_path(workspace_root, sid),
            )
            if tr_id:
                patch_tasklet_sandbox(
                    workspace_root,
                    tr_id,
                    {
                        "phase": "fleet_argv_ready",
                        "fleet_argv_len": len(cmd),
                        "updated_at": dh_store.now_iso(),
                        "backend": "fleet",
                    },
                )
            job_id, fleet_base, fleet_token = fleet_cli.submit_docker_argv_job(
                workspace_root,
                argv=cmd,
                session_id=sid,
                meta={"project_slug": project_slug, "step": step_lc, "tasklet_run_id": ck_tid},
            )
            hp = fleet_cli.probe_node_health(fleet_base, fleet_token)
            host = hp.get("fleet") if isinstance(hp.get("fleet"), dict) else {}
            host_block = host.get("host") if isinstance(host.get("host"), dict) else {}
            if tr_id:
                patch_tasklet_sandbox(
                    workspace_root,
                    tr_id,
                    {
                        "phase": "fleet_job_submitted",
                        "fleet_job_id": job_id,
                        "fleet_endpoint": fleet_base,
                        "fleet_submit_at": dh_store.now_iso(),
                        "fleet_host_cpu_pct": hp.get("cpu_usage_pct"),
                        "fleet_host_mem_pct": hp.get("memory_used_pct"),
                        "fleet_server_host": host_block,
                        "updated_at": dh_store.now_iso(),
                        "backend": "fleet",
                    },
                )
            stop_poll = threading.Event()
            pol_t: threading.Thread | None = None
            if tr_id:
                pol_t = threading.Thread(
                    target=_fleet_job_poll_loop,
                    args=(workspace_root, tr_id),
                    kwargs={
                        "fleet_base": fleet_base,
                        "fleet_token": fleet_token,
                        "job_id": job_id,
                        "step_lc": step_lc,
                        "stop": stop_poll,
                    },
                    daemon=True,
                    name=f"fleet-poll-{job_id[:8]}",
                )
                pol_t.start()
            try:
                result = fleet_cli.wait_for_job(
                    workspace_root,
                    job_id,
                    fleet_base=fleet_base,
                    fleet_token=fleet_token,
                )
            finally:
                stop_poll.set()
                if pol_t is not None:
                    pol_t.join(timeout=3.0)
            if tr_id:
                patch_tasklet_sandbox(
                    workspace_root,
                    tr_id,
                    {
                        "phase": "fleet_job_finished",
                        "fleet_job_terminal_status": str(result.get("status") or ""),
                        "container_id": result.get("container_id"),
                        "fleet_finished_at": dh_store.now_iso(),
                        "backend": "fleet",
                    },
                )
        except Exception as ex:
            if tr_id:
                record_sandbox_step_outcome(
                    workspace_root,
                    tr_id,
                    step=step_lc,
                    container_id=None,
                    docker_status=None,
                    worker_ok=False,
                    error_tag="fleet_step_failed",
                )
            return (
                500,
                {
                    "ok": False,
                    "error": "fleet_step_failed",
                    "detail": str(ex)[:4000],
                },
            )
        code, body = fleet_cli.parse_step_cli_result(result)
        if tr_id:
            record_sandbox_step_outcome(
                workspace_root,
                tr_id,
                step=step_lc,
                container_id=str(result.get("container_id") or "") or None,
                docker_status=str(result.get("status") or "") or None,
                worker_ok=code < 500 and isinstance(body, dict) and bool(body.get("ok", True)),
                error_tag=None if code < 500 else "fleet_http_error",
            )
        if isinstance(body, dict):
            return code, body
        return code, {"ok": False, "error": "invalid_worker_payload"}

    use_docker = backend == "docker" and docker_cli_available()
    env = os.environ.copy()
    if bundle.get("effective_readonly"):
        env["LENSES_STEP_EFFECTIVE_READONLY"] = "1"

    if use_docker:
        cidfile = sandbox_cidfile_path(workspace_root, sid)
        cleanup_cidfile(cidfile)
        ck_tid = tr_id or sid
        if tr_id:
            patch_tasklet_sandbox(
                workspace_root,
                tr_id,
                {
                    "phase": "starting",
                    "step": step_lc,
                    "backend": "docker",
                    "updated_at": dh_store.now_iso(),
                },
            )
        cmd = build_docs_health_docker_argv(
            workspace_root=workspace_root,
            repo_root=child.resolve(),
            lenses_repo_root=_lenses_repo_root(),
            project_slug=project_slug,
            session_id=sid,
            tasklet_run_id=ck_tid,
            step=step_lc,
            cidfile=cidfile,
        )
        stop_ev = threading.Event()
        _t, join_watcher = spawn_cidfile_watcher(cidfile, sid, stop_ev)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        register_subprocess(sid, proc)
        container_id: str | None = None
        try:
            out, err = proc.communicate(timeout=3600)
        finally:
            join_watcher()
            try:
                if cidfile.is_file():
                    container_id = cidfile.read_text(encoding="utf-8").strip() or None
            except OSError:
                container_id = None
            ck = tasklet_checkpoint_dir(workspace_root, ck_tid)
            dst = docker_inspect_status(container_id) if container_id else None
            write_host_heartbeat(
                ck,
                step=step_lc,
                container_id=container_id,
                status=dst or "unknown",
            )
            clear_session_handles(sid)
            cleanup_cidfile(cidfile)

        if proc.returncode not in (0, 1):
            err_detail = (err or out or "")[:4000]
            if tr_id:
                record_sandbox_step_outcome(
                    workspace_root,
                    tr_id,
                    step=step_lc,
                    container_id=container_id,
                    docker_status=docker_inspect_status(container_id) if container_id else None,
                    worker_ok=False,
                    error_tag="docker_step_failed",
                )
            return (
                500,
                {
                    "ok": False,
                    "error": "docker_step_failed",
                    "detail": err_detail,
                },
            )
        try:
            line = (out or "").strip().splitlines()[-1]
            parsed = json.loads(line)
        except (json.JSONDecodeError, IndexError):
            if tr_id:
                record_sandbox_step_outcome(
                    workspace_root,
                    tr_id,
                    step=step_lc,
                    container_id=container_id,
                    docker_status=None,
                    worker_ok=False,
                    error_tag="step_worker_bad_output",
                )
            return (
                500,
                {
                    "ok": False,
                    "error": "step_worker_bad_output",
                    "detail": (out or "")[:2000],
                },
            )
        code = int(parsed.get("http_status") or 500)
        body = parsed.get("body")
        if tr_id:
            record_sandbox_step_outcome(
                workspace_root,
                tr_id,
                step=step_lc,
                container_id=container_id,
                docker_status=docker_inspect_status(container_id) if container_id else None,
                worker_ok=code < 500 and bool(parsed.get("ok")),
                error_tag=None if code < 500 else "step_http_error",
            )
        if isinstance(body, dict):
            return code, body
        return code, {"ok": False, "error": "invalid_worker_payload"}

    # process backend
    argv_tail = [
        "--workspace-root",
        str(workspace_root.resolve()),
        "--project-slug",
        project_slug,
        "--session-id",
        sid,
        "--step",
        step_lc,
        "--repo-root",
        str(child.resolve()),
    ]
    cmd = [
        sys.executable,
        "-m",
        "lenses.docs_health.step_cli",
        *argv_tail,
    ]
    if bundle.get("can_write_project") and step_lc == "apply":
        env["LENSES_STEP_BUNDLE_WRITE"] = "1"
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    register_subprocess(sid, proc)
    try:
        out, err = proc.communicate(timeout=3600)
    finally:
        clear_session_handles(sid)

    if proc.returncode not in (0, 1):
        tag = "step_worker_failed"
        return (
            500,
            {
                "ok": False,
                "error": tag,
                "detail": (err or out or "")[:4000],
            },
        )
    try:
        line = (out or "").strip().splitlines()[-1]
        parsed = json.loads(line)
    except (json.JSONDecodeError, IndexError):
        return (
            500,
            {
                "ok": False,
                "error": "step_worker_bad_output",
                "detail": (out or "")[:2000],
            },
        )
    code = int(parsed.get("http_status") or 500)
    body = parsed.get("body")
    if isinstance(body, dict):
        return code, body
    return code, {"ok": False, "error": "invalid_worker_payload"}
