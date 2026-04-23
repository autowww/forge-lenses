"""HTTP handlers for Docs Health API (invoked from ``serve.py``)."""

from __future__ import annotations

import urllib.parse
import uuid
from pathlib import Path
from typing import Any, Callable

from lenses.docs_health.closure import compute_closure_status, overlay_finding_suppressions
from lenses.docs_health.contract import contract_status_payload, resolve_project_docs_contract
from lenses.docs_health.git_branch_policy import resolve_git_branch_policy
from lenses.docs_health.feature_flag import docs_health_enabled
from lenses.docs_health.inventory import build_inventory_snapshot
from lenses.docs_health.isolation import run_docs_health_session_step
from lenses.docs_health.models import scan_run_stub
from lenses.docs_health.run_persist import (
    persist_quality_scan,
    suppressed_cluster_ids,
    user_suppressed_finding_ids,
)
from lenses.docs_health import store
from lenses.docs_health.artifacts import write_discarded_marker
from lenses.docs_health.scratch_workspace import discard_run_scratch, ensure_run_scratch_workspace
from lenses.docs_health.run_projection import merge_docs_health_session_view
from lenses.docs_health.run_sync import (
    bootstrap_docs_health_run,
    cancel_docs_health_run,
    resume_docs_health_run,
    seed_docs_health_session_timeline,
    sync_docs_health_timeline,
    tasklet_allows_new_steps,
)
from lenses.docs_health.session_projection import session_public_view
from lenses.scan import resolve_workspace_child_dir
from lenses.agent_runtime import sessions as ar_sessions
from lenses.sandbox.active import stop_session_execution
from lenses.sandbox.backends import docs_health_step_backend
from lenses.tasklet.store import create_tasklet_run

SendJson = Callable[[int, dict[str, Any]], None]


def _child_or_error(
    workspace_root: Path,
    registry: dict[str, Any],
    project_slug: str,
    send_json: SendJson,
) -> Path | None:
    child = resolve_workspace_child_dir(workspace_root, project_slug, registry)
    if child is None or not (child / ".git").is_dir():
        send_json(404, {"ok": False, "error": "not_found"})
        return None
    return child


def get_workspace_summary(
    workspace_root: Path,
    registry: dict[str, Any],
    *,
    send_json: SendJson,
) -> None:
    if not docs_health_enabled():
        send_json(404, {"ok": False, "error": "feature_disabled"})
        return
    out = store.workspace_summary(workspace_root, registry)
    send_json(200, out)


def get_workspace_work_items(
    workspace_root: Path,
    registry: dict[str, Any],
    *,
    send_json: SendJson,
) -> None:
    if not docs_health_enabled():
        send_json(404, {"ok": False, "error": "feature_disabled"})
        return
    items = store.all_open_work_items(workspace_root, registry)
    send_json(200, {"ok": True, "work_items": items})


def get_live_docs_sessions(
    workspace_root: Path,
    registry: dict[str, Any],
    *,
    send_json: SendJson,
) -> None:
    if not docs_health_enabled():
        send_json(404, {"ok": False, "error": "feature_disabled"})
        return
    rows = store.list_live_docs_health_sessions(workspace_root, registry, limit=32)
    send_json(200, {"ok": True, "sessions": rows})


