"""GitHub Actions → canonical ``pipeline_run``."""

from __future__ import annotations

from typing import Any


def normalize_github_actions_run(raw: dict[str, Any], *, project: str = "") -> dict[str, Any]:
    stages: list[dict[str, Any]] = []
    for job in raw.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        stages.append(
            {
                "name": str(job.get("name") or ""),
                "status": str(job.get("conclusion") or job.get("status") or "unknown"),
                "started_at": str(job.get("started_at") or ""),
                "finished_at": str(job.get("completed_at") or ""),
            }
        )
    return {
        "pipeline_run_id": str(raw.get("id") or raw.get("databaseId") or ""),
        "provider": "github_actions",
        "project": project,
        "name": str(raw.get("name") or raw.get("display_title") or "workflow"),
        "status": str(raw.get("status") or raw.get("conclusion") or "unknown"),
        "conclusion": str(raw.get("conclusion") or ""),
        "started_at": str(raw.get("run_started_at") or raw.get("created_at") or ""),
        "finished_at": str(raw.get("updated_at") or ""),
        "url": str(raw.get("html_url") or raw.get("url") or ""),
        "head_sha": str(raw.get("head_sha") or ""),
        "ref": str(raw.get("head_branch") or raw.get("ref") or ""),
        "stages": stages,
    }
