"""GitLab CI → canonical ``pipeline_run``."""

from __future__ import annotations

from typing import Any


def normalize_gitlab_ci_pipeline(raw: dict[str, Any], *, project: str = "") -> dict[str, Any]:
    stages: list[dict[str, Any]] = []
    for job in raw.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        stages.append(
            {
                "name": str(job.get("name") or ""),
                "status": str(job.get("status") or ""),
                "started_at": str(job.get("started_at") or ""),
                "finished_at": str(job.get("finished_at") or ""),
            }
        )
    st = str(raw.get("status") or "").lower()
    status = "success" if st == "success" else "failed" if st == "failed" else "running" if st == "running" else st
    return {
        "pipeline_run_id": str(raw.get("id") or ""),
        "provider": "gitlab_ci",
        "project": project,
        "name": str(raw.get("name") or "pipeline"),
        "status": status,
        "conclusion": status,
        "started_at": str(raw.get("started_at") or raw.get("created_at") or ""),
        "finished_at": str(raw.get("finished_at") or ""),
        "url": str(raw.get("web_url") or ""),
        "head_sha": str(raw.get("sha") or ""),
        "ref": str(raw.get("ref") or ""),
        "stages": stages,
    }
