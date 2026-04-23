"""GitLab → normalized workflow v1 (merge requests as ``pull_requests``)."""

from __future__ import annotations

from typing import Any

from lenses.repo_workflow.normalized import SCHEMA_VERSION, empty_workflow_v1


def normalize_gitlab_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    out = empty_workflow_v1()
    proj = raw.get("project") if isinstance(raw.get("project"), dict) else raw.get("repository") or {}
    path = str(proj.get("path_with_namespace") or proj.get("full_name") or "")
    out["repository"] = {
        "full_name": path,
        "default_branch": str(proj.get("default_branch") or ""),
        "web_url": str(proj.get("web_url") or ""),
        "vcs_host_kind": "gitlab",
    }
    for b in raw.get("branches") or []:
        if not isinstance(b, dict):
            continue
        out["branches"].append(
            {
                "name": str(b.get("name") or ""),
                "head_sha": str(b.get("commit", {}).get("id") or b.get("sha") or ""),
                "protected": bool(b.get("protected")),
                "url": str(b.get("web_url") or ""),
            }
        )
    mrs = raw.get("merge_requests") or raw.get("pull_requests") or []
    for mr in mrs:
        if not isinstance(mr, dict):
            continue
        iid = mr.get("iid") or mr.get("number")
        try:
            num = int(iid) if iid is not None else 0
        except (TypeError, ValueError):
            num = 0
        state = str(mr.get("state") or "").lower()
        if state == "merged":
            st = "merged"
        elif state == "closed":
            st = "closed"
        else:
            st = "open"
        out["pull_requests"].append(
            {
                "id": str(mr.get("id") or ""),
                "number": num,
                "title": str(mr.get("title") or ""),
                "state": st,
                "is_draft": bool(mr.get("draft") or mr.get("work_in_progress")),
                "head_ref": str(mr.get("source_branch") or ""),
                "base_ref": str(mr.get("target_branch") or ""),
                "head_sha": str(mr.get("sha") or ""),
                "mergeable": str(mr.get("merge_status") or "unknown").lower(),
                "merge_blocked_reason": str(mr.get("merge_error") or "") or None,
                "review_decision": mr.get("approval_status"),
                "review_debt_count": int(mr.get("reviewers_missing_count") or 0),
                "stale_days": float(mr["stale_days"]) if mr.get("stale_days") is not None else None,
                "url": str(mr.get("web_url") or ""),
                "created_at": str(mr.get("created_at") or ""),
                "updated_at": str(mr.get("updated_at") or ""),
            }
        )
    for c in raw.get("commits_recent") or []:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or c.get("sha") or "")
        short = str(c.get("short_id") or "")[:7] or cid[:7]
        out["commits_recent"].append(
            {
                "sha": cid,
                "short_sha": short,
                "message_first_line": str(c.get("title") or c.get("message", "")[:200]),
                "url": str(c.get("web_url") or ""),
                "author": str((c.get("author_name") or c.get("author", {}) or "")),
                "committed_at": str(c.get("created_at") or c.get("committed_date") or ""),
            }
        )
    for bp in raw.get("protected_branches") or raw.get("branch_protection") or []:
        if not isinstance(bp, dict):
            continue
        out["branch_protection"].append(
            {
                "pattern": str(bp.get("name") or bp.get("pattern") or ""),
                "required_reviews": int(bp.get("required_approvals") or 0),
                "url": str(bp.get("web_url") or ""),
            }
        )
    co = raw.get("code_owners") if isinstance(raw.get("code_owners"), dict) else {}
    out["code_owners"] = {
        "present": bool(co.get("present")),
        "path": str(co.get("path") or "") or None,
        "url": str(co.get("url") or "") or None,
    }
    rs = raw.get("reviews_summary") if isinstance(raw.get("reviews_summary"), dict) else {}
    out["reviews_summary"] = {
        "approved_open_count": int(rs.get("approved_open_count") or 0),
        "changes_requested_open_count": int(rs.get("changes_requested_open_count") or 0),
    }
    out["schema_version"] = SCHEMA_VERSION
    return out


class GitLabRepoWorkflowAdapter:
    provider = "gitlab"

    def normalize_repo_snapshot(self, raw: dict[str, Any]) -> dict[str, Any]:
        return normalize_gitlab_snapshot(raw)
