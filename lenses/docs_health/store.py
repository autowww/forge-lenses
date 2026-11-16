"""Persistence for Docs Health under ``<workspace>/.lenses-local/docs-health/<project>/``."""

from __future__ import annotations

import json
import os
import urllib.parse
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def project_store_dir(workspace_root: Path, project_slug: str) -> Path:
    safe = project_slug.strip().replace(os.sep, "_").replace("/", "_")
    if not safe or ".." in safe:
        raise ValueError("invalid_project_slug")
    return workspace_root.resolve() / ".lenses-local" / "docs-health" / safe


def ensure_store_dir(workspace_root: Path, project_slug: str) -> Path:
    d = project_store_dir(workspace_root, project_slug)
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d.parent.parent, 0o700)
        os.chmod(d.parent, 0o700)
        os.chmod(d, 0o700)
    except OSError:
        pass
    return d


def runs_dir(workspace_root: Path, project_slug: str) -> Path:
    d = ensure_store_dir(workspace_root, project_slug) / "runs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def sessions_dir(workspace_root: Path, project_slug: str) -> Path:
    d = ensure_store_dir(workspace_root, project_slug) / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def session_cancel_flag_path(workspace_root: Path, project_slug: str, session_id: str) -> Path:
    """Marker file: set when operator requests cancel (worker may poll; stop also SIGKILLs)."""
    sid = str(session_id or "").strip().replace(os.sep, "_").replace("/", "_")
    if not sid or ".." in sid:
        raise ValueError("invalid_session_id")
    return sessions_dir(workspace_root, project_slug) / f"{sid}.cancel_requested"


