"""Docs Health remediation step execution (draft vs apply boundary, tasklet checkpoints, artifacts)."""

from __future__ import annotations

import json
import time
import urllib.parse
from pathlib import Path
from typing import Any

from lenses.agent_runtime import sessions as ar_sessions
from lenses.docs_health.agents import (
    parse_docs_patch,
    parse_review_json,
    run_cluster_agent,
    run_decision_agent,
    run_diagram_agent,
    run_enricher,
    run_reviewer,
    run_writer,
)
from lenses.docs_health.artifacts import (
    list_artifact_manifest,
    load_apply_gate,
    load_patch_for_apply,
    mark_apply_consumed,
    write_apply_ready_artifact,
    write_diff_preview_artifact,
    write_patch_bundle_manifest,
    write_proposed_patch_artifact,
)
from lenses.docs_health.scratch_workspace import ensure_run_scratch_workspace, write_patch_to_scratch
from lenses.docs_health.closure import compute_closure_status, overlay_finding_suppressions
from lenses.docs_health.contract import resolve_project_docs_contract
from lenses.docs_health.patch_precheck import precheck_docs_patch
from lenses.docs_health.run_persist import (
    persist_quality_scan,
    suppressed_cluster_ids,
    user_suppressed_finding_ids,
)
from lenses.docs_health.run_projection import enrich_docs_health_session_view, merge_docs_health_session_view
from lenses.docs_health.run_sync import mark_verify_phase_started, sync_docs_health_timeline
from lenses.docs_health import store
from lenses.docs_health.session_projection import _elapsed_seconds, redact_secrets, session_public_view
from lenses.docs_health.verification_pipeline import run_post_apply_verification
from lenses.tasklet.registry import resolve_tasklet


def _session_response(workspace_root: Path, project_slug: str, sess: dict[str, Any]) -> dict[str, Any]:
    sid = str(sess.get("id") or "").strip()
    if sid and sess.get("tasklet_run_id"):
        merged = merge_docs_health_session_view(workspace_root, project_slug, sid)
        if merged is not None:
            return merged
    enrich_docs_health_session_view(workspace_root, project_slug, sess)
    return session_public_view(sess)


def _stage_proposed_patch(
    workspace_root: Path,
    project_slug: str,
    sess: dict[str, Any],
    patch: dict[str, str],
    *,
    kind: str | None,
    child: Path,
) -> dict[str, Any]:
    """
    Write draft content only under the run scratch root; persist artifacts + diff preview.
    Source checkout ``child`` is not modified (diff preview reads old file read-only).
    """
    sid = str(sess.get("id") or "").strip()
    sw = ensure_run_scratch_workspace(child, workspace_root, project_slug, sid)
    sess["scratch_workspace"] = sw
    scratch_root = Path(str(sw.get("worktree_path") or ""))
    wr: dict[str, Any] = {"ok": False}
    if sw.get("ok") and scratch_root.is_dir():
        wr = write_patch_to_scratch(scratch_root, patch)
    if wr.get("ok"):
        chk = precheck_docs_patch(scratch_root, project_slug=project_slug, patch=patch)
    else:
        chk = {
            "ok": False,
            "notes": str(wr.get("error") or "scratch_write_failed"),
            "warnings": [],
        }
    write_diff_preview_artifact(workspace_root, project_slug, sid, child, patch)
    staged_ok = bool(wr.get("ok") and chk.get("ok"))
    if staged_ok:
        write_proposed_patch_artifact(
            workspace_root,
            project_slug,
            sid,
            patch,
            kind=kind,
            scratch_write=wr if isinstance(wr, dict) else None,
        )
        write_patch_bundle_manifest(
            workspace_root,
            project_slug,
            sid,
            paths=[str(patch.get("path") or "").strip()],
            scratch_root=str(scratch_root) if scratch_root.parts else None,
        )
    sha = str(wr.get("sha256") or "").strip()
    if staged_ok and sha:
        write_apply_ready_artifact(workspace_root, project_slug, sid, sha256=sha)
        sess["apply_gate"] = {"status": "pending_apply", "sha256": sha}
    else:
        sess["apply_gate"] = {"status": "blocked", "notes": chk.get("notes")}
    sess["scratch_worktree"] = {
        "path": str(scratch_root),
        "preview_rel_path": str(patch.get("path") or "").strip(),
        "source": sw.get("source"),
    }
    sess["artifact_manifest"] = list_artifact_manifest(workspace_root, project_slug, sid)
    sess["patch_preview"] = {
        "artifact": "diff_preview.patch",
        "apply_artifact": "proposed_patch.json",
        "apply_ready": staged_ok,
    }
    return {"precheck": chk, "scratch_write": wr}


