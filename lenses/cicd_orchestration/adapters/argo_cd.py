"""Argo CD / Argo Rollouts style deployment sync → canonical ``deployment_sync`` row.

Maps to the same ``pipeline_run`` envelope so the control tower can list “delivery activity” uniformly.
"""

from __future__ import annotations

from typing import Any


def normalize_argo_application_sync(raw: dict[str, Any], *, project: str = "") -> dict[str, Any]:
    op = raw.get("operation") if isinstance(raw.get("operation"), dict) else {}
    sync = op.get("sync") if isinstance(op.get("sync"), dict) else {}
    rev = str(raw.get("status", {}).get("sync", {}).get("revision") or raw.get("target_revision") or "")
    health = str(raw.get("status", {}).get("health", {}).get("status") or "")
    sync_status = str(raw.get("status", {}).get("sync", {}).get("status") or "")
    stages = [
        {
            "name": "sync",
            "status": sync_status or health or "unknown",
            "started_at": str(raw.get("status", {}).get("reconciledAt") or ""),
            "finished_at": "",
        }
    ]
    return {
        "pipeline_run_id": str(raw.get("metadata", {}).get("uid") or raw.get("name") or ""),
        "provider": "argo_cd",
        "project": project,
        "name": str(raw.get("metadata", {}).get("name") or "application"),
        "status": "success" if sync_status == "Synced" and health == "Healthy" else sync_status.lower() or health.lower(),
        "conclusion": health,
        "started_at": str(raw.get("status", {}).get("reconciledAt") or ""),
        "finished_at": "",
        "url": str(raw.get("metadata", {}).get("annotations", {}).get("argocd.argoproj.io/sync-url") or ""),
        "head_sha": rev,
        "ref": str(raw.get("spec", {}).get("source", {}).get("targetRevision") or ""),
        "stages": stages,
        "kind": "deployment_sync",
        "target_cluster": str(raw.get("spec", {}).get("destination", {}).get("name") or ""),
    }
