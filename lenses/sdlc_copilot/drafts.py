"""Structured draft proposals (no silent writes until operator commits)."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lenses.cross_team_release import build_cross_team_release_overview
from lenses.devsecops_compliance.aggregate import build_devsecops_overview_payload
from lenses.ops_delivery.aggregate import build_ops_delivery_overview
from lenses.test_quality.aggregate import build_quality_overview_payload

_PROPOSAL_TTL_SEC = 48 * 3600

_PR_URL_RE = re.compile(
    r"https://github\.com/[\w.-]+/[\w.-]+/pull/(\d+)",
    re.IGNORECASE,
)
_WBSISH = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")


def proposals_dir(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / "copilot-proposals"


def exports_dir(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / "copilot-exports"


def build_tool_proposals(
    user_message: str,
    workspace_root: Path,
    scan_state: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Return proposal dicts without ``id`` — each has tool_id, title, payload (JSON-serializable).
    Heuristic keyword triggers; safe to call only when caller already allowed propose_writes.
    """
    um = (user_message or "").lower()
    out: list[dict[str, Any]] = []

    if any(k in um for k in ("risk exception", "compliance exception", "security exception")):
        doc = build_devsecops_overview_payload(
            workspace_root=workspace_root, scan_state=scan_state
        )
        ex = [e for e in (doc.get("exceptions") or []) if isinstance(e, dict)][:5]
        out.append(
            {
                "tool_id": "risk_exception_draft",
                "title": "Draft compliance / risk exception record",
                "payload": {
                    "status": "draft",
                    "summary": "Time-bound exception with owner, scope, compensating controls, and expiry.",
                    "related_open_exceptions": [
                        {k: e.get(k) for k in ("id", "title", "status", "expires_on") if k in e}
                        for e in ex
                    ],
                    "template_fields": {
                        "control_id": "",
                        "finding_ids": [],
                        "business_justification": "",
                        "expiry": "",
                        "owner": "",
                        "approver": "",
                    },
                },
            }
        )

    if "test plan" in um or "testplan" in um.replace(" ", ""):
        q = build_quality_overview_payload(
            workspace_root=workspace_root, scan_state=scan_state
        )
        plans = [p for p in (q.get("test_plans") or []) if isinstance(p, dict)][:5]
        out.append(
            {
                "tool_id": "test_plan_draft",
                "title": "Draft test plan scaffold",
                "payload": {
                    "status": "draft",
                    "existing_plans": [
                        {k: p.get(k) for k in ("id", "name", "project") if k in p} for p in plans
                    ],
                    "sections": [
                        "scope",
                        "environments",
                        "entry_exit_criteria",
                        "suites_and_cases",
                        "defect_handling",
                        "signoff",
                    ],
                },
            }
        )

    if any(
        k in um
        for k in (
            "link pr",
            "link pull",
            "pull request",
            "merge request",
            "work item",
        )
    ):
        m = _PR_URL_RE.search(user_message or "")
        pr_url = m.group(0) if m else ""
        wbs_ids = _WBSISH.findall(user_message or "")
        out.append(
            {
                "tool_id": "link_pr_to_work_item",
                "title": "Proposed PR ↔ work item link",
                "payload": {
                    "status": "draft",
                    "pr_url": pr_url,
                    "suggested_work_item_ids": wbs_ids,
                    "note": "Confirm IDs and paste into your ALM or extend orchestration graph import.",
                },
            }
        )

    if any(
        k in um
        for k in (
            "release readiness",
            "go/no-go",
            "go no-go",
            "gono-go",
            "readiness summary",
        )
    ):
        ctr = build_cross_team_release_overview(
            workspace_root=workspace_root, scan_state=scan_state
        )
        pkt = ctr.get("go_no_go_packet") if isinstance(ctr, dict) else {}
        md = str(pkt.get("markdown") or "") if isinstance(pkt, dict) else ""
        comm = ctr.get("communication_artifacts") if isinstance(ctr, dict) else {}
        stake = str(comm.get("stakeholder_summary_md") or "") if isinstance(comm, dict) else ""
        out.append(
            {
                "tool_id": "release_readiness_summary",
                "title": "Release readiness summary (from live packet)",
                "payload": {
                    "status": "draft",
                    "go_no_go_excerpt": md[:4000],
                    "stakeholder_summary_excerpt": stake[:2000],
                },
            }
        )

    if "rollback" in um:
        ctr = build_cross_team_release_overview(
            workspace_root=workspace_root, scan_state=scan_state
        )
        crs = [c for c in (ctr.get("change_requests") or []) if isinstance(c, dict)]
        roll_lines = []
        for c in crs[:8]:
            rn = c.get("rollback_notes")
            if rn:
                roll_lines.append(f"{c.get('id', '?')}: {rn}")
        live = ctr.get("live_enrichment") if isinstance(ctr, dict) else {}
        targets = live.get("rollback_targets") if isinstance(live, dict) else []
        out.append(
            {
                "tool_id": "rollback_notes",
                "title": "Rollback notes (from change requests + live enrichment)",
                "payload": {
                    "status": "draft",
                    "per_change_request": roll_lines,
                    "rollback_targets": targets if isinstance(targets, list) else [],
                },
            }
        )

    if "postmortem" in um or "post-mortem" in um:
        ops = build_ops_delivery_overview(workspace_root=workspace_root, scan_state=scan_state)
        inc = [i for i in (ops.get("incidents") or []) if isinstance(i, dict)][:5]
        tmpl = [t for t in (ops.get("postmortem_templates") or []) if isinstance(t, dict)][:2]
        out.append(
            {
                "tool_id": "postmortem_stub",
                "title": "Post-incident review stub",
                "payload": {
                    "status": "draft",
                    "incidents_sample": [
                        {k: i.get(k) for k in ("id", "title", "severity", "status") if k in i}
                        for i in inc
                    ],
                    "template_hints": tmpl,
                    "sections": [
                        "summary",
                        "customer_impact",
                        "timeline",
                        "root_cause",
                        "what_went_well",
                        "what_went_wrong",
                        "action_items",
                    ],
                },
            }
        )

    return out