def execute_docs_health_session_step(
    workspace_root: Path,
    child: Path,
    project_slug: str,
    sess: dict[str, Any],
    step: str,
    bundle: dict[str, Any],
) -> tuple[int, dict[str, Any]]:
    """
    Run one remediation step. Mutates ``sess`` and persists via ``store.write_session``.

    Returns ``(http_status, body)``. Apply / verify may write the live repo (gated by bundle).
    """
    sid = str(sess.get("id") or "").strip()
    if sid and store.is_session_cancel_requested(workspace_root, project_slug, sid):
        return (
            409,
            {
                "ok": False,
                "error": "session_not_active",
                "detail": "cancel_requested",
                "session": _session_response(workspace_root, project_slug, sess),
            },
        )

    if str(sess.get("tasklet_run_id") or "").strip():
        tr = sess.get("tasklet") if isinstance(sess.get("tasklet"), dict) else {}
        tid = str(tr.get("id") or "docs_health_remediation").strip()
        ver = int(tr.get("version") or 1)
        if not resolve_tasklet(tid, ver):
            return (
                400,
                {
                    "ok": False,
                    "error": "tasklet_not_registered",
                    "detail": f"{tid}@{ver}",
                    "session": _session_response(workspace_root, project_slug, sess),
                },
            )

    step = str(step or "").strip().lower()
    ar_id = str(sess.get("agent_runtime_session_id") or "").strip() or None
    usage = sess.setdefault("usage_session", {})
    cluster = sess.get("cluster") or {}
    findings = sess.get("findings_snapshot") or []

    def push(ev: dict[str, Any]) -> None:
        ev.setdefault("ts", store.now_iso())
        sess.setdefault("events", []).append(ev)

    usage_at_step_start = {
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
    }
    t_step_mono = time.monotonic()

    def append_step_metric() -> None:
        """Per-invocation LLM / step cost (deltas vs start of this handler)."""
        pt0 = int(usage_at_step_start["prompt_tokens"])
        ct0 = int(usage_at_step_start["completion_tokens"])
        tt0 = int(usage_at_step_start["total_tokens"])
        if tt0 == 0 and (pt0 or ct0):
            tt0 = pt0 + ct0
        pt1 = int(usage.get("prompt_tokens") or 0)
        ct1 = int(usage.get("completion_tokens") or 0)
        tt1 = int(usage.get("total_tokens") or 0)
        if tt1 == 0 and (pt1 or ct1):
            tt1 = pt1 + ct1
        st_gate = str(sess.get("status") or "").strip().lower()
        gate = st_gate if st_gate in ("awaiting_input", "awaiting_approval") else None
        row: dict[str, Any] = {
            "step": step,
            "prompt_tokens": max(0, pt1 - pt0),
            "completion_tokens": max(0, ct1 - ct0),
            "total_tokens": max(0, tt1 - tt0),
            "elapsed_ms": int((time.monotonic() - t_step_mono) * 1000),
            "ts": store.now_iso(),
        }
        if gate:
            row["gate"] = gate
        sess.setdefault("step_metrics", []).append(row)

    if step == "enrich":
        ev_base = len(sess.get("events") or [])
        res = run_enricher(
            workspace_root,
            project_name=project_slug,
            cluster=cluster,
            findings=findings,
            sess_usage=usage,
            runtime_session_id=ar_id,
            scan_run_id=str(sess.get("run_id") or ""),
            cluster_id=str(sess.get("cluster_id") or ""),
        )
        text = str(res.get("text") or "").strip() or "(no response)"
        push({"type": "summary", "title": "Finding context", "body": text})
        push({"type": "token_stats", "snapshot": dict(usage), "last_model": res.get("model")})
        sess["enricher_text"] = text
        sess["status"] = "running"
        store.write_session(workspace_root, project_slug, sess)
        sync_docs_health_timeline(
            workspace_root,
            project_slug,
            sess,
            step=step,
            timeline_slice=(sess.get("events") or [])[ev_base:],
        )
        if ar_id:
            ar_sessions.append_event(
                workspace_root,
                ar_id,
                "docs_health_step",
                {"step": "enrich", "ok": bool(res.get("ok"))},
            )
        append_step_metric()
        return (
            200,
            {"ok": True, "session": _session_response(workspace_root, project_slug, sess), "llm": {"ok": bool(res.get("ok"))}},
        )

    if step == "cluster_brief":
        ev_base = len(sess.get("events") or [])
        res = run_cluster_agent(
            workspace_root,
            project_name=project_slug,
            cluster=cluster if isinstance(cluster, dict) else {},
            findings=findings if isinstance(findings, list) else [],
            sess_usage=usage,
            runtime_session_id=ar_id,
            scan_run_id=str(sess.get("run_id") or ""),
            cluster_id=str(sess.get("cluster_id") or ""),
        )
        text = str(res.get("text") or "").strip() or "(no response)"
        push({"type": "summary", "title": "Cluster agent", "body": text})
        push({"type": "token_stats", "snapshot": dict(usage), "last_model": res.get("model")})
        sess["cluster_brief_text"] = text
        sess["status"] = "running"
        store.write_session(workspace_root, project_slug, sess)
        sync_docs_health_timeline(
            workspace_root,
            project_slug,
            sess,
            step=step,
            timeline_slice=(sess.get("events") or [])[ev_base:],
        )
        if ar_id:
            ar_sessions.append_event(
                workspace_root,
                ar_id,
                "docs_health_step",
                {"step": "cluster_brief", "ok": bool(res.get("ok"))},
            )
        append_step_metric()
        return (
            200,
            {"ok": True, "session": _session_response(workspace_root, project_slug, sess), "llm": {"ok": bool(res.get("ok"))}},
        )

    if step == "diagram_draft":
        ev_base = len(sess.get("events") or [])
        prior_parts = [
            str(sess.get("enricher_text") or ""),
            str(sess.get("cluster_brief_text") or ""),
        ]
        prior = "\n\n".join(p for p in prior_parts if p.strip()) or "See findings cluster."
        res = run_diagram_agent(
            workspace_root,
            project_name=project_slug,
            cluster=cluster if isinstance(cluster, dict) else {},
            findings=findings if isinstance(findings, list) else [],
            prior_summary=prior,
            sess_usage=usage,
            runtime_session_id=ar_id,
            scan_run_id=str(sess.get("run_id") or ""),
            cluster_id=str(sess.get("cluster_id") or ""),
        )
        text = str(res.get("text") or "")
        patch = parse_docs_patch(text)
        push({"type": "token_stats", "snapshot": dict(usage), "last_model": res.get("model")})
        if patch:
            staged = _stage_proposed_patch(
                workspace_root, project_slug, sess, patch, kind="diagram", child=child
            )
            chk = staged["precheck"]
            push({"type": "verification", "ok": chk["ok"], "detail": chk["notes"], "layer": "rules"})
            for w in chk.get("warnings") or []:
                push({"type": "summary", "title": "Diagram draft — precheck", "body": w})
            if chk["ok"] and staged["scratch_write"].get("ok"):
                sess["proposed_patch"] = patch
                sess["proposed_patch_kind"] = "diagram"
                push(
                    {
                        "type": "diff",
                        "path": patch["path"],
                        "unified": f"Diagram update {patch['path']} ({len(patch['content'])} chars)",
                    }
                )
                sess["status"] = "awaiting_approval"
            else:
                sess["proposed_patch"] = None
                push({"type": "summary", "title": "Diagram draft blocked", "body": chk["notes"]})
                sess["status"] = "awaiting_input"
        else:
            push({"type": "summary", "title": "Diagram draft not parsed", "body": text[:8000]})
            sess["status"] = "awaiting_input"
        store.write_session(workspace_root, project_slug, sess)
        sync_docs_health_timeline(
            workspace_root,
            project_slug,
            sess,
            step=step,
            timeline_slice=(sess.get("events") or [])[ev_base:],
        )
        if ar_id:
            ar_sessions.append_event(
                workspace_root,
                ar_id,
                "docs_health_step",
                {"step": "diagram_draft", "ok": bool(res.get("ok")), "has_patch": bool(patch)},
            )
        append_step_metric()
        return (
            200,
            {"ok": True, "session": _session_response(workspace_root, project_slug, sess), "llm": {"ok": bool(res.get("ok"))}},
        )

    if step == "decision_stub":
        ev_base = len(sess.get("events") or [])
        prior_parts = [
            str(sess.get("enricher_text") or ""),
            str(sess.get("cluster_brief_text") or ""),
        ]
        prior = "\n\n".join(p for p in prior_parts if p.strip()) or "See findings cluster."
        res = run_decision_agent(
            workspace_root,
            project_name=project_slug,
            cluster=cluster if isinstance(cluster, dict) else {},
            findings=findings if isinstance(findings, list) else [],
            prior_summary=prior,
            sess_usage=usage,
            runtime_session_id=ar_id,
            scan_run_id=str(sess.get("run_id") or ""),
            cluster_id=str(sess.get("cluster_id") or ""),
        )
        text = str(res.get("text") or "")
        patch = parse_docs_patch(text)
        push({"type": "token_stats", "snapshot": dict(usage), "last_model": res.get("model")})
        if patch:
            staged = _stage_proposed_patch(workspace_root, project_slug, sess, patch, kind="adr", child=child)
            chk = staged["precheck"]
            push({"type": "verification", "ok": chk["ok"], "detail": chk["notes"], "layer": "rules"})
            for w in chk.get("warnings") or []:
                push({"type": "summary", "title": "ADR stub — precheck", "body": w})
            if chk["ok"] and staged["scratch_write"].get("ok"):
                sess["proposed_patch"] = patch
                sess["proposed_patch_kind"] = "adr"
                push(
                    {
                        "type": "diff",
                        "path": patch["path"],
                        "unified": f"ADR / decision stub {patch['path']} ({len(patch['content'])} chars)",
                    }
                )
                sess["status"] = "awaiting_approval"
            else:
                sess["proposed_patch"] = None
                push({"type": "summary", "title": "ADR draft blocked", "body": chk["notes"]})
                sess["status"] = "awaiting_input"
        else:
            push({"type": "summary", "title": "ADR draft not parsed", "body": text[:8000]})
            sess["status"] = "awaiting_input"
        store.write_session(workspace_root, project_slug, sess)
        sync_docs_health_timeline(
            workspace_root,
            project_slug,
            sess,
            step=step,
            timeline_slice=(sess.get("events") or [])[ev_base:],
        )
        if ar_id:
            ar_sessions.append_event(
                workspace_root,
                ar_id,
                "docs_health_step",
                {"step": "decision_stub", "ok": bool(res.get("ok")), "has_patch": bool(patch)},
            )
        append_step_metric()
        return (
            200,
            {"ok": True, "session": _session_response(workspace_root, project_slug, sess), "llm": {"ok": bool(res.get("ok"))}},
        )

    if step == "draft":
        ev_base = len(sess.get("events") or [])
        prior = str(sess.get("enricher_text") or "See findings cluster.")
        notes = str(sess.get("user_clarification_notes") or "").strip()
        if notes:
            prior = f"{prior}\n\nOperator notes:\n{notes}"
        res = run_writer(
            workspace_root,
            project_name=project_slug,
            cluster=cluster,
            findings=findings,
            prior_summary=prior,
            sess_usage=usage,
            runtime_session_id=ar_id,
            scan_run_id=str(sess.get("run_id") or ""),
            cluster_id=str(sess.get("cluster_id") or ""),
        )
        text = str(res.get("text") or "")
        patch = parse_docs_patch(text)
        push({"type": "token_stats", "snapshot": dict(usage), "last_model": res.get("model")})
        if patch:
            staged = _stage_proposed_patch(
                workspace_root, project_slug, sess, patch, kind="markdown", child=child
            )
            chk = staged["precheck"]
            push({"type": "verification", "ok": chk["ok"], "detail": chk["notes"], "layer": "rules"})
            for w in chk.get("warnings") or []:
                push({"type": "summary", "title": "Writer draft — precheck", "body": w})
            if chk["ok"] and staged["scratch_write"].get("ok"):
                sess["proposed_patch"] = patch
                sess["proposed_patch_kind"] = "markdown"
                push(
                    {
                        "type": "diff",
                        "path": patch["path"],
                        "unified": f"Replace {patch['path']} ({len(patch['content'])} chars)",
                    }
                )
                sess["status"] = "awaiting_approval"
            else:
                sess["proposed_patch"] = None
                push({"type": "summary", "title": "Writer draft blocked", "body": chk["notes"]})
                sess["status"] = "awaiting_input"
        else:
            push({"type": "summary", "title": "Draft not parsed", "body": text[:8000]})
            md_paths: list[str] = []
            for f in findings:
                if not isinstance(f, dict):
                    continue
                for ap in f.get("affected_paths") or []:
                    s = str(ap).strip()
                    if s.lower().endswith(".md"):
                        md_paths.append(s)
            md_paths = sorted(set(md_paths))[:16]
            push(
                {
                    "type": "question",
                    "prompt": (
                        "The model output was not in the expected docs_patch format. "
                        "Send guidance or a target path in a reply, pick an action, or run Draft again after enriching."
                    ),
                    "choices": [
                        {"id": "retry_draft", "label": "Run Draft patch again (after reply)"},
                        {"id": "after_reply", "label": "I will add guidance in a reply"},
                    ],
                    "requires_reply": True,
                }
            )
            if md_paths:
                push({"type": "file_inquiry", "paths": md_paths, "hint": "Markdown paths referenced on findings"})
            sess["status"] = "awaiting_input"
        store.write_session(workspace_root, project_slug, sess)
        sync_docs_health_timeline(
            workspace_root,
            project_slug,
            sess,
            step=step,
            timeline_slice=(sess.get("events") or [])[ev_base:],
        )
        if ar_id:
            ar_sessions.append_event(
                workspace_root,
                ar_id,
                "docs_health_step",
                {"step": "draft", "ok": bool(res.get("ok")), "has_patch": bool(patch)},
            )
        append_step_metric()
        return (
            200,
            {"ok": True, "session": _session_response(workspace_root, project_slug, sess), "llm": {"ok": bool(res.get("ok"))}},
        )

    if step == "review":
        ev_base = len(sess.get("events") or [])
        patch = sess.get("proposed_patch")
        if not isinstance(patch, dict) or not patch.get("path"):
            return 400, {"ok": False, "error": "no_proposed_patch"}
        contract = resolve_project_docs_contract(child, project_slug=project_slug)
        cex = json.dumps(contract, indent=2, default=str)[:8000]
        res = run_reviewer(
            workspace_root,
            proposed=patch,
            sess_usage=usage,
            runtime_session_id=ar_id,
            project_slug=project_slug,
            scan_run_id=str(sess.get("run_id") or ""),
            cluster_id=str(sess.get("cluster_id") or ""),
            contract_excerpt=cex,
        )
        text = str(res.get("text") or "")
        verdict = parse_review_json(text) or {"approve": False, "notes": text[:2000]}
        push(
            {
                "type": "verification",
                "ok": bool(verdict.get("approve")),
                "detail": str(verdict.get("notes") or ""),
                "layer": "model",
            }
        )
        push({"type": "token_stats", "snapshot": dict(usage), "last_model": res.get("model")})
        sess["review_verdict"] = verdict
        store.write_session(workspace_root, project_slug, sess)
        sync_docs_health_timeline(
            workspace_root,
            project_slug,
            sess,
            step=step,
            timeline_slice=(sess.get("events") or [])[ev_base:],
        )
        if ar_id:
            ar_sessions.append_event(
                workspace_root,
                ar_id,
                "docs_health_step",
                {"step": "review", "ok": bool(res.get("ok")), "approve": bool(verdict.get("approve"))},
            )
        append_step_metric()
        return (
            200,
            {"ok": True, "session": _session_response(workspace_root, project_slug, sess), "llm": {"ok": bool(res.get("ok"))}},
        )

    if step == "apply":
        ev_base = len(sess.get("events") or [])
        if not bundle.get("can_write_project") or bundle.get("effective_readonly"):
            return 403, {"ok": False, "error": "write_forbidden"}
        gate = load_apply_gate(workspace_root, project_slug, sid)
        if gate and str(gate.get("status") or "") == "applied":
            return 400, {"ok": False, "error": "patch_already_applied"}
        if gate and str(gate.get("status") or "") != "pending_apply":
            return 400, {"ok": False, "error": "apply_not_ready", "detail": gate.get("status")}
        patch = load_patch_for_apply(workspace_root, project_slug, sid)
        if not isinstance(patch, dict) or not str(patch.get("path") or "").strip():
            legacy = sess.get("proposed_patch")
            if isinstance(legacy, dict) and legacy.get("path"):
                lchk = precheck_docs_patch(child, project_slug=project_slug, patch=legacy)
                if lchk.get("ok"):
                    patch = {
                        "path": str(legacy.get("path") or "").strip(),
                        "content": str(legacy.get("content") if legacy.get("content") is not None else ""),
                    }
        if not isinstance(patch, dict):
            return 400, {"ok": False, "error": "no_apply_artifact"}
        rel = str(patch.get("path") or "").strip()
        content = str(patch.get("content") if patch.get("content") is not None else "")
        if ".." in rel or rel.startswith("/"):
            return 400, {"ok": False, "error": "invalid_path"}
        target = (child / rel).resolve()
        try:
            target.relative_to(child.resolve())
        except ValueError:
            return 400, {"ok": False, "error": "path_escape"}
        if not rel.endswith(".md"):
            return 400, {"ok": False, "error": "not_markdown"}
        chk = precheck_docs_patch(child, project_slug=project_slug, patch={"path": rel, "content": content})
        if not chk["ok"]:
            return 400, {"ok": False, "error": "patch_precheck_failed", "detail": chk["notes"]}
        t0 = time.perf_counter()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        nbytes = len(content.encode("utf-8"))
        push(
            {
                "type": "file_change",
                "path": rel,
                "bytes_written": nbytes,
                "operation": "write",
            }
        )
        raw_line = f"path={rel}\nbytes_written={nbytes}\nencoding=utf-8\n"
        summary = f"Wrote {nbytes} bytes to {rel}."
        push(
            {
                "type": "command",
                "cmd": f"write {rel}",
                "why": "Apply the proposed markdown patch after reviewer approval and project write policy.",
                "status": "ok",
                "duration_ms": elapsed_ms,
                "stdout_summary": summary,
                "raw_output": redact_secrets(raw_line),
            }
        )
        push(
            {
                "type": "command_result",
                "status": "ok",
                "duration_ms": elapsed_ms,
                "summary": summary,
                "detail_raw": redact_secrets(raw_line),
            }
        )
        prev_paths = sess.get("last_applied_paths")
        paths_acc: list[str] = [str(x) for x in prev_paths] if isinstance(prev_paths, list) else []
        if rel not in paths_acc:
            paths_acc.append(rel)
        sess["last_applied_paths"] = paths_acc
        sess["status"] = "running"
        sess["applied_from_artifact"] = True
        mark_apply_consumed(workspace_root, project_slug, sid)
        if isinstance(sess.get("apply_gate"), dict):
            sess["apply_gate"] = {**sess["apply_gate"], "status": "applied"}
        store.write_session(workspace_root, project_slug, sess)
        sync_docs_health_timeline(
            workspace_root,
            project_slug,
            sess,
            step=step,
            timeline_slice=(sess.get("events") or [])[ev_base:],
        )
        append_step_metric()
        return 200, {"ok": True, "session": _session_response(workspace_root, project_slug, sess)}

    if step == "verify":
        ev_base = len(sess.get("events") or [])
        mark_verify_phase_started(workspace_root, sess)
        contract = resolve_project_docs_contract(child, project_slug=project_slug)
        applied = sess.get("last_applied_paths")
        applied_list = [str(x) for x in applied] if isinstance(applied, list) else []
        pipe = run_post_apply_verification(
            child,
            applied_rel_paths=applied_list,
            contract=contract,
        )
        push(
            {
                "type": "verification",
                "ok": bool(pipe.get("ok")),
                "detail": "Post-apply checks (links, markdownlint, optional contract commands) before re-scan.",
                "layer": "pipeline",
                "pipeline": pipe,
            }
        )
        run_payload, _n = persist_quality_scan(
            workspace_root, child, project_slug, follows_session=str(sess.get("id") or "")
        )
        rid = str(run_payload.get("id") or "")
        _sv = (run_payload.get("score") or {}).get("value")
        _base = sess.get("baseline_score")
        _delta = (
            int(_sv) - int(_base)
            if isinstance(_sv, (int, float)) and isinstance(_base, (int, float))
            else None
        )
        push(
            {
                "type": "kpi_update",
                "score": _sv,
                "finding_count": run_payload.get("finding_count"),
                "run_id": rid,
                "score_delta": _delta,
                "baseline_score": _base,
            }
        )
        fd = run_payload.get("finding_diff") if isinstance(run_payload.get("finding_diff"), dict) else {}
        resolved_ids = fd.get("resolved_from_prior_scan") if isinstance(fd.get("resolved_from_prior_scan"), list) else []
        deferred_ids = fd.get("new_since_prior_scan") if isinstance(fd.get("new_since_prior_scan"), list) else []
        reopened = fd.get("reopened_findings") if isinstance(fd.get("reopened_findings"), list) else []
        resolved_n = len(resolved_ids)
        usage2 = sess.setdefault("usage_session", {})
        pt = int(usage2.get("prompt_tokens") or 0) if isinstance(usage2.get("prompt_tokens"), (int, float)) else 0
        ct = int(usage2.get("completion_tokens") or 0) if isinstance(usage2.get("completion_tokens"), (int, float)) else 0
        tokens = int(usage2.get("total_tokens") or 0) if isinstance(usage2.get("total_tokens"), (int, float)) else 0
        if tokens == 0 and (pt or ct):
            tokens = pt + ct
        elapsed = _elapsed_seconds(str(sess.get("started_at") or ""))
        last_model: str | None = None
        for ev in reversed(sess.get("events") or []):
            if isinstance(ev, dict) and ev.get("type") == "token_stats" and ev.get("last_model"):
                last_model = str(ev.get("last_model"))
                break
        sup_fids = user_suppressed_finding_ids(workspace_root, project_slug)
        sup_cids = suppressed_cluster_ids(workspace_root, project_slug)
        findings_after = run_payload.get("findings") if isinstance(run_payload.get("findings"), list) else []
        clusters_after = run_payload.get("clusters") if isinstance(run_payload.get("clusters"), list) else []
        overlaid = overlay_finding_suppressions(
            findings_after,
            suppressed_finding_ids=sup_fids,
            suppressed_cluster_ids=sup_cids,
            clusters=clusters_after,
        )
        work_all = store.load_work_items(workspace_root, project_slug)
        open_work_n = sum(1 for w in work_all if str(w.get("status", "open")).lower() != "done")
        closure = compute_closure_status(overlaid, work_items_open=open_work_n)
        sess["closure_status"] = closure
        score_delta_num = int(_delta) if isinstance(_delta, int) else None
        sess["efficiency_metrics"] = {
            "total_tokens": tokens,
            "elapsed_seconds_total": elapsed,
            "score_delta": score_delta_num,
            "resolved_findings_count": resolved_n,
            "tokens_per_resolved_finding": (tokens / resolved_n) if resolved_n else None,
            "tokens_per_score_point": (tokens / score_delta_num)
            if tokens and score_delta_num not in (None, 0)
            else None,
            "seconds_per_resolved_finding": (elapsed / resolved_n) if elapsed is not None and resolved_n else None,
            "last_model": last_model,
        }
        enc_proj = urllib.parse.quote(project_slug, safe="")
        sess["completion_summary"] = {
            "finished_at": store.now_iso(),
            "verification_pipeline_ok": bool(pipe.get("ok")),
            "verification_pipeline": pipe,
            "verification_run_id": rid,
            "baseline_score": _base,
            "score_after": _sv,
            "score_delta": _delta,
            "finding_diff": fd,
            "findings_resolved_ids": resolved_ids,
            "findings_new_or_reopened": {"new": deferred_ids, "reopened": reopened},
            "closure_status": closure,
            "artifact_links": {
                "docs_health_project": f"/projects/{enc_proj}/docs-health",
                "verification_run": f"/projects/{enc_proj}/docs-health#run-{rid}",
            },
        }
        push(
            {
                "type": "summary",
                "title": "Run complete",
                "body": (
                    f"Verification pipeline: {'passed' if pipe.get('ok') else 'reported issues'}. "
                    f"Score after re-scan: {_sv} (delta {_delta if _delta is not None else 'n/a'}). "
                    f"Resolved {resolved_n} finding(s) vs prior scan. "
                    f"Scope closure: {'complete' if closure.get('complete') else 'incomplete'} — {closure.get('notes', '')}"
                )[:8000],
            }
        )
        sess["status"] = "completed"
        sess["verification_run_id"] = rid
        store.write_session(workspace_root, project_slug, sess)
        sync_docs_health_timeline(
            workspace_root,
            project_slug,
            sess,
            step=step,
            timeline_slice=(sess.get("events") or [])[ev_base:],
        )
        if ar_id:
            ar_sessions.append_event(
                workspace_root,
                ar_id,
                "docs_health_step",
                {
                    "step": "verify",
                    "ok": bool(pipe.get("ok")),
                    "run_id": rid,
                    "score_delta": _delta,
                },
            )
        append_step_metric()
        return (
            200,
            {
                "ok": True,
                "session": _session_response(workspace_root, project_slug, sess),
                "verification_run": run_payload,
            },
        )

    return 400, {"ok": False, "error": "unknown_step"}
