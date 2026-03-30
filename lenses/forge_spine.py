"""Join WBS IDs with Charge, Ember Log, and Versona sessions (deterministic, read-only)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from lenses.roadmap_outline import extract_chart_metrics, extract_gantt_model, iter_gfm_tables
from lenses.safe_forge_paths import workspace_md_view_link
from lenses.wbs_model import WBS_ID_RE, WbsModel, parse_wbs_markdown


def _norm_header(h: str) -> str:
    return re.sub(r"\s+", " ", h.strip().lower())


def _repo_base(workspace_root: Path, repo_hint: str) -> Path:
    if not repo_hint:
        return workspace_root.resolve()
    return (workspace_root / repo_hint).resolve()


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
            roadmap_summary = {
                "metrics": extract_chart_metrics(rm),
                "has_gantt": bool(gantt.get("has_gantt")),
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
    if roadmap_rel:
        rp = wr / roadmap_rel.replace("\\", "/").strip("/")
        if rp.is_file():
            rm = rp.read_text(encoding="utf-8", errors="replace")
            roadmap_ctx = {
                "rel_path": roadmap_rel,
                "metrics": extract_chart_metrics(rm),
            }

    return {
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
        "provenance": {
            "wbs_view": f"/wbs/view?p={wbs_rel}",
            "charge": workspace_md_view_link(str(charge_path.relative_to(wr)))
            if charge_path.is_file()
            else "",
        },
    }
