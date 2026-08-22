"""Build ``GET /api/cicd/control-tower`` from workspace scan + local / demo fixtures."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from lenses.cicd_orchestration.adapters.argo_cd import normalize_argo_application_sync
from lenses.cicd_orchestration.adapters.azure_pipelines import normalize_azure_pipeline_run
from lenses.cicd_orchestration.adapters.github_actions import normalize_github_actions_run
from lenses.cicd_orchestration.adapters.gitlab_ci import normalize_gitlab_ci_pipeline
from lenses.cicd_orchestration.adapters.jenkins import normalize_jenkins_build
from lenses.cicd_orchestration.feature_flag import experimental_cicd_orchestration_enabled
from lenses.cicd_orchestration.local_store import load_demo_fixture, read_local_cicd_orchestration
from lenses.cicd_orchestration.normalized import SCHEMA_VERSION, empty_control_tower
from lenses.devsecops_compliance.cicd_integration import merge_devsecops_into_control_tower_payload
from lenses.test_quality.cicd_merge import extend_blocked_promotions_with_quality_gates


def _lenses_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _truthy_env(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _load_doc(workspace_root: Path) -> dict[str, Any] | None:
    doc = read_local_cicd_orchestration(workspace_root)
    if doc is not None:
        return doc
    if _truthy_env("LENSES_CICD_ORCHESTRATION_SEED_DEMO"):
        return load_demo_fixture(_lenses_root())
    return None


def _normalize_pipeline(provider: str, raw: dict[str, Any], project: str) -> dict[str, Any]:
    p = provider.strip().lower().replace("-", "_")
    if p in ("github_actions", "github"):
        return normalize_github_actions_run(raw, project=project)
    if p in ("gitlab_ci", "gitlab"):
        return normalize_gitlab_ci_pipeline(raw, project=project)
    if p in ("azure_pipelines", "azure", "ado"):
        return normalize_azure_pipeline_run(raw, project=project)
    if p == "jenkins":
        return normalize_jenkins_build(raw, project=project)
    if p in ("argo_cd", "argocd", "argo"):
        return normalize_argo_application_sync(raw, project=project)
    return normalize_github_actions_run(raw, project=project)


def _merge_blocked_promotions(doc: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen_key: set[str] = set()
    for row in doc.get("blocked_promotions") or []:
        if not isinstance(row, dict):
            continue
        pid = str(row.get("promotion_id") or "")
        reason = str(row.get("reason") or "")
        key = f"{pid}:{reason}"
        if key in seen_key:
            continue
        seen_key.add(key)
        out.append(dict(row))

    for prom in doc.get("promotions") or []:
        if not isinstance(prom, dict):
            continue
        pid = str(prom.get("id") or "")
        br = str(prom.get("blocked_reason") or "").strip()
        if pid and br:
            key = f"{pid}:{br}"
            if key not in seen_key:
                seen_key.add(key)
                out.append(
                    {
                        "promotion_id": pid,
                        "reason": "promotion_blocked",
                        "detail": br,
                    }
                )

    freezes = [f for f in doc.get("freeze_windows") or [] if isinstance(f, dict) and f.get("active")]
    for prom in doc.get("promotions") or []:
        if not isinstance(prom, dict):
            continue
        pid = str(prom.get("id") or "")
        to_env = str(prom.get("to_env") or "")
        if not pid:
            continue
        for fw in freezes:
            blocked_to = fw.get("blocks_promotion_to") or []
            if isinstance(blocked_to, list) and to_env in blocked_to:
                key = f"{pid}:freeze_window"
                if key not in seen_key:
                    seen_key.add(key)
                    out.append(
                        {
                            "promotion_id": pid,
                            "reason": "freeze_window",
                            "detail": str(fw.get("name") or "active freeze"),
                        }
                    )
                break
    return out


def _what_is_live(environments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for e in environments:
        if not isinstance(e, dict):
            continue
        rows.append(
            {
                "environment_id": str(e.get("id") or ""),
                "display_name": str(e.get("display_name") or e.get("id") or ""),
                "tier": str(e.get("tier") or ""),
                "version": str(e.get("current_version") or ""),
                "artifact_ref": str(e.get("current_artifact_ref") or ""),
                "last_successful_deploy_at": str(e.get("last_successful_deploy_at") or ""),
                "last_deploy_status": str(e.get("last_deploy_status") or ""),
                "project": str(e.get("project") or ""),
            }
        )
    return rows


def _rollback_rows(environments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for e in environments:
        if not isinstance(e, dict):
            continue
        rv = e.get("rollback_target_version")
        if rv:
            out.append(
                {
                    "environment_id": str(e.get("id") or ""),
                    "rollback_target_version": str(rv),
                    "approval_status": str(e.get("approval_status") or ""),
                }
            )
    return out


def build_cicd_control_tower_payload(
    *,
    workspace_root: Path,
    scan_state: dict[str, Any],
    force_flag: bool | None = None,
) -> dict[str, Any]:
    enabled = experimental_cicd_orchestration_enabled() if force_flag is None else bool(force_flag)
    children = scan_state.get("children")
    if not isinstance(children, list):
        children = []
    child_names = {str(c.get("name") or "").strip() for c in children if isinstance(c, dict)}
    child_names.discard("")

    if not enabled:
        base = empty_control_tower()
        return {
            "ok": True,
            **base,
            "feature_enabled": False,
            "provider_kind": "disabled",
            "resolved_at": scan_state.get("resolved_at"),
            "workspace_summary": {"child_count": len(children), "git_repo_count": sum(1 for c in children if isinstance(c, dict) and c.get("is_git"))},
            "hints": [
                "CI/CD control tower is off (LENSES_EXPERIMENTAL_CICD_ORCHESTRATION=0).",
                "When on, use `.lenses-local/cicd-orchestration.json` or LENSES_CICD_ORCHESTRATION_SEED_DEMO=1.",
            ],
        }

    doc = _load_doc(workspace_root)
    if doc is None:
        base = empty_control_tower()
        return {
            "ok": True,
            **base,
            "feature_enabled": True,
            "provider_kind": "scan_only",
            "resolved_at": scan_state.get("resolved_at"),
            "workspace_summary": {
                "child_count": len(children),
                "git_repo_count": sum(1 for c in children if isinstance(c, dict) and c.get("is_git")),
            },
            "hints": [
                "No `.lenses-local/cicd-orchestration.json` — add one or set LENSES_CICD_ORCHESTRATION_SEED_DEMO=1 "
                "for the checked-in demo (pipelines, environments, promotions, freezes).",
            ],
        }

    envs_in = [e for e in doc.get("environments") or [] if isinstance(e, dict)]
    environments = []
    for e in envs_in:
        proj = str(e.get("project") or "").strip()
        if child_names and proj and proj not in child_names:
            continue
        environments.append(e)

    pipeline_runs: list[dict[str, Any]] = []
    repos_doc = doc.get("repos") if isinstance(doc.get("repos"), dict) else {}
    for proj, blob in repos_doc.items():
        if not isinstance(blob, dict):
            continue
        if child_names and proj not in child_names:
            continue
        for entry in blob.get("pipelines") or []:
            if not isinstance(entry, dict):
                continue
            prov = str(entry.get("provider") or "")
            run = entry.get("run")
            if isinstance(run, dict) and prov:
                pipeline_runs.append(_normalize_pipeline(prov, run, proj))

    release_train = doc.get("release_train") if isinstance(doc.get("release_train"), dict) else None
    promotions = [p for p in doc.get("promotions") or [] if isinstance(p, dict)]
    freeze_windows = [f for f in doc.get("freeze_windows") or [] if isinstance(f, dict)]
    blocked = _merge_blocked_promotions(doc)
    gate_hints = extend_blocked_promotions_with_quality_gates(
        blocked,
        workspace_root=workspace_root,
        scan_state=scan_state,
        cicd_doc=doc,
    )
    what_live = _what_is_live(environments)
    rollbacks = _rollback_rows(environments)

    payload: dict[str, Any] = {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "feature_enabled": True,
        "provider_kind": "local_fixture",
        "resolved_at": scan_state.get("resolved_at"),
        "workspace_summary": {
            "child_count": len(children),
            "git_repo_count": sum(1 for c in children if isinstance(c, dict) and c.get("is_git")),
        },
        "pipeline_runs": pipeline_runs[:80],
        "environments": environments,
        "release_train": release_train,
        "promotions": promotions,
        "freeze_windows": freeze_windows,
        "blocked_promotions": blocked,
        "what_is_live": what_live,
        "rollback_targets": rollbacks,
        "artifacts": doc.get("artifacts") if isinstance(doc.get("artifacts"), list) else [],
        "hints": gate_hints,
    }
    merge_devsecops_into_control_tower_payload(
        payload,
        workspace_root=workspace_root,
        scan_state=scan_state,
    )
    return payload
