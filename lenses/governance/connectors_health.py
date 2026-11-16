"""Aggregate connector / integration health for admin dashboards."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.cicd_orchestration import build_cicd_control_tower_payload
from lenses.cross_team_release import build_cross_team_release_overview
from lenses.delivery_signals import build_delivery_overview_payload
from lenses.devsecops_compliance.aggregate import build_devsecops_overview_payload
from lenses.ops_delivery import build_ops_delivery_overview
from lenses.repo_workflow import build_repo_workflow_overview_payload
from lenses.test_quality.aggregate import build_quality_overview_payload


def _row(
    connector_id: str,
    label: str,
    *,
    enabled: bool,
    ok: bool,
    provider_kind: str | None,
    hints: list[str] | None,
) -> dict[str, Any]:
    return {
        "id": connector_id,
        "label": label,
        "enabled": enabled,
        "healthy": ok,
        "provider_kind": provider_kind or "unknown",
        "hints": hints or [],
    }


def build_connectors_health(
    *,
    workspace_root: Path,
    scan_state: dict[str, Any],
) -> dict[str, Any]:
    """Read-only snapshot for ``GET /api/connectors/health``."""
    rows: list[dict[str, Any]] = []

    try:
        d = build_delivery_overview_payload(
            workspace_root=workspace_root, scan_state=scan_state
        )
        en = bool(d.get("feature_enabled"))
        pk = str(d.get("provider_kind") or "")
        hints = [str(x) for x in (d.get("hints") or []) if isinstance(x, str)][:5]
        rows.append(
            _row(
                "delivery_signals",
                "Delivery signals",
                enabled=en,
                ok=en and pk not in ("disabled",),
                provider_kind=pk,
                hints=hints,
            )
        )
    except (OSError, TypeError, ValueError) as ex:
        rows.append(
            _row(
                "delivery_signals",
                "Delivery signals",
                enabled=False,
                ok=False,
                provider_kind="error",
                hints=[str(ex)],
            )
        )

    try:
        rw = build_repo_workflow_overview_payload(
            workspace_root=workspace_root, scan_state=scan_state
        )
        en = bool(rw.get("feature_enabled"))
        pk = str(rw.get("provider_kind") or "")
        hints = [str(x) for x in (rw.get("hints") or []) if isinstance(x, str)][:5]
        rows.append(
            _row(
                "repo_workflow",
                "Repo / PR workflow",
                enabled=en,
                ok=en and pk != "disabled",
                provider_kind=pk,
                hints=hints,
            )
        )
    except (OSError, TypeError, ValueError) as ex:
        rows.append(
            _row(
                "repo_workflow",
                "Repo / PR workflow",
                enabled=False,
                ok=False,
                provider_kind="error",
                hints=[str(ex)],
            )
        )

    try:
        cicd = build_cicd_control_tower_payload(
            workspace_root=workspace_root, scan_state=scan_state
        )
        en = bool(cicd.get("feature_enabled"))
        pk = str(cicd.get("provider_kind") or "")
        blocked = cicd.get("blocked_promotions") or []
        n_blocked = len(blocked) if isinstance(blocked, list) else 0
        hints = [str(x) for x in (cicd.get("hints") or []) if isinstance(x, str)][:3]
        if n_blocked:
            hints = [f"{n_blocked} blocked promotion(s)"] + hints
        rows.append(
            _row(
                "cicd",
                "CI/CD control tower",
                enabled=en,
                ok=en and pk != "disabled",
                provider_kind=pk,
                hints=hints[:5],
            )
        )
    except (OSError, TypeError, ValueError) as ex:
        rows.append(
            _row(
                "cicd",
                "CI/CD control tower",
                enabled=False,
                ok=False,
                provider_kind="error",
                hints=[str(ex)],
            )
        )

    try:
        q = build_quality_overview_payload(
            workspace_root=workspace_root, scan_state=scan_state
        )
        en = bool(q.get("feature_enabled"))
        pk = str(q.get("provider_kind") or "")
        hints = [str(x) for x in (q.get("hints") or []) if isinstance(x, str)][:5]
        rows.append(
            _row(
                "test_quality",
                "Test & quality",
                enabled=en,
                ok=en and pk != "disabled",
                provider_kind=pk,
                hints=hints,
            )
        )
    except (OSError, TypeError, ValueError) as ex:
        rows.append(
            _row(
                "test_quality",
                "Test & quality",
                enabled=False,
                ok=False,
                provider_kind="error",
                hints=[str(ex)],
            )
        )

    try:
        sec = build_devsecops_overview_payload(
            workspace_root=workspace_root, scan_state=scan_state
        )
        en = bool(sec.get("feature_enabled"))
        pk = str(sec.get("provider_kind") or "")
        hints = [str(x) for x in (sec.get("hints") or []) if isinstance(x, str)][:5]
        rows.append(
            _row(
                "devsecops",
                "DevSecOps / compliance",
                enabled=en,
                ok=en and pk != "disabled",
                provider_kind=pk,
                hints=hints,
            )
        )
    except (OSError, TypeError, ValueError) as ex:
        rows.append(
            _row(
                "devsecops",
                "DevSecOps / compliance",
                enabled=False,
                ok=False,
                provider_kind="error",
                hints=[str(ex)],
            )
        )

    try:
        ctr = build_cross_team_release_overview(
            workspace_root=workspace_root, scan_state=scan_state
        )
        en = bool(ctr.get("feature_enabled"))
        pk = str(ctr.get("provider_kind") or "")
        hints = [str(x) for x in (ctr.get("hints") or []) if isinstance(x, str)][:5]
        rows.append(
            _row(
                "cross_team_release",
                "Cross-team release",
                enabled=en,
                ok=en and pk != "disabled",
                provider_kind=pk,
                hints=hints,
            )
        )
    except (OSError, TypeError, ValueError) as ex:
        rows.append(
            _row(
                "cross_team_release",
                "Cross-team release",
                enabled=False,
                ok=False,
                provider_kind="error",
                hints=[str(ex)],
            )
        )

    try:
        ops = build_ops_delivery_overview(
            workspace_root=workspace_root, scan_state=scan_state
        )
        en = bool(ops.get("feature_enabled"))
        pk = str(ops.get("provider_kind") or "")
        hints = [str(x) for x in (ops.get("hints") or []) if isinstance(x, str)][:5]
        rows.append(
            _row(
                "ops_delivery",
                "Ops delivery",
                enabled=en,
                ok=en and pk != "disabled",
                provider_kind=pk,
                hints=hints,
            )
        )
    except (OSError, TypeError, ValueError) as ex:
        rows.append(
            _row(
                "ops_delivery",
                "Ops delivery",
                enabled=False,
                ok=False,
                provider_kind="error",
                hints=[str(ex)],
            )
        )

    healthy_n = sum(1 for r in rows if r.get("healthy"))
    return {
        "ok": True,
        "schema_version": 1,
        "summary": {
            "connector_count": len(rows),
            "healthy_count": healthy_n,
            "degraded_count": len(rows) - healthy_n,
        },
        "connectors": rows,
    }
