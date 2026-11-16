"""HTTP handlers for ``/api/deploy/*``."""

from __future__ import annotations

import urllib.parse
from pathlib import Path
from typing import Any, Callable

from lenses.deploy_orchestrator import fleet_deploy_client
from lenses.deploy_orchestrator.audit import append_audit
from lenses.deploy_orchestrator.feature_flag import experimental_deploy_orchestration_enabled
from lenses.deploy_orchestrator.gates import attest_manual_gate, run_gates_for_release
from lenses.deploy_orchestrator.locks import acquire_lock, release_lock
from lenses.deploy_orchestrator.pipeline_spec import (
    discover_pipeline_paths,
    discover_pipelines,
    load_pipeline_for_project,
)
from lenses.deploy_orchestrator.promote import promote_release
from lenses.deploy_orchestrator.reconcile import reconcile_project
from lenses.deploy_orchestrator.rollback import rollback_release
from lenses.deploy_orchestrator.state import create_release, get_release, load_state, public_state_payload, update_release

SendJson = Callable[[int, dict[str, Any]], None]


def _disabled() -> dict[str, Any]:
    return {"ok": False, "feature_disabled": True}


def handle_deploy_get(
    *,
    workspace_root: Path,
    path: str,
    send_json: SendJson,
) -> bool:
    p = path.rstrip("/") or "/"
    if not p.startswith("/api/deploy"):
        return False
    if p == "/api/deploy/enabled":
        send_json(200, {"ok": True, "enabled": experimental_deploy_orchestration_enabled()})
        return True
    if not experimental_deploy_orchestration_enabled():
        send_json(200, _disabled())
        return True
    parsed = urllib.parse.urlparse(path)
    qs = urllib.parse.parse_qs(parsed.query)
    project = (qs.get("project") or [""])[0].strip()
    if p == "/api/deploy/pipeline":
        if not project:
            send_json(400, {"ok": False, "error": "project_required"})
            return True
        pipeline_id = (qs.get("pipeline_id") or ["default"])[0].strip() or "default"
        send_json(200, load_pipeline_for_project(workspace_root, project, pipeline_id=pipeline_id))
        return True
    if p == "/api/deploy/pipelines":
        if not project:
            send_json(400, {"ok": False, "error": "project_required"})
            return True
        grouped = discover_pipelines(workspace_root).get(project, {})
        send_json(
            200,
            {
                "ok": True,
                "project": project,
                "pipelines": {pid: str(path) for pid, path in grouped.items()},
            },
        )
        return True
    if p == "/api/deploy/environment-health":
        from lenses.environment_health.aggregate import probe_health_url, rollup_environment_health

        urls = qs.get("url") or []
        bearer = (qs.get("bearer") or [""])[0]
        probes = [probe_health_url(u, bearer=bearer) for u in urls if u.strip()]
        send_json(200, {"ok": True, **rollup_environment_health(probes)})
        return True
    if p == "/api/deploy/state":
        if not project:
            send_json(400, {"ok": False, "error": "project_required"})
            return True
        payload = public_state_payload(workspace_root, project=project)
        payload["discovered"] = list(discover_pipeline_paths(workspace_root).keys())
        payload["reconcile"] = reconcile_project(workspace_root, project=project)
        send_json(200, payload)
        return True
    send_json(404, {"ok": False, "error": "not_found"})
    return True


