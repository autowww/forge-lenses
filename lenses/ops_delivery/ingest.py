"""Expand ``ingestions[]`` into canonical incident rows."""

from __future__ import annotations

from typing import Any

from lenses.ops_delivery.adapters.incident_generic import normalize_generic_incident
from lenses.ops_delivery.adapters.incident_pagerduty import normalize_pagerduty_incident


def expand_ingestions(doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(doc)
    base = [i for i in out.get("incidents") or [] if isinstance(i, dict)]
    seen = {str(i.get("incident_id") or i.get("id") or "") for i in base}
    extra: list[dict[str, Any]] = []

    for row in out.get("ingestions") or []:
        if not isinstance(row, dict):
            continue
        prov = str(row.get("provider") or "").strip().lower()
        project = str(row.get("project") or "")
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        norm: dict[str, Any] | None = None
        if prov in ("pagerduty", "pager_duty"):
            norm = normalize_pagerduty_incident(payload, service_hint=str(row.get("service_id") or ""))
        elif prov in ("incident", "generic_incident", "opsgenie", "statuspage"):
            norm = normalize_generic_incident(payload, project=project)
        if not norm:
            continue
        iid = str(norm.get("incident_id") or "")
        if not iid or iid in seen:
            continue
        seen.add(iid)
        if project:
            norm["project"] = project
        extra.append(norm)

    if extra:
        out["incidents"] = base + extra
    return out
