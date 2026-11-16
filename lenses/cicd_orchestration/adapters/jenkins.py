"""Jenkins → canonical ``pipeline_run``."""

from __future__ import annotations

from typing import Any


def normalize_jenkins_build(raw: dict[str, Any], *, project: str = "") -> dict[str, Any]:
    stages: list[dict[str, Any]] = []
    for st in raw.get("stages") or []:
        if not isinstance(st, dict):
            continue
        stages.append(
            {
                "name": str(st.get("name") or ""),
                "status": str(st.get("status") or ""),
                "started_at": str(st.get("startTimeMillis") or ""),
                "finished_at": str(st.get("durationMillis") or ""),
            }
        )
    res = str(raw.get("result") or "UNKNOWN").upper()
    status = "success" if res == "SUCCESS" else "failed" if res == "FAILURE" else res.lower()
    head_sha = ""
    cs = raw.get("changeSet")
    if isinstance(cs, dict):
        items = cs.get("items")
        if isinstance(items, list) and items and isinstance(items[0], dict):
            head_sha = str(items[0].get("commitId") or "")
    br = raw.get("branch")
    ref = str(br.get("name") if isinstance(br, dict) else br or "")

    return {
        "pipeline_run_id": str(raw.get("number") or raw.get("id") or ""),
        "provider": "jenkins",
        "project": project,
        "name": str(raw.get("fullDisplayName") or raw.get("displayName") or "build"),
        "status": status,
        "conclusion": status,
        "started_at": str(raw.get("timestamp") or ""),
        "finished_at": "",
        "url": str(raw.get("url") or ""),
        "head_sha": head_sha,
        "ref": ref,
        "stages": stages,
    }
