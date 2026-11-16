"""DORA-style metrics from CI/CD traceability + ops incidents (Sprint 8)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def _parse_iso(s: str) -> datetime | None:
    t = (s or "").strip()
    if not t:
        return None
    try:
        if t.endswith("Z"):
            t = t[:-1] + "+00:00"
        return datetime.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_prod_env(env: dict[str, Any]) -> bool:
    tid = str(env.get("tier") or "").lower()
    eid = str(env.get("id") or "").lower()
    return tid in ("prod", "production") or eid in ("production", "prod")


def compute_dora_metrics(
    cicd: dict[str, Any],
    ops_doc: dict[str, Any],
    *,
    quality: dict[str, Any] | None = None,
    window_days: int = 30,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=max(1, window_days))

    deploy_events: list[dict[str, Any]] = []
    for env in cicd.get("environments") or []:
        if not isinstance(env, dict):
            continue
        if not _is_prod_env(env):
            continue
        for d in env.get("deployment_history") or []:
            if not isinstance(d, dict):
                continue
            if str(d.get("status") or "").lower() != "success":
                continue
            at = _parse_iso(str(d.get("at") or ""))
            if at is None or at < start:
                continue
            deploy_events.append(
                {
                    "at": d.get("at"),
                    "version": str(d.get("version") or ""),
                    "environment_id": str(env.get("id") or ""),
                }
            )

    pipeline_runs = [r for r in cicd.get("pipeline_runs") or [] if isinstance(r, dict)]
    success_main = [
        r
        for r in pipeline_runs
        if str(r.get("conclusion") or r.get("status") or "").lower() in ("success", "completed")
        and ("main" in str(r.get("ref") or "").lower() or "main" in str(r.get("head_branch") or "").lower())
    ]

    lead_samples: list[float] = []
    for dep in deploy_events[:40]:
        dep_at = _parse_iso(str(dep.get("at") or ""))
        if dep_at is None:
            continue
        best: datetime | None = None
        for r in success_main:
            fin = _parse_iso(str(r.get("finished_at") or r.get("started_at") or ""))
            if fin is None or fin > dep_at:
                continue
            if dep_at - fin <= timedelta(days=14) and (best is None or fin > best):
                best = fin
        if best:
            lead_samples.append((dep_at - best).total_seconds() / 3600.0)

    lead_hours_median: float | None = None
    if lead_samples:
        srt = sorted(lead_samples)
        lead_hours_median = srt[len(srt) // 2]

    incidents = [i for i in ops_doc.get("incidents") or [] if isinstance(i, dict)]
    prod_incidents = [
        i
        for i in incidents
        if str(i.get("linked_environment_id") or "").lower() in ("production", "prod")
        or "production" in str(i.get("title") or "").lower()
    ]
    window_incs: list[dict[str, Any]] = []
    for i in prod_incidents:
        st = _parse_iso(str(i.get("started_at") or ""))
        if st is None or st < start:
            continue
        window_incs.append(i)

    deploy_n = len(deploy_events)
    fail_related = [
        i
        for i in window_incs
        if str(i.get("status") or "").lower() in ("resolved", "closed")
        and (
            str(i.get("linked_release_version") or "").strip() != ""
            or str(i.get("classification") or "") == "change_related"
        )
    ]
    cfr = len(fail_related) / max(1, deploy_n)

    mttr_hours: float | None = None
    resolved_durations: list[float] = []
    for i in incidents:
        a = _parse_iso(str(i.get("started_at") or ""))
        b = _parse_iso(str(i.get("resolved_at") or ""))
        if a is None or b is None or b < a:
            continue
        if a < start:
            continue
        resolved_durations.append((b - a).total_seconds() / 3600.0)
    if resolved_durations:
        mttr_hours = sum(resolved_durations) / len(resolved_durations)

    rework = {
        "failed_pipeline_runs": sum(
            1
            for r in pipeline_runs
            if str(r.get("conclusion") or "").lower() in ("failure", "failed", "cancelled")
        ),
        "blocked_promotions": len(cicd.get("blocked_promotions") or []),
        "open_defects": 0,
    }
    if isinstance(quality, dict):
        rq = quality.get("release_quality") if isinstance(quality.get("release_quality"), dict) else {}
        defects = [d for d in quality.get("defects") or [] if isinstance(d, dict)]
        rework["open_defects"] = sum(
            1 for d in defects if str(d.get("status") or "").lower() in ("open", "new", "in_progress")
        )

    return {
        "window_days": window_days,
        "window_ends_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "deployment_frequency": {
            "production_successful_deploys": deploy_n,
            "per_day_approx": round(deploy_n / max(1, window_days), 3),
            "computed_from": "CI/CD environment deployment_history (production tier)",
        },
        "lead_time_for_changes": {
            "median_hours": lead_hours_median,
            "sample_count": len(lead_samples),
            "computed_from": "Time from last successful main-branch pipeline finish to production deploy (matched heuristically)",
        },
        "change_failure_rate": {
            "ratio": round(cfr, 4),
            "failed_changes_count": len(fail_related),
            "deployments_denominator": deploy_n,
            "computed_from": "Production incidents with release linkage or change_related / successful prod deploys in window",
        },
        "recovery": {
            "mean_time_to_restore_hours": round(mttr_hours, 2) if mttr_hours is not None else None,
            "resolved_incidents_in_window": len(resolved_durations),
            "computed_from": "Mean (resolved_at - started_at) for incidents with timestamps in window",
        },
        "rework_signals": rework,
    }
