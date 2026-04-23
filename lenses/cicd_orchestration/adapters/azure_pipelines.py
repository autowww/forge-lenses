"""Azure Pipelines → canonical ``pipeline_run``."""

from __future__ import annotations

from typing import Any


def normalize_azure_pipeline_run(raw: dict[str, Any], *, project: str = "") -> dict[str, Any]:
    stages: list[dict[str, Any]] = []
    for phase in raw.get("stages") or []:
        if not isinstance(phase, dict):
            continue
        stages.append(
            {
                "name": str(phase.get("name") or ""),
                "status": str(phase.get("result") or phase.get("state") or ""),
                "started_at": str(phase.get("startTime") or ""),
                "finished_at": str(phase.get("finishTime") or ""),
            }
        )
    res = str(raw.get("result") or raw.get("status") or "").lower()
    status = "success" if res == "succeeded" else "failed" if res in ("failed", "canceled") else res or "unknown"
    return {
        "pipeline_run_id": str(raw.get("id") or raw.get("buildNumber") or ""),
        "provider": "azure_pipelines",
        "project": project,
        "name": str(raw.get("definition", {}).get("name") or raw.get("buildNumber") or "build"),
        "status": status,
        "conclusion": status,
        "started_at": str(raw.get("queueTime") or raw.get("startTime") or ""),
        "finished_at": str(raw.get("finishTime") or ""),
        "url": str(raw.get("url") or raw.get("_links", {}).get("web", {}).get("href") or ""),
        "head_sha": str(raw.get("sourceVersion") or ""),
        "ref": str(raw.get("sourceBranch") or "").replace("refs/heads/", ""),
        "stages": stages,
    }
