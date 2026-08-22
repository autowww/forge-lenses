"""Azure Repos → normalized workflow v1 (pull requests as ``pull_requests``)."""

from __future__ import annotations

from typing import Any

from lenses.repo_workflow.normalized import SCHEMA_VERSION, empty_workflow_v1


def normalize_azure_repos_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    out = empty_workflow_v1()
    repo = raw.get("repository") if isinstance(raw.get("repository"), dict) else {}
    proj = raw.get("project") if isinstance(raw.get("project"), dict) else {}
    name = str(repo.get("name") or "")
    proj_name = str(proj.get("name") or "")
    full = f"{proj_name}/{name}" if proj_name and name else str(repo.get("full_name") or "")
    out["repository"] = {
        "full_name": full,
        "default_branch": str(repo.get("defaultBranch") or repo.get("default_branch") or "").replace("refs/heads/", ""),
        "web_url": str(repo.get("webUrl") or repo.get("web_url") or ""),
        "vcs_host_kind": "azure_repos",
    }
    for b in raw.get("branches") or []:
        if not isinstance(b, dict):
            continue
        out["branches"].append(
            {
                "name": str(b.get("name") or "").replace("refs/heads/", ""),
                "head_sha": str(b.get("commitId") or b.get("sha") or ""),
                "protected": bool(b.get("isLocked") or b.get("protected")),
                "url": str(b.get("url") or ""),
            }
        )
    prs = raw.get("pull_requests") or raw.get("pullRequests") or []
    for pr in prs:
        if not isinstance(pr, dict):
            continue
        try:
            num = int(pr.get("pullRequestId") or pr.get("codeReviewId") or 0)
        except (TypeError, ValueError):
            num = 0
        st = str(pr.get("status") or "").lower()
        if "complete" in st or pr.get("closedDate"):
            state = "merged" if pr.get("mergeStatus") == "succeeded" else "closed"
        elif "abandon" in st:
            state = "closed"
        else:
            state = "open"
        src = pr.get("sourceRefName") or ""
        tgt = pr.get("targetRefName") or ""
        out["pull_requests"].append(
            {
                "id": str(pr.get("pullRequestId") or ""),
                "number": num,
                "title": str(pr.get("title") or ""),
                "state": state,
                "is_draft": bool(pr.get("isDraft")),
                "head_ref": str(src).replace("refs/heads/", ""),
                "base_ref": str(tgt).replace("refs/heads/", ""),
                "head_sha": str(pr.get("lastMergeSourceCommit", {}).get("commitId") or ""),
                "mergeable": str(pr.get("mergeStatus") or "unknown").lower(),
                "merge_blocked_reason": str(pr.get("mergeFailureMessage") or "") or None,
                "review_decision": pr.get("reviewDecision"),
                "review_debt_count": int(pr.get("pendingReviewerCount") or 0),
                "stale_days": float(pr["stale_days"]) if pr.get("stale_days") is not None else None,
                "url": str(pr.get("url") or pr.get("remoteUrl") or ""),
                "created_at": str(pr.get("creationDate") or ""),
                "updated_at": str(pr.get("closedDate") or pr.get("creationDate") or ""),
            }
        )
    for c in raw.get("commits_recent") or []:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("commitId") or c.get("sha") or "")
        out["commits_recent"].append(
            {
                "sha": cid,
                "short_sha": cid[:7] if cid else "",
                "message_first_line": str(c.get("comment") or c.get("message", ""))[:200],
                "url": str(c.get("remoteUrl") or c.get("url") or ""),
                "author": str((c.get("author", {}) or {}).get("name") or ""),
                "committed_at": str(c.get("author", {}).get("date") or ""),
            }
        )
    for bp in raw.get("branch_protection") or []:
        if not isinstance(bp, dict):
            continue
        out["branch_protection"].append(
            {
                "pattern": str(bp.get("pattern") or bp.get("name") or ""),
                "required_reviews": int(bp.get("minimumApproverCount") or 0),
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


class AzureReposWorkflowAdapter:
    provider = "azure_repos"

    def normalize_repo_snapshot(self, raw: dict[str, Any]) -> dict[str, Any]:
        return normalize_azure_repos_snapshot(raw)