def persist_proposals(
    workspace_root: Path,
    proposals: list[dict[str, Any]],
    *,
    audit_id: str,
    login: str | None,
    project_slug: str | None,
) -> list[dict[str, Any]]:
    """Write each proposal to disk; return the same list with ``id`` and ``created_at``."""
    d = proposals_dir(workspace_root)
    d.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    saved: list[dict[str, Any]] = []
    for p in proposals:
        pid = str(uuid.uuid4())
        env = {
            "id": pid,
            "created_at": now,
            "audit_id": audit_id,
            "session_login": (login or "").strip().lower() or None,
            "project_slug": (project_slug or "").strip() or None,
            "tool_id": p.get("tool_id"),
            "title": p.get("title"),
            "payload": p.get("payload"),
        }
        fp = d / f"{pid}.json"
        fp.write_text(json.dumps(env, indent=2, ensure_ascii=False), encoding="utf-8")
        try:
            fp.chmod(0o600)
        except OSError:
            pass
        saved.append(
            {
                "id": pid,
                "tool_id": p.get("tool_id"),
                "title": p.get("title"),
                "payload": p.get("payload"),
                "created_at": now,
            }
        )
    return saved


def load_proposal(workspace_root: Path, proposal_id: str) -> dict[str, Any] | None:
    pid = (proposal_id or "").strip()
    if not pid or ".." in pid or "/" in pid or "\\" in pid:
        return None
    fp = proposals_dir(workspace_root) / f"{pid}.json"
    if not fp.is_file():
        return None
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def proposal_is_fresh(record: dict[str, Any], *, now_ts: float | None = None) -> bool:
    from datetime import datetime as dt

    raw = str(record.get("created_at") or "")
    try:
        t = dt.fromisoformat(raw.replace("Z", "+00:00"))
        ts = t.timestamp()
    except ValueError:
        return False
    if now_ts is None:
        now_ts = datetime.now(timezone.utc).timestamp()
    return now_ts - ts <= _PROPOSAL_TTL_SEC


def export_committed_proposal(workspace_root: Path, record: dict[str, Any]) -> Path:
    """Write a human-readable export under ``copilot-exports/``; return path."""
    ex = exports_dir(workspace_root)
    ex.mkdir(parents=True, exist_ok=True)
    pid = str(record.get("id") or "unknown")
    tool = str(record.get("tool_id") or "draft")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fn = f"{stamp}_{tool}_{pid[:8]}.md"
    path = ex / fn
    body = [
        f"# Copilot draft export",
        f"",
        f"- proposal_id: `{pid}`",
        f"- tool_id: `{tool}`",
        f"- title: {record.get('title')}",
        f"",
        "```json",
        json.dumps(record.get("payload"), indent=2, ensure_ascii=False),
        "```",
        "",
    ]
    path.write_text("\n".join(body), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def delete_proposal_file(workspace_root: Path, proposal_id: str) -> None:
    pid = (proposal_id or "").strip()
    if not pid:
        return
    fp = proposals_dir(workspace_root) / f"{pid}.json"
    try:
        fp.unlink(missing_ok=True)
    except OSError:
        pass