def write_session_cancel_flag(workspace_root: Path, project_slug: str, session_id: str) -> Path:
    p = session_cancel_flag_path(workspace_root, project_slug, session_id)
    p.write_text(now_iso(), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    return p


def clear_session_cancel_flag(workspace_root: Path, project_slug: str, session_id: str) -> None:
    p = session_cancel_flag_path(workspace_root, project_slug, session_id)
    try:
        p.unlink(missing_ok=True)
    except OSError:
        pass


def is_session_cancel_requested(workspace_root: Path, project_slug: str, session_id: str) -> bool:
    return session_cancel_flag_path(workspace_root, project_slug, session_id).is_file()


def work_items_path(workspace_root: Path, project_slug: str) -> Path:
    return ensure_store_dir(workspace_root, project_slug) / "work_items.json"


def finding_lifecycle_path(workspace_root: Path, project_slug: str) -> Path:
    return ensure_store_dir(workspace_root, project_slug) / "finding_lifecycle.json"


def cluster_suppressions_path(workspace_root: Path, project_slug: str) -> Path:
    return ensure_store_dir(workspace_root, project_slug) / "cluster_suppressions.json"


def list_cluster_suppressions(workspace_root: Path, project_slug: str) -> list[dict[str, Any]]:
    p = cluster_suppressions_path(workspace_root, project_slug)
    if not p.is_file():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    return []


def add_cluster_suppression(
    workspace_root: Path,
    project_slug: str,
    *,
    cluster_id: str,
    reason: str,
    run_id: str | None = None,
) -> list[dict[str, Any]]:
    cur = list_cluster_suppressions(workspace_root, project_slug)
    cid = str(cluster_id or "").strip()
    if not cid:
        raise ValueError("cluster_id_required")
    row = {
        "cluster_id": cid,
        "reason": (reason or "").strip()[:4000],
        "run_id": (run_id or "").strip() or None,
        "suppressed_at": now_iso(),
    }
    cur = [x for x in cur if str((x or {}).get("cluster_id") or "") != cid]
    cur.append(row)
    p = cluster_suppressions_path(workspace_root, project_slug)
    p.write_text(json.dumps(cur, indent=2, sort_keys=True), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    return cur


def finding_suppressions_path(workspace_root: Path, project_slug: str) -> Path:
    return ensure_store_dir(workspace_root, project_slug) / "finding_suppressions.json"


def list_finding_suppressions(workspace_root: Path, project_slug: str) -> list[dict[str, Any]]:
    p = finding_suppressions_path(workspace_root, project_slug)
    if not p.is_file():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    return []


def add_finding_suppression(
    workspace_root: Path,
    project_slug: str,
    *,
    finding_id: str,
    reason: str,
    mode: str = "suppress",
    review_at: str | None = None,
    run_id: str | None = None,
) -> list[dict[str, Any]]:
    fid = str(finding_id or "").strip()
    if not fid:
        raise ValueError("finding_id_required")
    cur = list_finding_suppressions(workspace_root, project_slug)
    row = {
        "finding_id": fid,
        "reason": (reason or "").strip()[:4000],
        "mode": (mode or "suppress").strip()[:32],
        "review_at": (review_at or "").strip() or None,
        "run_id": (run_id or "").strip() or None,
        "suppressed_at": now_iso(),
    }
    cur = [x for x in cur if str((x or {}).get("finding_id") or "") != fid]
    cur.append(row)
    p = finding_suppressions_path(workspace_root, project_slug)
    p.write_text(json.dumps(cur, indent=2, sort_keys=True), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    return cur


def load_finding_lifecycle(workspace_root: Path, project_slug: str) -> dict[str, Any]:
    p = finding_lifecycle_path(workspace_root, project_slug)
    if not p.is_file():
        return {"previously_resolved": []}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"previously_resolved": []}
    if not isinstance(raw, dict):
        return {"previously_resolved": []}
    pr = raw.get("previously_resolved")
    if isinstance(pr, list):
        return {"previously_resolved": [str(x) for x in pr if str(x).strip()]}
    return {"previously_resolved": []}


def save_finding_lifecycle(workspace_root: Path, project_slug: str, data: dict[str, Any]) -> None:
    p = finding_lifecycle_path(workspace_root, project_slug)
    p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def update_finding_lifecycle(
    workspace_root: Path,
    project_slug: str,
    *,
    prior_ids: set[str],
    current_ids: set[str],
) -> dict[str, Any]:
    """Track resolved/reopened between scans. Returns diff hints for the run payload."""
    st = load_finding_lifecycle(workspace_root, project_slug)
    prev_resolved: set[str] = set(st.get("previously_resolved") or [])
    resolved_now = prior_ids - current_ids
    new_ids = current_ids - prior_ids
    reopened_ids = sorted(new_ids & prev_resolved)
    prev_resolved |= resolved_now
    prev_resolved -= current_ids
    st["previously_resolved"] = sorted(prev_resolved)
    save_finding_lifecycle(workspace_root, project_slug, st)
    return {
        "resolved_from_prior_scan": sorted(prior_ids - current_ids),
        "new_since_prior_scan": sorted(current_ids - prior_ids),
        "reopened_findings": reopened_ids,
    }


def inventories_dir(workspace_root: Path, project_slug: str) -> Path:
    return ensure_store_dir(workspace_root, project_slug) / "inventories"


def latest_inventory_pointer_path(workspace_root: Path, project_slug: str) -> Path:
    return ensure_store_dir(workspace_root, project_slug) / "latest_inventory.json"


def write_inventory_snapshot(workspace_root: Path, project_slug: str, snapshot: dict[str, Any]) -> None:
    iid = str(snapshot.get("id") or "").strip()
    if not iid:
        raise ValueError("inventory_id_required")
    d = inventories_dir(workspace_root, project_slug)
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{iid}.json"
    p.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    ptr = latest_inventory_pointer_path(workspace_root, project_slug)
    ptr.write_text(
        json.dumps({"id": iid, "updated_at": snapshot.get("created_at") or now_iso()}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    try:
        os.chmod(ptr, 0o600)
    except OSError:
        pass


def load_latest_inventory_summary(workspace_root: Path, project_slug: str) -> dict[str, Any] | None:
    ptr = latest_inventory_pointer_path(workspace_root, project_slug)
    if not ptr.is_file():
        return None
    try:
        meta = json.loads(ptr.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    iid = str(meta.get("id") or "").strip()
    if not iid:
        return None
    fullp = inventories_dir(workspace_root, project_slug) / f"{iid}.json"
    if not fullp.is_file():
        return {"id": iid, "updated_at": meta.get("updated_at"), "document_count": None, "partial": True}
    try:
        data = json.loads(fullp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return {
        "id": iid,
        "updated_at": data.get("created_at") or meta.get("updated_at"),
        "document_count": data.get("document_count"),
        "by_doc_type": data.get("by_doc_type") or {},
        "by_knowledge_category": data.get("by_knowledge_category") or {},
        "link_edge_count": len(data.get("link_graph") or []) if isinstance(data.get("link_graph"), list) else 0,
    }


def load_latest_inventory_full(
    workspace_root: Path,
    project_slug: str,
    *,
    max_documents: int | None = None,
) -> dict[str, Any] | None:
    ptr = latest_inventory_pointer_path(workspace_root, project_slug)
    if not ptr.is_file():
        return None
    try:
        meta = json.loads(ptr.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    iid = str(meta.get("id") or "").strip()
    if not iid:
        return None
    fullp = inventories_dir(workspace_root, project_slug) / f"{iid}.json"
    if not fullp.is_file():
        return None
    try:
        data = json.loads(fullp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if max_documents is not None and isinstance(data.get("documents"), list):
        docs = data["documents"]
        data = dict(data)
        data["documents"] = docs[: max(0, max_documents)]
        data["documents_truncated"] = len(docs) > max_documents
    return data


def write_run(workspace_root: Path, project_slug: str, run: dict[str, Any]) -> None:
    rid = str(run.get("id") or "").strip() or uuid.uuid4().hex
    run["id"] = rid
    p = runs_dir(workspace_root, project_slug) / f"{rid}.json"
    p.write_text(json.dumps(run, indent=2, sort_keys=True), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def load_run(workspace_root: Path, project_slug: str, run_id: str) -> dict[str, Any] | None:
    p = runs_dir(workspace_root, project_slug) / f"{run_id}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def list_run_summaries(workspace_root: Path, project_slug: str, *, limit: int = 30) -> list[dict[str, Any]]:
    d = runs_dir(workspace_root, project_slug)
    if not d.is_dir():
        return []
    rows: list[tuple[float, dict[str, Any]]] = []
    for p in d.glob("*.json"):
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            mtime = p.stat().st_mtime
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        score_obj = raw.get("score") if isinstance(raw.get("score"), dict) else {}
        crit = 0
        for f in raw.get("findings") or []:
            if not isinstance(f, dict):
                continue
            if str(f.get("severity") or "").lower() == "critical":
                crit += 1
        rows.append(
            (
                mtime,
                {
                    "id": raw.get("id"),
                    "started_at": raw.get("started_at"),
                    "finished_at": raw.get("finished_at"),
                    "finding_count": raw.get("finding_count"),
                    "score": score_obj.get("value"),
                    "critical_open_count": crit,
                },
            )
        )
    rows.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in rows[:limit]]


def load_latest_run_id(workspace_root: Path, project_slug: str) -> str | None:
    sums = list_run_summaries(workspace_root, project_slug, limit=1)
    if not sums:
        return None
    rid = sums[0].get("id")
    return str(rid).strip() if rid else None


def load_work_items(workspace_root: Path, project_slug: str) -> list[dict[str, Any]]:
    p = work_items_path(workspace_root, project_slug)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []


def save_work_items(workspace_root: Path, project_slug: str, items: list[dict[str, Any]]) -> None:
    p = work_items_path(workspace_root, project_slug)
    p.write_text(json.dumps(items, indent=2, sort_keys=True), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def upsert_docs_debt_work_items(
    workspace_root: Path,
    project_slug: str,
    items: list[dict[str, Any]],
) -> int:
    """Merge by stable id; refresh metadata for open items."""
    cur = load_work_items(workspace_root, project_slug)
    by_id = {str(x.get("id")): x for x in cur if x.get("id")}
    n = 0
    for it in items:
        iid = str(it.get("id") or "").strip()
        if not iid:
            continue
        if iid in by_id:
            existing = by_id[iid]
            if str(existing.get("status", "open")).lower() == "done":
                continue
            existing.update({k: v for k, v in it.items() if k != "id"})
            existing["updated_at"] = now_iso()
        else:
            by_id[iid] = dict(it)
            n += 1
    save_work_items(workspace_root, project_slug, list(by_id.values()))
    return n


def append_work_items(workspace_root: Path, project_slug: str, new_items: list[dict[str, Any]]) -> None:
    cur = load_work_items(workspace_root, project_slug)
    seen = {str(x.get("id")) for x in cur if x.get("id")}
    for it in new_items:
        iid = str(it.get("id") or "").strip()
        if iid and iid not in seen:
            cur.append(it)
            seen.add(iid)
    save_work_items(workspace_root, project_slug, cur)


def update_work_item(
    workspace_root: Path,
    project_slug: str,
    item_id: str,
    *,
    status: str | None = None,
) -> dict[str, Any] | None:
    cur = load_work_items(workspace_root, project_slug)
    out = None
    for it in cur:
        if str(it.get("id")) == item_id:
            if status:
                it["status"] = status
            it["updated_at"] = now_iso()
            out = dict(it)
            break
    if out:
        save_work_items(workspace_root, project_slug, cur)
    return out


def write_session(workspace_root: Path, project_slug: str, session: dict[str, Any]) -> None:
    sid = str(session.get("id") or "").strip()
    if not sid:
        raise ValueError("session_id_required")
    p = sessions_dir(workspace_root, project_slug) / f"{sid}.json"
    session["updated_at"] = now_iso()
    p.write_text(json.dumps(session, indent=2, sort_keys=True), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def load_session(workspace_root: Path, project_slug: str, session_id: str) -> dict[str, Any] | None:
    p = sessions_dir(workspace_root, project_slug) / f"{session_id}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def list_recent_docs_health_sessions(
    workspace_root: Path,
    project_slug: str,
    *,
    limit: int = 15,
) -> list[dict[str, Any]]:
    """Recent remediation sessions (any status) for project dashboards and history."""
    sd = sessions_dir(workspace_root, project_slug)
    if not sd.is_dir():
        return []
    rows: list[tuple[float, dict[str, Any]]] = []
    for sp in sd.glob("*.json"):
        try:
            sess = json.loads(sp.read_text(encoding="utf-8"))
            mtime = sp.stat().st_mtime
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(sess, dict):
            continue
        sid = str(sess.get("id") or sp.stem).strip()
        if not sid:
            continue
        usage = sess.get("usage_session") if isinstance(sess.get("usage_session"), dict) else {}
        tt = int(usage.get("total_tokens") or 0) if isinstance(usage.get("total_tokens"), (int, float)) else 0
        pt = int(usage.get("prompt_tokens") or 0) if isinstance(usage.get("prompt_tokens"), (int, float)) else 0
        ct = int(usage.get("completion_tokens") or 0) if isinstance(usage.get("completion_tokens"), (int, float)) else 0
        if tt == 0 and (pt or ct):
            tt = pt + ct
        last_model: str | None = None
        for ev in reversed(sess.get("events") or []):
            if isinstance(ev, dict) and ev.get("type") == "token_stats" and ev.get("last_model"):
                last_model = str(ev.get("last_model"))
                break
        cs = sess.get("closure_status") if isinstance(sess.get("closure_status"), dict) else {}
        comp = sess.get("completion_summary") if isinstance(sess.get("completion_summary"), dict) else None
        eff = sess.get("efficiency_metrics") if isinstance(sess.get("efficiency_metrics"), dict) else None
        cluster = sess.get("cluster") if isinstance(sess.get("cluster"), dict) else {}
        rows.append(
            (
                mtime,
                {
                    "session_id": sid,
                    "status": str(sess.get("status") or ""),
                    "display_name": str(sess.get("display_name") or "").strip() or None,
                    "started_at": sess.get("started_at"),
                    "updated_at": sess.get("updated_at"),
                    "run_id": sess.get("run_id"),
                    "cluster_id": sess.get("cluster_id"),
                    "cluster_label": str(cluster.get("label") or cluster.get("id") or "").strip() or None,
                    "verification_run_id": sess.get("verification_run_id"),
                    "total_tokens": tt,
                    "last_model": last_model,
                    "closure_complete": cs.get("complete"),
                    "verification_pipeline_ok": comp.get("verification_pipeline_ok") if comp else None,
                    "score_delta": (eff or {}).get("score_delta") if eff else comp.get("score_delta") if comp else None,
                    "href_session": f"/projects/{urllib.parse.quote(project_slug, safe='')}/docs-health/session/{urllib.parse.quote(sid, safe='')}",
                },
            )
        )
    rows.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in rows[: max(1, limit)]]


_TASKLET_FOLLOWUP_STATES = frozenset(
    {
        "awaiting_input",
        "awaiting_approval",
        "stopped",
        "failed",
        "paused",
    }
)


def _title_for_tasklet_followup(state: str, stop_reason: Any) -> str:
    s = str(state or "").lower()
    if s == "awaiting_input":
        return "Docs remediation — waiting for your input"
    if s == "awaiting_approval":
        return "Docs remediation — waiting for approval"
    if s == "stopped":
        sr = str(stop_reason or "").lower()
        if sr == "cancelled":
            return "Docs remediation — stopped (cancelled); resume or review"
        return "Docs remediation — stopped; resume available"
    if s == "failed":
        return "Docs remediation — failed; needs follow-up"
    if s == "paused":
        return "Docs remediation — paused"
    return f"Docs remediation — {state}"


def tasklet_followup_work_items(
    workspace_root: Path,
    registry: dict[str, Any],
    *,
    limit: int = 48,
) -> list[dict[str, Any]]:
    """
    Virtual work rows for Docs Health TaskletRuns that need operator action (not persisted in work_items.json).

    Uses the generic tasklet runtime as the source of truth for lifecycle.
    """
    from lenses.tasklet.catalog import list_tasklet_runs

    ignore = set(registry.get("ignore_paths") or [])
    out: list[dict[str, Any]] = []
    for tr in list_tasklet_runs(workspace_root, limit=400):
        if str(tr.get("tasklet_id") or "") != "docs_health_remediation":
            continue
        st = str(tr.get("state") or "").strip().lower()
        if st not in _TASKLET_FOLLOWUP_STATES:
            continue
        proj = str(tr.get("project_slug") or "").strip()
        if not proj or proj in ignore:
            continue
        trid = str(tr.get("id") or "").strip()
        sid = str(tr.get("docs_health_session_id") or "").strip()
        if not trid or not sid:
            continue
        enc_p = urllib.parse.quote(proj, safe="")
        enc_s = urllib.parse.quote(sid, safe="")
        ts = tr.get("updated_at") or tr.get("created_at")
        out.append(
            {
                "id": f"tasklet-followup-{trid}",
                "kind": "tasklet_run",
                "source": "tasklet_runtime",
                "status": "open",
                "title": _title_for_tasklet_followup(st, tr.get("stop_reason")),
                "tasklet_run_id": trid,
                "tasklet_run_state": st,
                "tasklet_id": str(tr.get("tasklet_id") or ""),
                "stop_reason": tr.get("stop_reason"),
                "last_error": (str(tr.get("last_error") or "")[:500] or None),
                "docs_health_session_id": sid,
                "project": proj,
                "project_docs_health_href": f"/projects/{enc_p}/docs-health",
                "docs_health_session_href": f"/projects/{enc_p}/docs-health/session/{enc_s}",
                "created_at": tr.get("created_at"),
                "updated_at": ts,
            }
        )
        if len(out) >= max(1, limit):
            break
    return out


def count_tasklet_followups_by_project(
    workspace_root: Path,
    registry: dict[str, Any],
) -> dict[str, int]:
    m: dict[str, int] = {}
    for it in tasklet_followup_work_items(workspace_root, registry, limit=400):
        p = str(it.get("project") or "").strip()
        if p:
            m[p] = m.get(p, 0) + 1
    return m


_LIVE_SESSION_STATUSES = frozenset({"running", "awaiting_approval", "awaiting_input"})


def list_live_docs_health_sessions(
    workspace_root: Path,
    registry: dict[str, Any],
    *,
    limit: int = 24,
) -> list[dict[str, Any]]:
    """Sessions across git children that are still in an interactive state."""
    root = workspace_root.resolve()
    ignore = set(registry.get("ignore_paths") or [])
    rows: list[tuple[float, dict[str, Any]]] = []
    if not root.is_dir():
        return []
    for p in sorted(root.iterdir(), key=lambda x: x.name.lower()):
        if not p.is_dir() or p.name.startswith(".") or p.name in ignore:
            continue
        if not (p / ".git").is_dir():
            continue
        proj = p.name
        sd = sessions_dir(workspace_root, proj)
        if not sd.is_dir():
            continue
        for sp in sd.glob("*.json"):
            try:
                sess = json.loads(sp.read_text(encoding="utf-8"))
                mtime = sp.stat().st_mtime
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(sess, dict):
                continue
            st = str(sess.get("status") or "").lower()
            if st not in _LIVE_SESSION_STATUSES:
                continue
            sid = str(sess.get("id") or sp.stem).strip()
            if not sid:
                continue
            usage = sess.get("usage_session") if isinstance(sess.get("usage_session"), dict) else {}
            tt = int(usage.get("total_tokens") or 0) if isinstance(usage.get("total_tokens"), (int, float)) else 0
            pt = int(usage.get("prompt_tokens") or 0) if isinstance(usage.get("prompt_tokens"), (int, float)) else 0
            ct = int(usage.get("completion_tokens") or 0) if isinstance(usage.get("completion_tokens"), (int, float)) else 0
            if tt == 0 and (pt or ct):
                tt = pt + ct
            last_model: str | None = None
            for ev in reversed(sess.get("events") or []):
                if isinstance(ev, dict) and ev.get("type") == "token_stats" and ev.get("last_model"):
                    last_model = str(ev.get("last_model"))
                    break
            cluster = sess.get("cluster") if isinstance(sess.get("cluster"), dict) else {}
            label = str(cluster.get("label") or cluster.get("id") or "").strip() or None
            row: dict[str, Any] = {
                "project": proj,
                "session_id": sid,
                "status": st,
                "started_at": sess.get("started_at"),
                "updated_at": sess.get("updated_at"),
                "total_tokens": tt,
                "prompt_tokens": pt,
                "completion_tokens": ct,
                "last_model": last_model,
                "cluster_label": label,
            }
            trid = str(sess.get("tasklet_run_id") or "").strip()
            if trid:
                from lenses.tasklet import store as tr_store

                tr = tr_store.load_tasklet_run(workspace_root, trid)
                if tr:
                    row["tasklet_run_id"] = trid
                    row["tasklet_state"] = str(tr.get("state") or "")
                    if tr.get("stop_reason") is not None:
                        row["tasklet_stop_reason"] = tr.get("stop_reason")
            rows.append((mtime, row))
    rows.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in rows[: max(1, limit)]]


def workspace_summary(workspace_root: Path, registry: dict[str, Any]) -> dict[str, Any]:
    """Aggregate latest scores for git children (best-effort)."""
    root = workspace_root.resolve()
    ignore = set(registry.get("ignore_paths") or [])
    projects: list[dict[str, Any]] = []
    active_sessions = 0
    scores_for_avg: list[int] = []
    if root.is_dir():
        for p in sorted(root.iterdir(), key=lambda x: x.name.lower()):
            if not p.is_dir() or p.name.startswith(".") or p.name in ignore:
                continue
            if not (p / ".git").is_dir():
                continue
            sums = list_run_summaries(workspace_root, p.name, limit=2)
            score = sums[0].get("score") if sums else None
            fc = sums[0].get("finding_count") if sums else None
            crit = sums[0].get("critical_open_count") if sums else None
            last_score_delta: int | None = None
            if len(sums) >= 2:
                a = sums[0].get("score")
                b = sums[1].get("score")
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    last_score_delta = int(a) - int(b)
            if isinstance(score, int):
                scores_for_avg.append(score)
            has_fc = (p / "forge" / "docs-contract.yaml").is_file()
            inv_s = load_latest_inventory_summary(workspace_root, p.name)
            open_work = sum(
                1
                for it in load_work_items(workspace_root, p.name)
                if str(it.get("status", "open")).lower() != "done"
            )
            projects.append(
                {
                    "project": p.name,
                    "last_score": score,
                    "last_score_delta": last_score_delta,
                    "last_finding_count": fc,
                    "critical_open_findings": crit if isinstance(crit, int) else None,
                    "open_docs_work_items": open_work,
                    "needs_attention": (isinstance(fc, int) and fc > 0) or (isinstance(score, int) and score < 80),
                    "has_docs_contract_file": has_fc,
                    "markdown_document_count": inv_s.get("document_count") if inv_s else None,
                    "last_docs_inventory_at": inv_s.get("updated_at") if inv_s else None,
                }
            )
            sd = sessions_dir(workspace_root, p.name)
            if sd.is_dir():
                for sp in sd.glob("*.json"):
                    try:
                        sess = json.loads(sp.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        continue
                    st = str(sess.get("status", "")).lower()
                    if st in ("running", "live", "awaiting_approval", "awaiting_input"):
                        active_sessions += 1
    tf_map = count_tasklet_followups_by_project(workspace_root, registry)
    for row in projects:
        row["open_tasklet_followups"] = int(tf_map.get(str(row.get("project")), 0))
    with_contract = sum(1 for row in projects if row.get("has_docs_contract_file"))
    indexed = sum(1 for row in projects if row.get("markdown_document_count") is not None)
    avg_score = round(sum(scores_for_avg) / len(scores_for_avg)) if scores_for_avg else None
    critical_projects = sum(
        1 for row in projects if isinstance(row.get("critical_open_findings"), int) and row["critical_open_findings"] > 0
    )
    awaiting = sum(int(row.get("open_docs_work_items") or 0) for row in projects)
    tasklet_follow_total = sum(tf_map.values())
    live_rows = list_live_docs_health_sessions(workspace_root, registry, limit=64)
    tokens_in_flight = sum(int(r.get("total_tokens") or 0) for r in live_rows if isinstance(r.get("total_tokens"), (int, float)))
    improving = sum(
        1
        for row in projects
        if isinstance(row.get("last_score_delta"), int) and int(row["last_score_delta"]) > 0
    )
    from lenses.tasklet.registry import list_builtin_tasklet_definitions

    return {
        "ok": True,
        "projects": projects,
        "active_sessions_estimate": active_sessions,
        "live_docs_health_sessions": live_rows[:12],
        "projects_with_contract_file": with_contract,
        "projects_with_inventory": indexed,
        "builtin_tasklets": list_builtin_tasklet_definitions(),
        "rollup": {
            "average_last_score": avg_score,
            "projects_with_critical_open_findings": critical_projects,
            "open_docs_work_items_total": awaiting,
            "open_tasklet_followups_total": tasklet_follow_total,
            "estimated_llm_tokens_in_flight": tokens_in_flight,
            "projects_with_recent_score_gain": improving,
        },
    }


def all_open_work_items(workspace_root: Path, registry: dict[str, Any], *, limit: int = 80) -> list[dict[str, Any]]:
    """Flatten open Docs Health work items across git children, plus virtual tasklet follow-up rows."""
    root = workspace_root.resolve()
    ignore = set(registry.get("ignore_paths") or [])
    tf_cap = min(36, max(8, limit // 2))
    tf_rows = tasklet_followup_work_items(workspace_root, registry, limit=tf_cap)
    out: list[dict[str, Any]] = list(tf_rows)
    if not root.is_dir():
        return out
    for p in sorted(root.iterdir(), key=lambda x: x.name.lower()):
        if not p.is_dir() or p.name.startswith(".") or p.name in ignore:
            continue
        if not (p / ".git").is_dir():
            continue
        for it in load_work_items(workspace_root, p.name):
            if str(it.get("status", "open")).lower() == "done":
                continue
            row = dict(it)
            row["project"] = p.name
            out.append(row)
            if len(out) >= limit:
                return out
    return out
