"""Generic / vendor-neutral incident dict → canonical row."""

from __future__ import annotations

from typing import Any


def normalize_generic_incident(raw: dict[str, Any], *, project: str = "") -> dict[str, Any]:
    stories = raw.get("linked_story_ids") or raw.get("story_ids") or []
    if not isinstance(stories, list):
        stories = []
    return {
        "incident_id": str(raw.get("incident_id") or raw.get("id") or ""),
        "title": str(raw.get("title") or ""),
        "severity": str(raw.get("severity") or "unknown").lower(),
        "status": str(raw.get("status") or "open").lower(),
        "started_at": str(raw.get("started_at") or raw.get("detected_at") or ""),
        "resolved_at": str(raw.get("resolved_at") or ""),
        "service_id": str(raw.get("service_id") or ""),
        "linked_release_version": str(raw.get("linked_release_version") or raw.get("release_version") or ""),
        "linked_environment_id": str(raw.get("linked_environment_id") or raw.get("environment_id") or ""),
        "linked_story_ids": [str(x) for x in stories],
        "linked_promotion_id": str(raw.get("linked_promotion_id") or ""),
        "source": str(raw.get("source") or "generic"),
        "html_url": str(raw.get("html_url") or raw.get("url") or ""),
        "project": project,
    }