def get_project_docs_health(
    workspace_root: Path,
    registry: dict[str, Any],
    project_slug: str,
    *,
    bundle: dict[str, Any],
    send_json: SendJson,
    query: str = "",
) -> None:
    if not docs_health_enabled():
        send_json(404, {"ok": False, "error": "feature_disabled"})
        return
    if not bundle.get("can_read_project"):
        send_json(403, {"ok": False, "error": "project_forbidden"})
        return
    child = _child_or_error(workspace_root, registry, project_slug, send_json)
    if child is None:
        return
    qs = urllib.parse.parse_qs((query or "").lstrip("?"))
    want_full = str(qs.get("full_inventory", [""])[0] or "").strip().lower() in ("1", "true", "yes")

    contract = resolve_project_docs_contract(child, project_slug=project_slug)
    cstatus = contract_status_payload(child, contract)
    inv_summary = store.load_latest_inventory_summary(workspace_root, project_slug)
    rdts = contract.get("required_doc_types") if isinstance(contract.get("required_doc_types"), list) else []

    latest_id = store.load_latest_run_id(workspace_root, project_slug)
    latest = store.load_run(workspace_root, project_slug, latest_id) if latest_id else None
    runs = store.list_run_summaries(workspace_root, project_slug)
    work = store.load_work_items(workspace_root, project_slug)

    def _scan_run_row(run: dict[str, Any] | None) -> dict[str, Any]:
        if not run:
            return dict(scan_run_stub())
        return {
            "id": run.get("id"),
            "status": "completed",
            "finished_at": run.get("finished_at"),
            "finding_count": run.get("finding_count"),
            "score": (run.get("score") or {}).get("value") if isinstance(run.get("score"), dict) else None,
        }

    inv_full = None
    if want_full:
        inv_full = store.load_latest_inventory_full(workspace_root, project_slug, max_documents=250)

    run_compare: dict[str, Any] | None = None
    if latest and len(runs) >= 2:
        prev_id = str(runs[1].get("id") or "").strip()
        if prev_id:
            prev_run = store.load_run(workspace_root, project_slug, prev_id)
            if isinstance(prev_run, dict):
                sv = (latest.get("score") or {}).get("value")
                pv = (prev_run.get("score") or {}).get("value")
                run_compare = {
                    "prior_run_id": prev_id,
                    "score_delta": (int(sv) - int(pv)) if isinstance(sv, int) and isinstance(pv, int) else None,
                    "finding_count_delta": int(latest.get("finding_count") or 0)
                    - int(prev_run.get("finding_count") or 0),
                }

    finding_sups = store.list_finding_suppressions(workspace_root, project_slug)
    sup_fids = user_suppressed_finding_ids(workspace_root, project_slug)
    sup_cids = suppressed_cluster_ids(workspace_root, project_slug)
    latest_view: dict[str, Any] | None = None
    closure_status: dict[str, Any] | None = None
    if isinstance(latest, dict):
        latest_view = dict(latest)
        findings_raw = latest_view.get("findings") if isinstance(latest_view.get("findings"), list) else []
        clusters_raw = latest_view.get("clusters") if isinstance(latest_view.get("clusters"), list) else []
        overlaid = overlay_finding_suppressions(
            findings_raw,
            suppressed_finding_ids=sup_fids,
            suppressed_cluster_ids=sup_cids,
            clusters=clusters_raw,
        )
        latest_view["findings"] = overlaid
        open_work_n = sum(1 for w in work if str(w.get("status", "open")).lower() != "done")
        closure_status = compute_closure_status(overlaid, work_items_open=open_work_n)

    docs_scan_run = _scan_run_row(latest_view if latest_view is not None else latest)

    from lenses.tasklet.catalog import list_tasklet_runs_for_project

    tasklet_runs = list_tasklet_runs_for_project(workspace_root, project_slug, limit=20)
    tasklet_runs_view = [
        {
            "id": str(r.get("id") or ""),
            "state": str(r.get("state") or ""),
            "stop_reason": r.get("stop_reason"),
            "updated_at": r.get("updated_at"),
            "docs_health_session_id": str(r.get("docs_health_session_id") or ""),
            "tasklet_id": str(r.get("tasklet_id") or ""),
            "last_error": (str(r.get("last_error") or "")[:400] or None),
        }
        for r in tasklet_runs
        if isinstance(r, dict)
    ]

    send_json(
        200,
        {
            "ok": True,
            "project": project_slug,
            "project_docs_contract": contract,
            "contract_status": cstatus,
            "required_doc_type_count": len(rdts),
            "inventory_summary": inv_summary,
            "latest_inventory": inv_full,
            "contract": contract,
            "latest_run": latest_view if latest_view is not None else latest,
            "run_history": runs,
            "run_compare": run_compare,
            "work_items": [w for w in work if str(w.get("status", "open")).lower() != "done"][:50],
            "tasklet_runs": tasklet_runs_view,
            "open_tasklet_followups": store.count_tasklet_followups_by_project(workspace_root, registry).get(
                project_slug,
                0,
            ),
            "docs_scan_run": docs_scan_run,
            "feature": {"docs_health": True},
            "cluster_suppressions": store.list_cluster_suppressions(workspace_root, project_slug),
            "finding_suppressions": finding_sups,
            "closure_status": closure_status,
            "recent_sessions": store.list_recent_docs_health_sessions(workspace_root, project_slug, limit=15),
        },
    )