def handle_deploy_post(
    *,
    workspace_root: Path,
    post_path: str,
    body: dict[str, Any],
    send_json: SendJson,
    may_run_actions: Callable[[str], bool],
    client_ip: str,
) -> bool:
    p = post_path.rstrip("/") or "/"
    if not p.startswith("/api/deploy"):
        return False
    if not experimental_deploy_orchestration_enabled():
        send_json(200, _disabled())
        return True
    if not may_run_actions(client_ip):
        send_json(403, {"ok": False, "error": "allowed_from_loopback_or_lenses_allow_actions"})
        return True

    if p == "/api/deploy/deploy":
        project = str(body.get("project") or "").strip()
        environment = str(body.get("environment") or "").strip()
        ref = str(body.get("ref") or "").strip()
        digest = str(body.get("digest") or ref or "").strip()
        if not project or not environment:
            send_json(400, {"ok": False, "error": "project_and_environment_required"})
            return True
        pl = load_pipeline_for_project(workspace_root, project)
        if not pl.get("ok"):
            send_json(400, pl)
            return True
        release = create_release(workspace_root, project=project, environment=environment, digest=digest, ref=ref)
        ok_lock, holder = acquire_lock(workspace_root, environment=environment, release_id=release["id"])
        if not ok_lock:
            send_json(409, {"ok": False, "error": "deploy_lock_held", "holder": holder})
            return True
        env_row = next(
            (
                e
                for e in (pl["pipeline"].get("environments") or [])
                if isinstance(e, dict) and str(e.get("id") or "") == environment
            ),
            None,
        )
        overrides: dict[str, Any] = {"forge_market_env": environment}
        if ref:
            overrides["forge_market_git_ref"] = ref
        if digest:
            repo = str((pl["pipeline"].get("artifact") or {}).get("repository") or "forge-market-app")
            overrides["forge_market_app_image"] = f"{repo}:{digest[:12]}"
        if env_row:
            overrides["forge_market_studio_host_port"] = str(env_row.get("host_port") or "")
            overrides["forge_market_studio_root"] = str(env_row.get("compose_root") or "")
        rollout = fleet_deploy_client.post_market_studio_rollout(workspace_root, overrides=overrides, sync=False)
        update_release(
            workspace_root,
            release["id"],
            status="deploying" if rollout.get("ok") else "deploy_failed",
            fleet_rollout=rollout,
        )
        gate_result = run_gates_for_release(workspace_root, project=project, release_id=release["id"])
        release_lock(workspace_root, environment=environment, release_id=release["id"])
        append_audit(workspace_root, "deploy", payload={"release_id": release["id"], "rollout": rollout})
        send_json(200, {"ok": rollout.get("ok", False), "release": release, "rollout": rollout, "gates": gate_result})
        return True

    if p == "/api/deploy/gates/run":
        release_id = str(body.get("release_id") or "").strip()
        gate_id = str(body.get("gate_id") or "").strip() or None
        doc = load_state(workspace_root)
        release = get_release(doc, release_id) if release_id else None
        if release is None:
            send_json(404, {"ok": False, "error": "release_not_found"})
            return True
        out = run_gates_for_release(
            workspace_root,
            project=str(release.get("project") or ""),
            release_id=release_id,
            gate_id=gate_id,
        )
        send_json(200, out)
        return True

    if p == "/api/deploy/gates/attest":
        release_id = str(body.get("release_id") or "").strip()
        gate_id = str(body.get("gate_id") or "").strip()
        note = str(body.get("note") or "")
        doc = load_state(workspace_root)
        release = get_release(doc, release_id) if release_id else None
        if release is None or not gate_id:
            send_json(400, {"ok": False, "error": "release_id_and_gate_id_required"})
            return True
        out = attest_manual_gate(
            workspace_root,
            release_id=release_id,
            gate_id=gate_id,
            digest=str(release.get("digest") or ""),
            note=note,
        )
        send_json(200, out)
        return True

    if p == "/api/deploy/promote":
        out = promote_release(
            workspace_root,
            release_id=str(body.get("release_id") or "").strip(),
            from_env=str(body.get("from") or "").strip(),
            to_env=str(body.get("to") or "").strip(),
            confirm_human_approval=bool(body.get("confirm_human_approval")),
        )
        code = 400 if out.get("error") == "confirm_human_approval_required" else (200 if out.get("ok") else 400)
        send_json(code, out)
        return True

    if p == "/api/deploy/rollback":
        out = rollback_release(
            workspace_root,
            release_id=str(body.get("release_id") or "").strip(),
            tier_ack=str(body.get("tier_ack") or "") or None,
        )
        send_json(200 if out.get("ok") else 400, out)
        return True

    send_json(404, {"ok": False, "error": "not_found"})
    return True
