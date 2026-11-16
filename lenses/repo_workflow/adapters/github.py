"""GitHub → normalized workflow v1.

Input shape matches REST-style keys used in ``repo-workflow.demo.json`` (``repository``, ``pull_requests``, …).
"""

from __future__ import annotations

from typing import Any

from lenses.repo_workflow.normalized import SCHEMA_VERSION, empty_workflow_v1


def normalize_github_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    out = empty_workflow_v1()
    repo = raw.get("repository") if isinstance(raw.get("repository"), dict) else {}
    out["repository"] = {
        "full_name": str(repo.get("full_name") or repo.get("name_with_owner") or ""),
        "default_branch": str(repo.get("default_branch") or ""),
        "web_url": str(repo.get("html_url") or repo.get("url") or ""),
        "vcs_host_kind": "github",
    }
    for b in raw.get("branches") or []:
        if not isinstance(b, dict):
            continue
        out["branches"].append(
            {
                "name": str(b.get("name") or ""),
                "head_sha": str(b.get("commit", {}).get("sha") or b.get("sha") or ""),
                "protected": bool(b.get("protected")),
                "url": str(b.get("url") or ""),
            }
        )
    for pr in raw.get("pull_requests") or []:
        if not isinstance(pr, dict):
            continue
        head = pr.get("head") if isinstance(pr.get("head"), dict) else {}
        base = pr.get("base") if isinstance(pr.get("base"), dict) else {}
        out["pull_requests"].append(
            {
                "id": str(pr.get("id") or pr.get("node_id") or ""),
                "number": int(pr["number"]) if isinstance(pr.get("number"), int) else 0,
                "title": str(pr.get("title") or ""),
                "state": str(pr.get("state") or "").lower(),
                "is_draft": bool(pr.get("draft") or pr.get("is_draft")),
                "head_ref": str(head.get("ref") or ""),
                "base_ref": str(base.get("ref") or ""),
                "head_sha": str(head.get("sha") or ""),
                "mergeable": str(pr.get("mergeable") or "unknown").lower(),
                "merge_blocked_reason": str(pr.get("merge_blocked_reason") or "") or None,
                "review_decision": pr.get("review_decision"),
                "review_debt_count": int(pr.get("pending_review_count") or 0),
                "stale_days": float(pr["stale_days"]) if pr.get("stale_days") is not None else None,
                "url": str(pr.get("html_url") or ""),
                "created_at": str(pr.get("created_at") or ""),
                "updated_at": str(pr.get("updated_at") or ""),
            }
        )
    for c in raw.get("commits_recent") or []:
        if not isinstance(c, dict):
            continue
        out["commits_recent"].append(
            {
                "sha": str(c.get("sha") or ""),
                "short_sha": str(c.get("short_sha") or (c.get("sha") or "")[:7]),
                "message_first_line": str(c.get("message_first_line") or c.get("commit", {}).get("message", "")[:200]),
                "url": str(c.get("html_url") or c.get("url") or ""),
                "author": str((c.get("author") or {}).get("login") or ""),
                "committed_at": str(c.get("committed_at") or ""),
            }
        )
    for bp in raw.get("branch_protection") or []:
        if not isinstance(bp, dict):
            continue
        out["branch_protection"].append(
            {
                "pattern": str(bp.get("pattern") or bp.get("branch") or ""),
                "required_reviews": int(bp.get("required_approving_review_count") or 0),
                "url": str(bp.get("url") or ""),
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


class GitHubRepoWorkflowAdapter:
    provider = "github"

    def normalize_repo_snapshot(self, raw: dict[str, Any]) -> dict[str, Any]:
        return normalize_github_snapshot(raw)