def post_project_docs_health(
    workspace_root: Path,
    registry: dict[str, Any],
    project_slug: str,
    body: dict[str, Any],
    *,
    bundle: dict[str, Any],
    send_json: SendJson,
) -> None:
    if not docs_health_enabled():
        send_json(404, {"ok": False, "error": "feature_disabled"})
        return
    if not bundle.get("can_read_project"):
        send_json(403, {"ok": False, "error": "project_forbidden"})
        return
    child = _child_or_error(workspace_root, registry, project_slug, send_json)
    if child is None:
        return

    op = str(body.get("op") or "").strip().lower()
    if op == "ping":
        send_json(
            200,
            {
                "ok": True,
                "op": "ping",
                "project": project_slug,
                "repo_has_git": (child / ".git").is_dir(),
            },
        )
        return

    if op == "inventory":
        contract = resolve_project_docs_contract(child, project_slug=project_slug)
        snap = build_inventory_snapshot(child, project_slug=project_slug, contract=contract)
        store.write_inventory_snapshot(workspace_root, project_slug, snap)
        send_json(
            200,
            {
                "ok": True,
                "inventory_snapshot": {
                    "id": snap.get("id"),
                    "document_count": snap.get("document_count"),
                    "by_doc_type": snap.get("by_doc_type"),
                    "by_knowledge_category": snap.get("by_knowledge_category"),
                    "created_at": snap.get("created_at"),
                },
            },
        )
        return

    if op == "scan":
        run_payload, created = persist_quality_scan(workspace_root, child, project_slug)
        send_json(200, {"ok": True, "run": run_payload, "work_items_upserted": created})
        return

    if op == "suppress_cluster":
        if not bundle.get("can_write_project"):
            send_json(403, {"ok": False, "error": "write_forbidden"})
            return
        cluster_id = str(body.get("cluster_id") or "").strip()
        reason = str(body.get("reason") or "").strip()
        run_id = str(body.get("run_id") or "").strip()
        if not cluster_id or len(reason) < 3:
            send_json(400, {"ok": False, "error": "missing_cluster_or_reason"})
            return
        rows = store.add_cluster_suppression(
            workspace_root,
            project_slug,
            cluster_id=cluster_id,
            reason=reason,
            run_id=run_id or None,
        )
        send_json(200, {"ok": True, "suppressions": rows})
        return

    if op == "suppress_finding":
        if not bundle.get("can_write_project"):
            send_json(403, {"ok": False, "error": "write_forbidden"})
            return
        finding_id = str(body.get("finding_id") or "").strip()
        reason = str(body.get("reason") or "").strip()
        mode = str(body.get("mode") or "suppress").strip().lower()
        if mode not in ("suppress", "manual", "waiver"):
            mode = "suppress"
        review_at = str(body.get("review_at") or "").strip() or None
        run_id = str(body.get("run_id") or "").strip()
        if not finding_id or len(reason) < 3:
            send_json(400, {"ok": False, "error": "missing_finding_or_reason"})
            return
        rows = store.add_finding_suppression(
            workspace_root,
            project_slug,
            finding_id=finding_id,
            reason=reason,
            mode=mode,
            review_at=review_at,
            run_id=run_id or None,
        )
        send_json(200, {"ok": True, "finding_suppressions": rows})
        return

    if op == "ktlo_ticket":
        if not bundle.get("can_write_project"):
            send_json(403, {"ok": False, "error": "write_forbidden"})
            return
        cluster_id = str(body.get("cluster_id") or "").strip()
        run_id = str(body.get("run_id") or "").strip()
        session_id = str(body.get("session_id") or "").strip()
        title = str(body.get("title") or "Documentation follow-up").strip()
        summary = str(body.get("summary") or "").strip()
        evidence = str(body.get("evidence") or "").strip()
        next_steps = str(body.get("next_steps") or "").strip()
        if not summary and not evidence:
            send_json(400, {"ok": False, "error": "missing_summary_or_evidence"})
            return
        wid = f"docs-ktlo-{uuid.uuid4().hex[:14]}"
        ts = store.now_iso()
        enc_proj = urllib.parse.quote(project_slug, safe="")
        body_blob = "\n\n".join(x for x in (summary, evidence, next_steps) if x)
        item: dict[str, Any] = {
            "id": wid,
            "project": project_slug,
            "title": title,
            "status": "open",
            "kind": "ktlo",
            "source": "docs_health_master",
            "cluster_id": cluster_id or None,
            "run_id": run_id or None,
            "summary": body_blob[:8000],
            "created_at": ts,
            "updated_at": ts,
            "due": None,
            "owner": None,
            "project_docs_health_href": f"/projects/{enc_proj}/docs-health",
            "project_docs_health_master_href": f"/projects/{enc_proj}/docs-health/master",
            "workspace_md_href": f"/workspace-md?contextProject={enc_proj}",
        }
        if session_id:
            item["docs_health_session_href"] = (
                f"/projects/{enc_proj}/docs-health/session/{urllib.parse.quote(session_id)}"
            )
        store.append_work_items(workspace_root, project_slug, [item])
        send_json(200, {"ok": True, "work_item": item})
        return

    if op == "create_session":
        cluster_id = str(body.get("cluster_id") or "").strip()
        run_id = str(body.get("run_id") or "").strip()
        if not cluster_id or not run_id:
            send_json(400, {"ok": False, "error": "missing_cluster_or_run"})
            return
        run = store.load_run(workspace_root, project_slug, run_id)
        if not run:
            send_json(404, {"ok": False, "error": "run_not_found"})
            return
        clusters = run.get("clusters") or []
        cluster = next((c for c in clusters if isinstance(c, dict) and str(c.get("id")) == cluster_id), None)
        if not cluster:
            send_json(404, {"ok": False, "error": "cluster_not_found"})
            return
        fids = set(cluster.get("finding_ids") or [])
        findings = [f for f in (run.get("findings") or []) if isinstance(f, dict) and str(f.get("id")) in fids]
        sid = uuid.uuid4().hex
        cluster_label = str(cluster.get("label") or cluster_id).strip()
        display_name = f"Docs remediation · {project_slug} · {cluster_label}"
        sess_usage = {
            "calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated": False,
            "by_slot": {},
        }
        score_obj = run.get("score") if isinstance(run.get("score"), dict) else {}
        _bs = score_obj.get("value")
        baseline_score = int(_bs) if isinstance(_bs, (int, float)) else None
        enc_proj = urllib.parse.quote(project_slug, safe="")
        _bpolicy = resolve_git_branch_policy(child, workspace_root)
        session: dict[str, Any] = {
            "id": sid,
            "project": project_slug,
            "display_name": display_name,
            "run_id": run_id,
            "cluster_id": cluster_id,
            "status": "running",
            "started_at": store.now_iso(),
            "baseline_score": baseline_score,
            "suggested_git_branch": _bpolicy.format_docs_health_branch(sid),
            "git_branch_policy": {
                "source": _bpolicy.source,
                "trunk": _bpolicy.trunk,
                "style": _bpolicy.style,
            },
            "knowledge_links": {
                "docs_health": f"/projects/{enc_proj}/docs-health",
                "docs_health_master": f"/projects/{enc_proj}/docs-health/master",
                "workspace_md": f"/workspace-md?contextProject={enc_proj}",
            },
            "events": [
                {
                    "type": "summary",
                    "title": "Remediation session",
                    "body": f"Working on: {cluster.get('label', cluster_id)}",
                    "ts": store.now_iso(),
                },
                {
                    "type": "plan",
                    "steps": [
                        "Cluster brief (agent)",
                        "Enrich findings",
                        "Draft safe markdown / diagram / ADR (agents)",
                        "Rule + reviewer pass",
                        "Preview — create git branch locally before Apply",
                        "Verify scan",
                    ],
                    "ts": store.now_iso(),
                },
                {
                    "type": "work_item",
                    "title": str(cluster.get("label") or "Documentation cluster"),
                    "cluster_id": cluster_id,
                    "run_id": run_id,
                    "finding_count": len(findings),
                    "ts": store.now_iso(),
                },
            ],
            "usage_session": sess_usage,
            "findings_snapshot": findings,
            "cluster": cluster,
        }
        ar_sess = ar_sessions.create_session(
            workspace_root,
            kind="docs_health_remediation",
            project_slug=project_slug,
            docs_health_run_id=run_id,
            cluster_id=cluster_id,
            agent={"id": "docs_health_remediation", "version": 1, "label": "Docs remediation"},
            metadata={"docs_health_session_id": sid},
        )
        session["agent_runtime_session_id"] = str(ar_sess.get("id") or "")
        sb = docs_health_step_backend()
        tr = create_tasklet_run(
            workspace_root,
            tasklet_id="docs_health_remediation",
            tasklet_version=1,
            kind="docs_health_remediation",
            project_slug=project_slug,
            docs_health_session_id=sid,
            agent_runtime_session_id=str(ar_sess.get("id") or ""),
            sandbox_backend=sb,
            metadata={"cluster_id": cluster_id, "scan_run_id": run_id},
        )
        session["tasklet_run_id"] = str(tr.get("id") or "")
        session["tasklet"] = {"id": "docs_health_remediation", "version": 1}
        session["execution"] = {"step_backend": sb, "resumable": True}
        session["scratch_workspace"] = ensure_run_scratch_workspace(child, workspace_root, project_slug, sid)
        store.write_session(workspace_root, project_slug, session)
        seed_docs_health_session_timeline(workspace_root, str(tr.get("id") or ""), session.get("events") or [])
        bootstrap_docs_health_run(workspace_root, str(tr.get("id") or ""))
        merged = merge_docs_health_session_view(workspace_root, project_slug, sid)
        send_json(200, {"ok": True, "session": merged or session_public_view(session)})
        return

    if op == "session_resume":
        sid = str(body.get("session_id") or "").strip()
        if not sid:
            send_json(400, {"ok": False, "error": "missing_session_id"})
            return
        sess = store.load_session(workspace_root, project_slug, sid)
        if not sess:
            send_json(404, {"ok": False, "error": "session_not_found"})
            return
        tr_id = str(sess.get("tasklet_run_id") or "").strip()
        if not tr_id:
            send_json(400, {"ok": False, "error": "missing_tasklet_run"})
            return
        ok, err = resume_docs_health_run(workspace_root, tr_id)
        if not ok:
            send_json(
                400,
                {"ok": False, "error": "resume_failed", "detail": err or "not_stopped"},
            )
            return
        store.clear_session_cancel_flag(workspace_root, project_slug, sid)
        now = store.now_iso()
        sess["status"] = "running"
        sess.setdefault("events", []).append(
            {
                "type": "summary",
                "title": "Session resumed",
                "body": "Tasklet run is active again; the next sandbox step starts a new Docker container using persisted session and checkpoint state.",
                "ts": now,
            }
        )
        store.write_session(workspace_root, project_slug, sess)
        merged = merge_docs_health_session_view(workspace_root, project_slug, sid)
        send_json(200, {"ok": True, "session": merged or session_public_view(sess)})
        return

    if op == "session_cancel":
        # Same trust as ``session_get`` / non-apply ``session_step``: updates
        # ``.lenses-local/docs-health/...`` only (not repo files). Repo writes
        # remain gated on ``apply`` / ``work_complete`` / suppressions.
        sid = str(body.get("session_id") or "").strip()
        if not sid:
            send_json(400, {"ok": False, "error": "missing_session_id"})
            return
        sess = store.load_session(workspace_root, project_slug, sid)
        if not sess:
            send_json(404, {"ok": False, "error": "session_not_found"})
            return
        st = str(sess.get("status") or "").lower()
        if st == "cancelled":
            merged_ac = merge_docs_health_session_view(workspace_root, project_slug, sid)
            send_json(200, {"ok": True, "already_cancelled": True, "session": merged_ac or session_public_view(sess)})
            return
        if st == "completed":
            merged_done = merge_docs_health_session_view(workspace_root, project_slug, sid)
            send_json(
                400,
                {
                    "ok": False,
                    "error": "session_already_completed",
                    "session": merged_done or session_public_view(sess),
                },
            )
            return
        now = store.now_iso()
        store.write_session_cancel_flag(workspace_root, project_slug, sid)
        stop_session_execution(sid)
        dr = discard_run_scratch(child, workspace_root, project_slug, sid)
        write_discarded_marker(workspace_root, project_slug, sid, reason="session_cancelled")
        sess["scratch_discarded"] = dr
        sess["status"] = "cancelled"
        sess["cancelled_at"] = now
        sess.setdefault("events", []).append(
            {
                "type": "summary",
                "title": "Session stopped",
                "body": (
                    "Cancelled from the runner UI. In-flight sandbox or worker processes are stopped; "
                    "further steps are rejected."
                ),
                "ts": now,
            }
        )
        store.write_session(workspace_root, project_slug, sess)
        tr_id = str(sess.get("tasklet_run_id") or "").strip()
        if tr_id:
            cancel_docs_health_run(workspace_root, tr_id)
        ar_id = str(sess.get("agent_runtime_session_id") or "").strip()
        if ar_id:
            ar_sess = ar_sessions.load_session(workspace_root, ar_id)
            if ar_sess:
                ar_sess["status"] = "cancelled"
                ar_sessions.save_session(workspace_root, ar_sess)
            ar_sessions.append_event(
                workspace_root,
                ar_id,
                "docs_health_session_cancelled",
                {"docs_health_session_id": sid, "project": project_slug},
            )
        merged = merge_docs_health_session_view(workspace_root, project_slug, sid)
        send_json(200, {"ok": True, "session": merged or session_public_view(sess)})
        return

    if op == "session_get":
        sid = str(body.get("session_id") or "").strip()
        if not sid:
            send_json(400, {"ok": False, "error": "missing_session_id"})
            return
        sess = store.load_session(workspace_root, project_slug, sid)
        if not sess:
            send_json(404, {"ok": False, "error": "session_not_found"})
            return
        merged = merge_docs_health_session_view(workspace_root, project_slug, sid)
        send_json(200, {"ok": True, "session": merged or session_public_view(sess)})
        return

    if op == "session_reply":
        sid = str(body.get("session_id") or "").strip()
        if not sid:
            send_json(400, {"ok": False, "error": "missing_session_id"})
            return
        sess = store.load_session(workspace_root, project_slug, sid)
        if not sess:
            send_json(404, {"ok": False, "error": "session_not_found"})
            return
        st0 = str(sess.get("status") or "").lower()
        if st0 in ("cancelled", "completed", "failed"):
            send_json(
                409,
                {
                    "ok": False,
                    "error": "session_not_active",
                    "detail": st0,
                    "session": merge_docs_health_session_view(workspace_root, project_slug, sid)
                    or session_public_view(sess),
                },
            )
            return
        ar_id = str(sess.get("agent_runtime_session_id") or "").strip() or None
        reply_ev_base = len(sess.get("events") or [])
        reply_text = str(body.get("reply_text") or "").strip()
        choice_id = str(body.get("choice_id") or "").strip()
        confirm = body.get("confirm")

        def push_reply(ev: dict[str, Any]) -> None:
            ev.setdefault("ts", store.now_iso())
            sess.setdefault("events", []).append(ev)

        entry: dict[str, Any] = {
            "type": "user_reply",
            "body": reply_text,
            "choice_id": choice_id or None,
        }
        if isinstance(confirm, bool):
            entry["confirm"] = confirm
        push_reply(entry)
        st = str(sess.get("status") or "").lower()
        if st == "awaiting_input":
            if choice_id == "retry_draft":
                sess["status"] = "running"
            elif reply_text:
                prev = str(sess.get("user_clarification_notes") or "").strip()
                sess["user_clarification_notes"] = (prev + "\n" + reply_text).strip() if prev else reply_text
                sess["status"] = "running"
            else:
                sess["status"] = "running"
        elif st == "awaiting_approval" and isinstance(confirm, bool):
            push_reply(
                {
                    "type": "summary",
                    "title": "Operator confirmation",
                    "body": "Confirmed" if confirm else "Declined",
                }
            )
        store.write_session(workspace_root, project_slug, sess)
        tr_id = str(sess.get("tasklet_run_id") or "").strip()
        if tr_id:
            sync_docs_health_timeline(
                workspace_root,
                project_slug,
                sess,
                step="session_reply",
                timeline_slice=(sess.get("events") or [])[reply_ev_base:],
            )
        if ar_id:
            ar_sessions.append_event(
                workspace_root,
                ar_id,
                "docs_health_user_reply",
                {"choice_id": choice_id, "has_text": bool(reply_text)},
            )
        merged = merge_docs_health_session_view(workspace_root, project_slug, sid)
        send_json(200, {"ok": True, "session": merged or session_public_view(sess)})
        return

    if op == "session_step":
        sid = str(body.get("session_id") or "").strip()
        step = str(body.get("step") or "").strip().lower()
        sess = store.load_session(workspace_root, project_slug, sid)
        if not sess:
            send_json(404, {"ok": False, "error": "session_not_found"})
            return
        st0 = str(sess.get("status") or "").lower()
        if st0 in ("cancelled", "completed", "failed"):
            send_json(
                409,
                {
                    "ok": False,
                    "error": "session_not_active",
                    "detail": st0,
                    "session": merge_docs_health_session_view(workspace_root, project_slug, sid)
                    or session_public_view(sess),
                },
            )
            return
        if not tasklet_allows_new_steps(workspace_root, sess):
            send_json(
                409,
                {
                    "ok": False,
                    "error": "session_not_active",
                    "detail": "tasklet_terminal",
                    "session": merge_docs_health_session_view(workspace_root, project_slug, sid)
                    or session_public_view(sess),
                },
            )
            return
        code, resp = run_docs_health_session_step(
            workspace_root,
            child,
            project_slug,
            sess,
            step,
            bundle,
        )
        send_json(code, resp)
        return

    if op == "work_complete":
        wid = str(body.get("work_item_id") or "").strip()
        if not wid:
            send_json(400, {"ok": False, "error": "missing_work_item_id"})
            return
        if wid.startswith("tasklet-followup-"):
            send_json(
                400,
                {
                    "ok": False,
                    "error": "not_persisted_work_item",
                    "detail": "tasklet_runtime_followups_complete_in_session",
                },
            )
            return
        if not bundle.get("can_write_project"):
            send_json(403, {"ok": False, "error": "write_forbidden"})
            return
        updated = store.update_work_item(workspace_root, project_slug, wid, status="done")
        if not updated:
            send_json(404, {"ok": False, "error": "work_item_not_found"})
            return
        send_json(200, {"ok": True, "work_item": updated})
        return

    send_json(400, {"ok": False, "error": "unknown_op"})
