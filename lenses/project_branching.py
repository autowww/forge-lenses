"""Project-level branching payload for Forge Studio."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.branch_steward_policy import categorize_branch_name, resolve_branch_steward_policy
from lenses.repo_workflow import build_project_repo_workflow_payload


def _child_git_scan(scan_state: dict[str, Any], project_name: str) -> dict[str, Any]:
    children = scan_state.get("children")
    if not isinstance(children, list):
        return {}
    for child in children:
        if not isinstance(child, dict):
            continue
        if str(child.get("name") or "") != project_name:
            continue
        g = child.get("git")
        return g if isinstance(g, dict) else {}
    return {}


def _lane_bucket_template() -> dict[str, list[dict[str, Any]]]:
    return {
        "main": [],
        "product": [],
        "iter": [],
        "spark": [],
        "spike": [],
        "release": [],
        "hotfix": [],
        "feature": [],
        "fix": [],
        "topic": [],
        "other": [],
    }


def _normalize_branches(workflow: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    out: list[dict[str, Any]] = []
    buckets = _lane_bucket_template()
    for row in workflow.get("branches") or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "")
        category = categorize_branch_name(name)
        item = {
            "name": name,
            "category": category,
            "protected": bool(row.get("protected")),
            "head_sha": str(row.get("head_sha") or ""),
            "url": str(row.get("url") or ""),
        }
        out.append(item)
        buckets.setdefault(category, []).append(item)
    return out, buckets


def _normalize_pull_requests(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in workflow.get("pull_requests") or []:
        if not isinstance(row, dict):
            continue
        head = str(row.get("head_ref") or "")
        out.append(
            {
                "number": int(row.get("number") or 0),
                "title": str(row.get("title") or ""),
                "state": str(row.get("state") or ""),
                "head_ref": head,
                "head_category": categorize_branch_name(head),
                "base_ref": str(row.get("base_ref") or ""),
                "mergeable": str(row.get("mergeable") or ""),
                "merge_blocked_reason": row.get("merge_blocked_reason"),
                "stale_days": row.get("stale_days"),
                "url": str(row.get("url") or ""),
            }
        )
    return out


def build_project_branching_payload(
    *,
    workspace_root: Path,
    project_root: Path,
    project_name: str,
    scan_state: dict[str, Any],
) -> dict[str, Any]:
    policy = resolve_branch_steward_policy(project_root, workspace_root=workspace_root)
    rw = build_project_repo_workflow_payload(
        workspace_root=workspace_root,
        scan_state=scan_state,
        project_name=project_name,
    )
    repo = rw.get("repo") if isinstance(rw.get("repo"), dict) else {}
    workflow = repo.get("workflow") if isinstance(repo.get("workflow"), dict) else {}
    branches, buckets = _normalize_branches(workflow)
    pull_requests = _normalize_pull_requests(workflow)
    git_scan = _child_git_scan(scan_state, project_name)

    return {
        "ok": True,
        "schema_version": 1,
        "project": project_name,
        "policy": {
            "source": policy.source,
            "trunk": policy.trunk,
            "model": policy.model,
            "team_scale": policy.team_scale,
            "topology": policy.topology,
            "cicd_maturity": policy.cicd_maturity,
            "feature_prefix": policy.feature_prefix,
            "fix_prefix": policy.fix_prefix,
            "product_prefix": policy.product_prefix,
            "iter_prefix": policy.iter_prefix,
            "spark_prefix": policy.spark_prefix,
            "spike_prefix": policy.spike_prefix,
            "release_prefix": policy.release_prefix,
            "hotfix_prefix": policy.hotfix_prefix,
            "require_pr": policy.require_pr,
            "required_approvals": policy.required_approvals,
            "require_green_checks": policy.require_green_checks,
            "docs_health_style": policy.docs_health_style,
            "lanes_enabled": policy.lanes_enabled,
        },
        "current": {
            "branch": str(git_scan.get("branch") or ""),
            "head_short": str(git_scan.get("head_short") or ""),
            "origin_url": str(git_scan.get("origin_url") or ""),
            "is_git": bool(git_scan),
        },
        "structure": {
            "branches": branches,
            "branches_by_lane": buckets,
            "pull_requests": pull_requests,
            "branch_protection": workflow.get("branch_protection") if isinstance(workflow.get("branch_protection"), list) else [],
            "work_item_links": repo.get("work_item_links") if isinstance(repo.get("work_item_links"), list) else [],
        },
        "recommendations": policy.recommendations(),
        "hints": rw.get("hints") if isinstance(rw.get("hints"), list) else [],
    }
