"""PagerDuty-style incident → canonical ``incident`` row."""

from __future__ import annotations

from typing import Any


def normalize_pagerduty_incident(raw: dict[str, Any], *, service_hint: str = "") -> dict[str, Any]:
    """Map webhook or API v2 incident shape to stable keys."""
    udf = raw.get("custom_fields") if isinstance(raw.get("custom_fields"), dict) else {}
    stories = raw.get("linked_story_ids") or udf.get("story_ids") or []
    if not isinstance(stories, list):
        stories = []
    return {
        "incident_id": str(raw.get("incident_id") or raw.get("id") or ""),
        "title": str(raw.get("title") or raw.get("summary") or ""),
        "severity": str(raw.get("severity") or raw.get("urgency") or "unknown").lower(),
        "status": str(raw.get("status") or "open").lower(),
        "started_at": str(raw.get("created_at") or raw.get("started_at") or ""),
        "resolved_at": str(raw.get("resolved_at") or raw.get("last_status_change_at") or ""),
        "service_id": str(raw.get("service_id") or udf.get("service_id") or service_hint or ""),
        "linked_release_version": str(raw.get("linked_release_version") or udf.get("release_version") or ""),
        "linked_environment_id": str(raw.get("linked_environment_id") or udf.get("environment_id") or ""),
        "linked_story_ids": [str(x) for x in stories],
        "linked_promotion_id": str(raw.get("linked_promotion_id") or udf.get("promotion_id") or ""),
        "source": "pagerduty",
        "html_url": str(raw.get("html_url") or raw.get("self") or ""),
    }
