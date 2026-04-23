"""Persist deterministic quality scans and shared scan helpers (used by API + session steps)."""

from __future__ import annotations

import urllib.parse
import uuid
from pathlib import Path
from typing import Any

from lenses.docs_health.contract import resolve_project_docs_contract
from lenses.docs_health.scanner import run_deterministic_scan
from lenses.docs_health import store


def finding_id_set(findings: Any) -> set[str]:
    out: set[str] = set()
    for f in findings or []:
        if isinstance(f, dict) and str(f.get("id") or "").strip():
            out.add(str(f.get("id")))
    return out


def build_docs_debt_work_items(project_slug: str, run_id: str, findings: list[Any]) -> list[dict[str, Any]]:
    enc_proj = urllib.parse.quote(project_slug, safe="")
    href = f"/projects/{enc_proj}/docs-health"
    out: list[dict[str, Any]] = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        fid = str(f.get("id") or "").strip()
        if not fid:
            continue
        fix = str(f.get("fixability") or "")
        sev = str(f.get("severity") or "").lower()
        suppressed = f.get("suppressed") is True
        track = (
            suppressed
            or fix in ("ticket_only", "manual")
            or sev in ("critical", "major")
        )
        if not track:
            continue
        wid = f"docs-debt-{fid}"
        ts = store.now_iso()
        out.append(
            {
                "id": wid,
                "project": project_slug,
                "title": str(f.get("title") or "Documentation debt"),
                "status": "open",
                "kind": "ktlo",
                "source": "docs_health_scan",
                "finding_id": fid,
                "run_id": run_id,
                "severity": f.get("severity"),
                "fixability": fix,
                "expected_score_impact": f.get("expected_score_impact"),
                "summary": f.get("summary"),
                "created_at": ts,
                "updated_at": ts,
                "due": None,
                "owner": None,
                "project_docs_health_href": href,
                "finding_anchor": fid,
            }
        )
    return out


def persist_quality_scan(
    workspace_root: Path,
    child: Path,
    project_slug: str,
    *,
    follows_session: str | None = None,
) -> tuple[dict[str, Any], int]:
    contract = resolve_project_docs_contract(child, project_slug=project_slug)
    started = store.now_iso()
    prior_id = store.load_latest_run_id(workspace_root, project_slug)
    prior_run = store.load_run(workspace_root, project_slug, prior_id) if prior_id else None
    prior_ids = finding_id_set(prior_run.get("findings") if prior_run else [])
    inv_full = store.load_latest_inventory_full(workspace_root, project_slug, max_documents=5000)
    scan = run_deterministic_scan(child, contract, inventory_snapshot=inv_full)
    current_ids = finding_id_set(scan.get("findings"))
    if prior_run is not None and prior_id:
        finding_diff = store.update_finding_lifecycle(
            workspace_root, project_slug, prior_ids=prior_ids, current_ids=current_ids
        )
    else:
        finding_diff = {
            "resolved_from_prior_scan": [],
            "new_since_prior_scan": sorted(current_ids),
            "reopened_findings": [],
        }
    rid = uuid.uuid4().hex
    run_payload: dict[str, Any] = {
        "id": rid,
        "project": project_slug,
        "started_at": started,
        "finished_at": store.now_iso(),
        "contract_version": contract.get("version"),
        "finding_count": len(scan.get("findings") or []),
        "score": scan.get("score"),
        "inventory": scan.get("inventory"),
        "findings": scan.get("findings"),
        "clusters": scan.get("clusters"),
        "prior_run_id": prior_id,
        "finding_diff": finding_diff,
    }
    if follows_session and str(follows_session).strip():
        run_payload["follows_session"] = str(follows_session).strip()
    store.write_run(workspace_root, project_slug, run_payload)
    work_items = build_docs_debt_work_items(project_slug, rid, scan.get("findings") or [])
    n = store.upsert_docs_debt_work_items(workspace_root, project_slug, work_items)
    return run_payload, n


def user_suppressed_finding_ids(workspace_root: Path, project_slug: str) -> set[str]:
    out: set[str] = set()
    for row in store.list_finding_suppressions(workspace_root, project_slug):
        if not isinstance(row, dict):
            continue
        mode = str(row.get("mode") or "suppress").strip().lower()
        if mode not in ("suppress", "manual", "waiver"):
            continue
        fid = str(row.get("finding_id") or "").strip()
        if fid:
            out.add(fid)
    return out


def suppressed_cluster_ids(workspace_root: Path, project_slug: str) -> set[str]:
    out: set[str] = set()
    for row in store.list_cluster_suppressions(workspace_root, project_slug):
        if not isinstance(row, dict):
            continue
        cid = str(row.get("cluster_id") or "").strip()
        if cid:
            out.add(cid)
    return out
