"""Rollback recommendations from incidents + environment health."""

from __future__ import annotations

from typing import Any


def _prod_rollback_version(cicd: dict[str, Any]) -> str:
    for env in cicd.get("environments") or []:
        if not isinstance(env, dict):
            continue
        tid = str(env.get("tier") or "").lower()
        eid = str(env.get("id") or "").lower()
        if tid not in ("prod", "production") and eid not in ("production", "prod"):
            continue
        return str(env.get("rollback_target_version") or "")
    for r in cicd.get("rollback_targets") or []:
        if not isinstance(r, dict):
            continue
        if str(r.get("environment_id") or "").lower() in ("production", "prod"):
            return str(r.get("rollback_target_version") or "")
    return ""


def build_rollback_signals(cicd: dict[str, Any], ops_doc: dict[str, Any]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    default_rb = _prod_rollback_version(cicd)

    for inc in ops_doc.get("incidents") or []:
        if not isinstance(inc, dict):
            continue
        status = str(inc.get("status") or "").lower()
        if status in ("resolved", "closed"):
            continue
        sev = str(inc.get("severity") or "").lower()
        env = str(inc.get("linked_environment_id") or "").lower()
        if env not in ("production", "prod", "") and "production" not in str(inc.get("title") or "").lower():
            continue
        if sev not in ("sev1", "critical", "1", "p1", "high"):
            continue
        rid = str(inc.get("incident_id") or inc.get("id") or "")
        ver = str(inc.get("linked_release_version") or "")
        msg = (
            f"Open {sev} incident on production — consider rollback"
            + (f" away from {ver}" if ver else "")
            + "."
        )
        signals.append(
            {
                "signal_id": f"rollback-hint:{rid or 'unknown'}",
                "severity": "high",
                "incident_id": rid,
                "service_id": str(inc.get("service_id") or ""),
                "message": msg,
                "recommend_rollback_to": default_rb,
                "linked_release_version": ver,
            }
        )

    for h in ops_doc.get("health_degradations") or []:
        if not isinstance(h, dict):
            continue
        if not h.get("suggest_rollback"):
            continue
        signals.append(
            {
                "signal_id": f"health:{h.get('id') or 'unknown'}",
                "severity": str(h.get("severity") or "medium"),
                "message": str(h.get("summary") or "Health degradation"),
                "recommend_rollback_to": str(h.get("rollback_target_version") or default_rb),
                "service_id": str(h.get("service_id") or ""),
            }
        )

    return signals
