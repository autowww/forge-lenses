"""Join WBS IDs with Charge, Ember Log, and Versona sessions (deterministic, read-only)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

import yaml

from lenses.roadmap_outline import (
    extract_chart_metrics,
    extract_date_shift_model,
    extract_gantt_model,
    iter_gfm_tables,
)
from lenses.safe_forge_paths import workspace_md_view_link
from lenses.story_definition_synthesis import build_story_view_dict
from lenses.wbs_model import WBS_ID_RE, WbsModel, WbsStory, parse_wbs_markdown


def _norm_header(h: str) -> str:
    return re.sub(r"\s+", " ", h.strip().lower())


def _repo_base(workspace_root: Path, repo_hint: str) -> Path:
    if not repo_hint:
        return workspace_root.resolve()
    return (workspace_root / repo_hint).resolve()


def _story_hub_code_execution(wr: Path, repo_hint: str, story_id: str) -> dict[str, Any]:
    """Graph + fixture-backed branch/PR/MR context for Studio story hub (Sprint 3)."""
    out: dict[str, Any] = {}
    sid = (story_id or "").strip()
    if not sid:
        return out

    from lenses.orchestration_graph.cicd_trace import story_cicd_trace_from_graph
    from lenses.orchestration_graph.code_links import story_code_links_from_graph
    from lenses.orchestration_graph.db import connect as ogs_connect
    from lenses.orchestration_graph.feature_flag import experimental_orchestration_graph_enabled
    from lenses.orchestration_graph.quality_trace import story_quality_trace_from_graph
    from lenses.orchestration_graph.security_trace import story_security_trace_from_graph
    from lenses.orchestration_graph.ops_trace import story_ops_trace_from_graph

    if experimental_orchestration_graph_enabled():
        conn = ogs_connect(wr)
        if conn is not None:
            try:
                g = story_code_links_from_graph(conn, sid)
                if g.get("ok"):
                    out["graph"] = g
                ctrace = story_cicd_trace_from_graph(conn, sid)
                if ctrace.get("ok"):
                    out["cicd_trace"] = ctrace
                qtrace = story_quality_trace_from_graph(conn, sid)
                if qtrace.get("ok"):
                    out["quality_trace"] = qtrace
                strace = story_security_trace_from_graph(conn, sid)
                if strace.get("ok"):
                    out["security_trace"] = strace
                otrace = story_ops_trace_from_graph(conn, sid)
                if otrace.get("ok"):
                    out["ops_trace"] = otrace
            finally:
                conn.close()

    from lenses.test_quality.feature_flag import experimental_test_quality_enabled
    from lenses.test_quality.story_evidence import load_doc_for_workspace, story_quality_evidence_from_doc

    if experimental_test_quality_enabled():
        lenses_root = Path(__file__).resolve().parent
        qdoc = load_doc_for_workspace(wr, lenses_root)
        if qdoc is not None:
            out["quality_evidence"] = story_quality_evidence_from_doc(qdoc, sid)

    from lenses.devsecops_compliance.feature_flag import experimental_devsecops_compliance_enabled
    from lenses.devsecops_compliance.story_evidence import load_doc_for_workspace as load_sec_doc
    from lenses.devsecops_compliance.story_evidence import story_devsecops_evidence_from_doc

    if experimental_devsecops_compliance_enabled():
        lenses_root = Path(__file__).resolve().parent
        sdoc = load_sec_doc(wr, lenses_root)
        if sdoc is not None:
            out["devsecops_evidence"] = story_devsecops_evidence_from_doc(sdoc, sid)

    from lenses.ops_delivery.feature_flag import experimental_ops_delivery_enabled
    from lenses.ops_delivery.story_evidence import load_doc_for_workspace as load_ops_doc
    from lenses.ops_delivery.story_evidence import story_ops_delivery_evidence_from_doc

    if experimental_ops_delivery_enabled():
        lenses_root = Path(__file__).resolve().parent
        odoc = load_ops_doc(wr, lenses_root)
        if odoc is not None:
            out["ops_delivery_evidence"] = story_ops_delivery_evidence_from_doc(odoc, sid)

    from lenses.repo_workflow.aggregate import get_repo_workflow_row_for_project
    from lenses.repo_workflow.feature_flag import experimental_repo_workflow_enabled

    rh = (repo_hint or "").strip()
    if experimental_repo_workflow_enabled() and rh:
        row = get_repo_workflow_row_for_project(wr, rh)
        if row:
            wf = row.get("workflow") or {}
            prs = wf.get("pull_requests") if isinstance(wf.get("pull_requests"), list) else []
            open_prs = [
                p for p in prs if isinstance(p, dict) and str(p.get("state") or "").lower() == "open"
            ]
            link = None
            for x in row.get("work_item_links") or []:
                if isinstance(x, dict) and str(x.get("story_id") or "") == sid:
                    link = x
                    break
            stale_n = sum(
                1
                for p in open_prs
                if isinstance(p.get("stale_days"), (int, float)) and float(p["stale_days"]) >= 7
            )
            blocked_n = sum(
                1
                for p in open_prs
                if str(p.get("mergeable") or "").lower() in ("conflicting", "false")
                or (str(p.get("merge_blocked_reason") or "").strip() != "")
            )
            out["repo"] = {
                "provider": row.get("provider"),
                "health": row.get("health"),
                "work_item_link": link,
                "open_pull_requests_preview": open_prs[:8],
                "open_pr_stats": {
                    "stale_count": stale_n,
                    "blocked_merge_count": blocked_n,
                },
                "repository": wf.get("repository") or {},
                "code_owners": wf.get("code_owners") or {},
                "branch_protection": wf.get("branch_protection") or [],
                "project_href": f"/projects/{quote(rh, safe='')}",
            }
    return out


def parse_charge_sparks(charge_md: str) -> list[dict[str, Any]]:
    """Rows from the Active Sparks table: spark_id, phase, intent, status."""
    out: list[dict[str, Any]] = []
    for table in iter_gfm_tables(charge_md):
        if len(table) < 2:
            continue
        hdr = [_norm_header(c) for c in table[0]]
        joined = " ".join(hdr)
        if "spark" not in joined or "id" not in joined:
            continue
        if "status" not in joined:
            continue
        idx_spark = None
        for i, h in enumerate(hdr):
            if "spark" in h and "id" in h:
                idx_spark = i
                break
        if idx_spark is None:
            continue
        idx_status = next((i for i, h in enumerate(hdr) if "status" in h), None)
        idx_phase = next((i for i, h in enumerate(hdr) if "phase" in h), None)
        idx_intent = next((i for i, h in enumerate(hdr) if "intent" in h), None)
        for row in table[2:]:
            if len(row) < len(table[0]):
                row = row + [""] * (len(table[0]) - len(row))
            raw = row[idx_spark].strip() if idx_spark < len(row) else ""
            if not raw or raw.startswith("#"):
                continue
            m = WBS_ID_RE.search(raw)
            spark_id = m.group(1) if m else raw
            st = ""
            if idx_status is not None and idx_status < len(row):
                st = re.sub(r"[`*]", "", row[idx_status]).strip().lower()
            phase = ""
            if idx_phase is not None and idx_phase < len(row):
                phase = row[idx_phase].strip()
            intent = ""
            if idx_intent is not None and idx_intent < len(row):
                intent = row[idx_intent].strip()
            out.append(
                {
                    "spark_id": spark_id,
                    "phase": phase,
                    "intent": intent,
                    "status": st,
                }
            )
    return out


def parse_charge_frontmatter(charge_md: str) -> dict[str, Any]:
    """YAML frontmatter on Charge: hat, date, iteration."""
    out: dict[str, Any] = {"hat": "", "date": "", "iteration": ""}
    if not charge_md.startswith("---"):
        return out
    end = charge_md.find("\n---", 3)
    if end < 0:
        return out
    fm = charge_md[3:end].strip()
    try:
        meta = yaml.safe_load(fm)
    except yaml.YAMLError:
        return out
    if not isinstance(meta, dict):
        return out
    out["hat"] = str(meta.get("hat") or "").strip()
    out["date"] = str(meta.get("date") or "").strip()
    out["iteration"] = str(meta.get("iteration") or "").strip()
    return out


def _charge_body_after_frontmatter(charge_md: str) -> str:
    if not charge_md.startswith("---"):
        return charge_md
    end = charge_md.find("\n---", 3)
    if end < 0:
        return charge_md
    return charge_md[end + 4 :].lstrip("\n")


def iter_h2_sections(md: str) -> list[tuple[str, str]]:
    """Split markdown into (## title, body) pairs. Preamble before first ## is ("", body)."""
    lines = md.splitlines()
    sections: list[tuple[str, str]] = []
    cur_title = ""
    cur_lines: list[str] = []
    for line in lines:
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            if cur_title or cur_lines:
                sections.append((cur_title, "\n".join(cur_lines)))
            cur_title = m.group(1).strip()
            cur_lines = []
        else:
            cur_lines.append(line)
    sections.append((cur_title, "\n".join(cur_lines)))
    return sections


def _section_is_blockers(title: str) -> bool:
    t = _norm_header(title)
    return t == "blockers" or t.startswith("blocker")


def _section_is_banking(title: str) -> bool:
    t = _norm_header(title)
    return "banking" in t or ("bank" in t and "decision" in t)


def _parse_spark_blocker_action_table(table: list[list[str]]) -> list[dict[str, Any]]:
    """Blockers table: Spark | Blocker | Action."""
    if len(table) < 2:
        return []
    hdr = [_norm_header(c) for c in table[0]]
    joined = " ".join(hdr)
    if "spark" not in joined:
        return []
    idx_spark = next((i for i, h in enumerate(hdr) if "spark" in h), None)
    if idx_spark is None:
        return []
    idx_block = next(
        (i for i, h in enumerate(hdr) if "blocker" in h and "reason" not in h), None
    )
    idx_action = next((i for i, h in enumerate(hdr) if "action" in h), None)
    if idx_block is None:
        idx_block = next((i for i, h in enumerate(hdr) if "block" in h), None)
    out: list[dict[str, Any]] = []
    for row in table[2:]:
        if len(row) < len(table[0]):
            row = row + [""] * (len(table[0]) - len(row))
        raw = row[idx_spark].strip() if idx_spark < len(row) else ""
        if not raw or raw.startswith("#"):
            continue
        m = WBS_ID_RE.search(raw)
        spark_id = m.group(1) if m else raw
        blocker = ""
        if idx_block is not None and idx_block < len(row):
            blocker = re.sub(r"[`*]", "", row[idx_block]).strip()
        action = ""
        if idx_action is not None and idx_action < len(row):
            action = row[idx_action].strip()
        out.append({"spark_id": spark_id, "blocker": blocker, "action": action})
    return out


def _parse_spark_banking_table(table: list[list[str]]) -> list[dict[str, Any]]:
    """Banking decisions: Spark | Reason banked | Restart context."""
    if len(table) < 2:
        return []
    hdr = [_norm_header(c) for c in table[0]]
    joined = " ".join(hdr)
    if "spark" not in joined:
        return []
    idx_spark = next((i for i, h in enumerate(hdr) if "spark" in h), None)
    if idx_spark is None:
        return []
    idx_reason = next(
        (
            i
            for i, h in enumerate(hdr)
            if "reason" in h or ("bank" in h and "restart" not in h)
        ),
        None,
    )
    idx_restart = next((i for i, h in enumerate(hdr) if "restart" in h), None)
    out: list[dict[str, Any]] = []
    for row in table[2:]:
        if len(row) < len(table[0]):
            row = row + [""] * (len(table[0]) - len(row))
        raw = row[idx_spark].strip() if idx_spark < len(row) else ""
        if not raw or raw.startswith("#"):
            continue
        m = WBS_ID_RE.search(raw)
        spark_id = m.group(1) if m else raw
        reason = ""
        if idx_reason is not None and idx_reason < len(row):
            reason = row[idx_reason].strip()
        restart = ""
        if idx_restart is not None and idx_restart < len(row):
            restart = row[idx_restart].strip()
        out.append(
            {"spark_id": spark_id, "reason_banked": reason, "restart_context": restart}
        )
    return out


def _first_matching_table(
    body: str,
    parser: Callable[[list[list[str]]], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    for table in iter_gfm_tables(body):
        rows = parser(table)
        if rows:
            return rows
    return []


def parse_charge_blockers(charge_md: str) -> list[dict[str, Any]]:
    """Rows from ## Blockers: spark_id, blocker, action."""
    body = _charge_body_after_frontmatter(charge_md)
    for title, sec_body in iter_h2_sections(body):
        if not _section_is_blockers(title):
            continue
        rows = _first_matching_table(sec_body, _parse_spark_blocker_action_table)
        if rows:
            return rows
    return []


def parse_charge_banking(charge_md: str) -> list[dict[str, Any]]:
    """Rows from ## Banking decisions: spark_id, reason_banked, restart_context."""
    body = _charge_body_after_frontmatter(charge_md)
    for title, sec_body in iter_h2_sections(body):
        if not _section_is_banking(title):
            continue
        rows = _first_matching_table(sec_body, _parse_spark_banking_table)
        if rows:
            return rows
    return []


def _ember_log_files(ember_dir: Path, *, limit: int = 40) -> list[Path]:
    if not ember_dir.is_dir():
        return []
    files = sorted(
        [p for p in ember_dir.glob("*.md") if p.is_file()],
        key=lambda p: p.name,
        reverse=True,
    )
    return files[:limit]


def scan_ember_for_id(
    workspace_root: Path,
    ember_dir: Path,
    work_item_id: str,
    *,
    max_entries: int = 12,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for fp in _ember_log_files(ember_dir):
        text = fp.read_text(encoding="utf-8", errors="replace")
        if work_item_id not in text and work_item_id.upper() not in text.upper():
            continue
        try:
            rel = str(fp.resolve().relative_to(workspace_root.resolve()))
        except ValueError:
            rel = fp.name
        # Split on ## Decision: for snippets
        parts = re.split(r"(?m)^##\s+Decision:", text)
        for chunk in parts[1:]:
            if work_item_id not in chunk and work_item_id.upper() not in chunk.upper():
                continue
            snippet = ("## Decision:" + chunk).strip()[:1200]
            hits.append(
                {
                    "file_rel": rel,
                    "view_href": workspace_md_view_link(rel) if rel else "",
                    "snippet": snippet,
                }
            )
            if len(hits) >= max_entries:
                return hits
        if not any(h["file_rel"] == rel for h in hits):
            idx = text.find(work_item_id)
            if idx < 0:
                idx = text.lower().find(work_item_id.lower())
            if idx >= 0:
                lo = max(0, idx - 120)
                hi = min(len(text), idx + 400)
                hits.append(
                    {
                        "file_rel": rel,
                        "view_href": workspace_md_view_link(rel) if rel else "",
                        "snippet": text[lo:hi],
                    }
                )
        if len(hits) >= max_entries:
            break
    return hits[:max_entries]


def _iter_versona_session_files(versona_root: Path) -> list[Path]:
    if not versona_root.is_dir():
        return []
    out: list[Path] = []
    for p in versona_root.rglob("*.md"):
        if p.is_file() and p.name.lower() not in ("transcript.md",):
            out.append(p)
    return out[:200]


def parse_versona_frontmatter(
    path: Path, raw: str, workspace_root: Path
) -> dict[str, Any] | None:
    if not raw.startswith("---"):
        return None
    end = raw.find("\n---", 3)
    if end < 0:
        return None
    fm = raw[3:end].strip()
    try:
        meta = yaml.safe_load(fm)
    except yaml.YAMLError:
        return None
    if not isinstance(meta, dict):
        return None
    refs = meta.get("work_item_refs")
    if refs is None:
        refs = []
    if isinstance(refs, str):
        refs = [refs]
    if not isinstance(refs, list):
        refs = []
    try:
        rel = str(path.resolve().relative_to(workspace_root.resolve()))
    except ValueError:
        rel = str(path)
    rel = rel.replace("\\", "/")
    return {
        "session_id": str(meta.get("session_id") or path.parent.name),
        "started_at": meta.get("started_at"),
        "work_item_refs": [str(x) for x in refs if x],
        "ember_log_ref": meta.get("ember_log_ref"),
        "path": rel,
        "view_href": workspace_md_view_link(rel),
    }


def index_versona_sessions(
    workspace_root: Path, versona_root: Path
) -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []
    wr = workspace_root.resolve()
    for p in _iter_versona_session_files(versona_root):
        try:
            raw = p.read_text(encoding="utf-8", errors="replace")[:48000]
        except OSError:
            continue
        parsed = parse_versona_frontmatter(p, raw, wr)
        if parsed:
            sessions.append(parsed)
    return sessions


def sessions_for_id(
    sessions: list[dict[str, Any]], work_item_id: str
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for s in sessions:
        refs = s.get("work_item_refs") or []
        if work_item_id in refs:
            out.append(s)
            continue
        for r in refs:
            if work_item_id in str(r) or str(r) in work_item_id:
                out.append(s)
                break
    return out


def journal_hits_for_id(
    workspace_root: Path, journal_dir: Path, work_item_id: str, *, limit: int = 6
) -> list[dict[str, str]]:
    if not journal_dir.is_dir():
        return []
    hits: list[dict[str, str]] = []
    wr = workspace_root.resolve()
    for fp in sorted(journal_dir.glob("*.md"), key=lambda p: p.name, reverse=True):
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if work_item_id not in text:
            continue
        try:
            rel = str(fp.resolve().relative_to(wr)).replace("\\", "/")
        except ValueError:
            rel = str(fp)
        hits.append(
            {
                "file_rel": rel,
                "view_href": workspace_md_view_link(rel),
                "snippet": text[:800],
            }
        )
        if len(hits) >= limit:
            break
    return hits


def wbs_model_to_plan_tree(model: WbsModel) -> dict[str, Any]:
    """Grouped stories under epic keys for the Plan UI."""
    by_epic: dict[str, list[dict[str, Any]]] = {}
    for sid, st in sorted(model.stories.items(), key=lambda x: x[0]):
        ek = st.epic_label or "—"
        by_epic.setdefault(ek, []).append(
            {
                "id": sid,
                "title": st.title,
                "theme": st.theme_label,
                "epic": st.epic_label,
                "task_count": len(st.tasks),
            }
        )
    milestones: list[dict[str, Any]] = []
    for ek, title, th in model.epics:
        milestones.append(
            {
                "epic_key": ek,
                "title": title,
                "theme": th,
                "stories": by_epic.get(title, []),
            }
        )
    # If epics list empty but we have stories, still expose flat stories
    if not milestones and model.stories:
        milestones.append(
            {
                "epic_key": "—",
                "title": "Stories",
                "theme": "",
                "stories": [
                    {
                        "id": sid,
                        "title": st.title,
                        "theme": st.theme_label,
                        "epic": st.epic_label,
                        "task_count": len(st.tasks),
                    }
                    for sid, st in sorted(model.stories.items(), key=lambda x: x[0])
                ],
            }
        )
    return {
        "milestones": milestones,
        "story_ids": sorted(model.stories.keys()),
    }


def build_plan_spine_payload(
    workspace_root: Path,
    *,
    repo_hint: str,
    wbs_rel: str,
    roadmap_rel: str | None = None,
) -> dict[str, Any]:
    """JSON payload for GET /api/plan-spine."""
    wr = workspace_root.resolve()
    base = _repo_base(wr, repo_hint)
    charge_path = base / "forge" / "charge.md"
    ember_dir = base / "ember-logs"
    versona_root = base / "forge-logs" / "versona"
    journal_dir = base / "forge" / "journal"

    wbs_full = wr / wbs_rel.replace("\\", "/").strip("/")
    if not wbs_full.is_file():
        return {"ok": False, "error": "wbs_not_found", "wbs_rel": wbs_rel}
    text = wbs_full.read_text(encoding="utf-8", errors="replace")
    model = parse_wbs_markdown(wbs_rel, text)

    roadmap_summary: dict[str, Any] | None = None
    if roadmap_rel:
        rp = wr / roadmap_rel.replace("\\", "/").strip("/")
        if rp.is_file():
            rm = rp.read_text(encoding="utf-8", errors="replace")
            gantt = extract_gantt_model(rm)
            ds = extract_date_shift_model(rm)
            roadmap_summary = {
                "metrics": extract_chart_metrics(rm),
                "has_gantt": bool(gantt.get("has_gantt")),
                "has_date_shift": bool(ds.get("has_date_shift")),
                "date_shift": ds,
                "rel_path": roadmap_rel,
            }

    charge_rows: list[dict[str, Any]] = []
    charge_rel = ""
    if charge_path.is_file():
        try:
            rel = str(charge_path.relative_to(wr))
        except ValueError:
            rel = str(charge_path)
        charge_rel = rel.replace("\\", "/")
        ct = charge_path.read_text(encoding="utf-8", errors="replace")
        charge_rows = parse_charge_sparks(ct)

    versona_sessions = index_versona_sessions(wr, versona_root)

    tree = wbs_model_to_plan_tree(model)

    return {
        "ok": True,
        "repo_hint": repo_hint,
        "wbs_rel": wbs_rel,
        "roadmap_rel": roadmap_rel or "",
        "roadmap_summary": roadmap_summary,
        "forge": {
            "charge_path": charge_rel,
            "charge_view": workspace_md_view_link(charge_rel) if charge_rel else "",
            "ember_logs_dir": str(ember_dir.relative_to(wr)) if ember_dir.is_dir() else "",
            "versona_root": str(versona_root.relative_to(wr)) if versona_root.is_dir() else "",
            "journal_dir": str(journal_dir.relative_to(wr)) if journal_dir.is_dir() else "",
        },
        "charge_sparks": charge_rows,
        "versona_session_count": len(versona_sessions),
        "plan": tree,
        "wbs_view": f"/wbs/view?p={wbs_rel}",
    }


def _work_model_story_extras(
    workspace_root: Path,
    *,
    repo_hint: str,
    wbs_rel: str,
    roadmap_rel: str | None,
    story_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Product docs and graph-linked decisions/sessions for a story node."""
    from lenses.forge_work_model import build_forge_work_model

    wm = build_forge_work_model(
        workspace_root,
        repo_hint=repo_hint,
        wbs_rel=wbs_rel,
        roadmap_rel=roadmap_rel,
    )
    n = wm.nodes.get(story_id)
    if not n:
        return [], [], []
    products: list[dict[str, Any]] = []
    for did in n.extra.get("document_ref_ids") or []:
        dn = wm.nodes.get(did)
        if not dn:
            continue
        href = ""
        if dn.provenance:
            href = dn.provenance[0].get("view_href", "")
        products.append(
            {
                "id": did,
                "title": dn.title,
                "path": str(dn.extra.get("path", "") or ""),
                "view_href": href,
            }
        )
    decisions: list[dict[str, Any]] = []
    for did in n.extra.get("decision_ref_ids") or []:
        dn = wm.nodes.get(did)
        if not dn:
            continue
        href = ""
        if dn.provenance:
            href = dn.provenance[0].get("view_href", "")
        decisions.append(
            {
                "id": did,
                "title": dn.title,
                "view_href": href,
                "snippet": (dn.extra or {}).get("snippet", ""),
            }
        )
    sessions: list[dict[str, Any]] = []
    for sid in n.extra.get("session_ref_ids") or []:
        sn = wm.nodes.get(sid)
        if not sn:
            continue
        href = ""
        if sn.provenance:
            href = sn.provenance[0].get("view_href", "")
        sessions.append(
            {
                "id": sid,
                "title": sn.title,
                "session_id": (sn.extra or {}).get("session_id", ""),
                "view_href": href,
                "path": (sn.extra or {}).get("path", ""),
            }
        )
    return products, decisions, sessions


def _execution_sparks_from_story(story: WbsStory) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in story.tasks:
        phase = ""
        row = t.row or {}
        for key, val in row.items():
            if re.sub(r"\s+", " ", key.strip().lower()) == "phase" or "phase" in key.lower():
                phase = (val or "").strip()
                break
        out.append(
            {
                "id": t.id,
                "title": t.title,
                "phase": phase,
                "blockers": list(t.blockers),
                "row": t.row,
            }
        )
    return out


def _story_hub_outcome_loop(wr: Path, work_item_id: str) -> dict[str, Any] | None:
    try:
        from lenses.bridge.outcome_b6_feature_flag import experimental_outcome_bridge_b6_enabled
        from lenses.bridge.outcome_service import outcome_summary_for_work_item
        from lenses.orchestration_graph.db import connect
    except ImportError:
        return None
    if not experimental_outcome_bridge_b6_enabled():
        return None
    conn = connect(wr)
    if conn is None:
        return None
    try:
        return outcome_summary_for_work_item(conn, work_item_id)
    finally:
        conn.close()


def _story_hub_handoff_loop(wr: Path, work_item_id: str) -> dict[str, Any] | None:
    try:
        from lenses.bridge.handoff_b5_feature_flag import experimental_handoff_bridge_b5_enabled
        from lenses.bridge.handoff_service import handoff_summary_for_work_item
        from lenses.orchestration_graph.db import connect
    except ImportError:
        return None
    if not experimental_handoff_bridge_b5_enabled():
        return None
    conn = connect(wr)
    if conn is None:
        return None
    try:
        return handoff_summary_for_work_item(conn, work_item_id)
    finally:
        conn.close()


def build_story_hub_payload(
    workspace_root: Path,
    *,
    repo_hint: str,
    wbs_rel: str,
    work_item_id: str,
    roadmap_rel: str | None = None,
) -> dict[str, Any]:
    """JSON payload for GET /api/story-hub."""
    wr = workspace_root.resolve()
    base = _repo_base(wr, repo_hint)
    ember_dir = base / "ember-logs"
    versona_root = base / "forge-logs" / "versona"
    journal_dir = base / "forge" / "journal"

    wbs_full = wr / wbs_rel.replace("\\", "/").strip("/")
    if not wbs_full.is_file():
        return {"ok": False, "error": "wbs_not_found", "wbs_rel": wbs_rel}
    text = wbs_full.read_text(encoding="utf-8", errors="replace")
    model = parse_wbs_markdown(wbs_rel, text)

    wid = work_item_id.strip()
    story = model.stories.get(wid)
    task = model.tasks.get(wid)
    parent_story_id = ""
    if task:
        parent_story_id = task.story_id
        if not parent_story_id:
            parent_story_id = re.sub(r"T\d+$", "", wid)
        story = model.stories.get(parent_story_id)

    charge_path = base / "forge" / "charge.md"
    charge_hits: list[dict[str, Any]] = []
    if charge_path.is_file():
        ct = charge_path.read_text(encoding="utf-8", errors="replace")
        for row in parse_charge_sparks(ct):
            if row["spark_id"] == wid or row["spark_id"].startswith(wid):
                charge_hits.append(row)
            elif wid in row["spark_id"]:
                charge_hits.append(row)

    sessions = index_versona_sessions(wr, versona_root)
    sess_hits = sessions_for_id(sessions, wid)
    if not sess_hits and parent_story_id:
        sess_hits = sessions_for_id(sessions, parent_story_id)

    ember_hits = scan_ember_for_id(wr, ember_dir, wid)
    if not ember_hits and parent_story_id:
        ember_hits = scan_ember_for_id(wr, ember_dir, parent_story_id)

    journal_hits = journal_hits_for_id(wr, journal_dir, wid)

    definition: dict[str, Any] | None = None
    if task:
        definition = {
            "kind": "task",
            "id": task.id,
            "title": task.title,
            "story_id": parent_story_id,
            "row": task.row,
        }
    elif story:
        definition = {
            "kind": "story",
            "id": story.id,
            "title": story.title,
            "theme": story.theme_label,
            "epic": story.epic_label,
            "acceptance_summary": story.acceptance_summary,
            "product_paths": story.product_paths,
            "row": story.row,
            "tasks": [
                {"id": t.id, "title": t.title, "row": t.row} for t in story.tasks
            ],
        }

    roadmap_ctx: dict[str, Any] | None = None
    roadmap_md: str | None = None
    if roadmap_rel:
        rp = wr / roadmap_rel.replace("\\", "/").strip("/")
        if rp.is_file():
            roadmap_md = rp.read_text(encoding="utf-8", errors="replace")
            roadmap_ctx = {
                "rel_path": roadmap_rel,
                "metrics": extract_chart_metrics(roadmap_md),
                "date_shift": extract_date_shift_model(roadmap_md),
            }

    story_view: dict[str, Any] | None = None
    effective_story: WbsStory | None = story
    effective_story_id = story.id if story else ""
    if story:
        sv_core = build_story_view_dict(
            story,
            model,
            wbs_rel,
            roadmap_rel,
            roadmap_md,
            work_item_id=wid,
        )
        prod_g, dec_g, sess_g = _work_model_story_extras(
            wr,
            repo_hint=repo_hint,
            wbs_rel=wbs_rel,
            roadmap_rel=roadmap_rel,
            story_id=story.id,
        )
        story_view = {
            **sv_core,
            "product_context": prod_g,
            "decisions": {
                "ember_scans": ember_hits,
                "graph_decisions": dec_g,
                "graph_sessions": sess_g,
                "versona_sessions": sess_hits,
            },
            "execution": {
                "charge_rows": charge_hits,
                "sparks": _execution_sparks_from_story(story),
            },
            "sources": {
                "wbs_view": f"/wbs/view?p={wbs_rel}",
                "charge": workspace_md_view_link(str(charge_path.relative_to(wr)))
                if charge_path.is_file()
                else "",
                "journal": journal_hits,
            },
        }
    elif task and parent_story_id and model.stories.get(parent_story_id):
        # Spark: attach parent story_view for cockpit (execution focuses on this task)
        ps = model.stories[parent_story_id]
        sv_core = build_story_view_dict(
            ps,
            model,
            wbs_rel,
            roadmap_rel,
            roadmap_md,
            work_item_id=wid,
        )
        prod_g, dec_g, sess_g = _work_model_story_extras(
            wr,
            repo_hint=repo_hint,
            wbs_rel=wbs_rel,
            roadmap_rel=roadmap_rel,
            story_id=ps.id,
        )
        story_view = {
            **sv_core,
            "product_context": prod_g,
            "decisions": {
                "ember_scans": ember_hits,
                "graph_decisions": dec_g,
                "graph_sessions": sess_g,
                "versona_sessions": sess_hits,
            },
            "execution": {
                "charge_rows": charge_hits,
                "sparks": _execution_sparks_from_story(ps),
                "selected_spark_id": task.id,
            },
            "sources": {
                "wbs_view": f"/wbs/view?p={wbs_rel}",
                "charge": workspace_md_view_link(str(charge_path.relative_to(wr)))
                if charge_path.is_file()
                else "",
                "journal": journal_hits,
            },
        }

    charge_rel = ""
    if charge_path.is_file():
        try:
            charge_rel = str(charge_path.relative_to(wr)).replace("\\", "/")
        except ValueError:
            charge_rel = "forge/charge.md"

    eff_story = ""
    if story:
        eff_story = story.id
    elif parent_story_id:
        eff_story = parent_story_id

    payload: dict[str, Any] = {
        "ok": True,
        "work_item_id": wid,
        "repo_hint": repo_hint,
        "wbs_rel": wbs_rel,
        "roadmap_rel": roadmap_rel or "",
        "definition": definition,
        "today_charge": charge_hits,
        "decision_log_ember": ember_hits,
        "discipline_sessions_versona": sess_hits,
        "journal": journal_hits,
        "story_view": story_view,
        "provenance": {
            "wbs_view": f"/wbs/view?p={wbs_rel}",
            "charge": workspace_md_view_link(charge_rel) if charge_rel else "",
        },
        "roadmap_ctx": roadmap_ctx,
    }
    if eff_story:
        ce = _story_hub_code_execution(wr, repo_hint, eff_story)
        if ce:
            payload["code_execution"] = ce
    ho = _story_hub_handoff_loop(wr, wid)
    if ho:
        payload["handoff_loop"] = ho
    oc = _story_hub_outcome_loop(wr, wid)
    if oc:
        payload["outcome_loop"] = oc
    return payload
