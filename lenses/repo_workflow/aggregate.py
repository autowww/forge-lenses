"""Build repo-workflow API payloads from workspace scan + local / demo fixtures."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from lenses.repo_workflow.adapters.azure_repos import normalize_azure_repos_snapshot
from lenses.repo_workflow.adapters.github import normalize_github_snapshot
from lenses.repo_workflow.adapters.gitlab import normalize_gitlab_snapshot
from lenses.repo_workflow.feature_flag import experimental_repo_workflow_enabled
from lenses.repo_workflow.local_store import load_demo_fixture, read_local_repo_workflow
from lenses.repo_workflow.normalized import compute_health


def _lenses_package_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _truthy_env(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _normalize_provider_snapshot(provider: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    p = provider.strip().lower()
    if p == "github":
        return normalize_github_snapshot(snapshot)
    if p == "gitlab":
        return normalize_gitlab_snapshot(snapshot)
    if p in ("azure_repos", "azure", "ado"):
        return normalize_azure_repos_snapshot(snapshot)
    return normalize_github_snapshot(snapshot)


def _fixture_map_workspace(workspace_root: Path) -> dict[str, Any]:
    local_doc = read_local_repo_workflow(workspace_root)
    if isinstance(local_doc, dict) and isinstance(local_doc.get("repos"), dict):
        return dict(local_doc["repos"])
    if _truthy_env("LENSES_REPO_WORKFLOW_SEED_DEMO"):
        demo = load_demo_fixture(_lenses_package_root())
        if isinstance(demo, dict) and isinstance(demo.get("repos"), dict):
            return dict(demo["repos"])
    return {}


def get_repo_workflow_row_for_project(workspace_root: Path, project_name: str) -> dict[str, Any] | None:
    """Fixture-backed row for one workspace child (used from story-hub without a full scan)."""
    if not experimental_repo_workflow_enabled():
        return None
    blob = _fixture_map_workspace(workspace_root).get(project_name.strip())
    if blob is None:
        return None
    return _merge_repo_blob(project_name.strip(), blob)


def _merge_repo_blob(project: str, blob: Any) -> dict[str, Any] | None:
    if not isinstance(blob, dict):
        return None
    provider = str(blob.get("provider") or blob.get("vcs_host_kind") or "github")
    snapshot = blob.get("snapshot")
    if not isinstance(snapshot, dict):
        snapshot = blob
    workflow = _normalize_provider_snapshot(provider, snapshot)
    health = compute_health(workflow)
    extra = blob.get("health_hints") if isinstance(blob.get("health_hints"), dict) else {}
    if "unlinked_work_items_count" in extra:
        try:
            health["unlinked_work_items_count"] = int(extra["unlinked_work_items_count"])
        except (TypeError, ValueError):
            health["unlinked_work_items_count"] = 0
    wili = blob.get("work_item_links") if isinstance(blob.get("work_item_links"), list) else []
    return {
        "project": project,
        "provider": provider,
        "workflow": workflow,
        "health": health,
        "work_item_links": wili,
        "data_sources": ["local_fixture"],
    }


def build_repo_workflow_overview_payload(
    *,
    workspace_root: Path,
    scan_state: dict[str, Any],
    force_flag: bool | None = None,
) -> dict[str, Any]:
    enabled = experimental_repo_workflow_enabled() if force_flag is None else bool(force_flag)
    children = scan_state.get("children")
    if not isinstance(children, list):
        children = []
    git_count = sum(1 for c in children if isinstance(c, dict) and c.get("is_git"))

    if not enabled:
        return {
            "ok": True,
            "schema_version": 1,
            "feature_enabled": False,
            "resolved_at": scan_state.get("resolved_at"),
            "workspace_summary": {"child_count": len(children), "git_repo_count": git_count},
            "repos": [],
            "hints": [
                "Repo workflow overlays are off (LENSES_EXPERIMENTAL_REPO_WORKFLOW=0).",
                "When on, add `.lenses-local/repo-workflow.json` or LENSES_REPO_WORKFLOW_SEED_DEMO=1.",
            ],
        }

    fixture_map = _fixture_map_workspace(workspace_root)

    provider_kind = "local_fixture" if fixture_map else "scan_only"
    hints: list[str] = []
    if not fixture_map:
        hints.append(
            "No `.lenses-local/repo-workflow.json` — branch/PR/MR widgets use workspace names only. "
            "Copy `lenses/fixtures/repo-workflow.demo.json` or set LENSES_REPO_WORKFLOW_SEED_DEMO=1."
        )

    repos_out: list[dict[str, Any]] = []
    for c in children:
        if not isinstance(c, dict):
            continue
        name = str(c.get("name") or "").strip()
        if not name:
            continue
        git = c.get("git") if isinstance(c.get("git"), dict) else {}
        row: dict[str, Any] = {
            "project": name,
            "is_git": bool(c.get("is_git")),
            "git_head_short": git.get("head_short") if isinstance(git.get("head_short"), str) else "",
            "git_branch": git.get("branch") if isinstance(git.get("branch"), str) else "",
            "origin_url": git.get("origin_url") if isinstance(git.get("origin_url"), str) else "",
            "provider": "",
            "workflow": {},
            "health": {
                "open_prs_count": 0,
                "stale_open_prs_count": 0,
                "blocked_merge_count": 0,
                "review_debt_total": 0,
            },
            "work_item_links": [],
            "data_sources": ["workspace_scan"],
        }
        fix = fixture_map.get(name)
        merged = _merge_repo_blob(name, fix) if fix is not None else None
        if merged:
            row["provider"] = merged["provider"]
            row["workflow"] = merged["workflow"]
            row["health"] = merged["health"]
            row["work_item_links"] = merged["work_item_links"]
            row["data_sources"] = ["workspace_scan", "local_fixture"]
        repos_out.append(row)

    return {
        "ok": True,
        "schema_version": 1,
        "feature_enabled": True,
        "provider_kind": provider_kind,
        "resolved_at": scan_state.get("resolved_at"),
        "workspace_summary": {"child_count": len(children), "git_repo_count": git_count},
        "repos": repos_out,
        "hints": hints,
    }


def build_project_repo_workflow_payload(
    *,
    workspace_root: Path,
    scan_state: dict[str, Any],
    project_name: str,
    force_flag: bool | None = None,
) -> dict[str, Any]:
    overview = build_repo_workflow_overview_payload(
        workspace_root=workspace_root,
        scan_state=scan_state,
        force_flag=force_flag,
    )
    if not overview.get("feature_enabled"):
        return {**overview, "project": project_name, "repo": None}

    for r in overview.get("repos") or []:
        if isinstance(r, dict) and str(r.get("project") or "") == project_name:
            return {
                "ok": True,
                "schema_version": 1,
                "feature_enabled": True,
                "resolved_at": overview.get("resolved_at"),
                "project": project_name,
                "repo": r,
                "hints": overview.get("hints") or [],
            }
    return {
        "ok": True,
        "schema_version": 1,
        "feature_enabled": True,
        "resolved_at": overview.get("resolved_at"),
        "project": project_name,
        "repo": None,
        "hints": (overview.get("hints") or []) + ["Project not found in workspace scan."],
    }
