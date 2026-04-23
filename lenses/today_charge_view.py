"""JSON payload for the Today (Charge) operational view on /plan."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from lenses.charge_semantics import (
    status_banked,
    status_blocked_word,
    status_terminal,
)
from lenses.forge_spine import (
    _repo_base,
    index_versona_sessions,
    parse_charge_banking,
    parse_charge_blockers,
    parse_charge_frontmatter,
    parse_charge_sparks,
)
from lenses.forge_work_model import ForgeWorkModel, build_forge_work_model
from lenses.safe_forge_paths import workspace_md_view_link
from lenses.story_definition_synthesis import synthesize_wbs_slots
from lenses.wbs_model import WbsModel, parse_wbs_markdown

_RECENTLY_RESOLVED_CAP = 20

_SPARK_STORY_RE = re.compile(r"^(M\d+E\d+S\d+)T\d+$")


def _phase_prefix(spark_id: str) -> str:
    m = re.match(r"^(M\d+)", spark_id.strip())
    return m.group(1) if m else ""


def _row_get_ci(row: dict[str, str], *candidates: str) -> str:
    keys = {k.lower(): k for k in row}
    for c in candidates:
        lk = c.lower()
        if lk in keys:
            return (row.get(keys[lk]) or "").strip()
    return ""


def _story_id_from_spark(spark_id: str) -> str:
    m = _SPARK_STORY_RE.match(spark_id.strip())
    return m.group(1) if m else re.sub(r"T\d+$", "", spark_id)


def _breadcrumb(
    model: ForgeWorkModel,
    wbs: WbsModel,
    spark_id: str,
) -> list[dict[str, str]]:
    """Ordered trail: milestone → epic → story → spark (Forge labels)."""
    out: list[dict[str, str]] = []
    n = model.nodes.get(spark_id)
    if n and n.kind == "spark":
        trail = model.ancestors(spark_id) + [n]
        for node in trail:
            out.append(
                {
                    "id": node.id,
                    "kind": node.kind,
                    "title": node.title or node.id,
                }
            )
        return out
    # Fallback from IDs when node missing
    sid = _story_id_from_spark(spark_id)
    st = wbs.stories.get(sid)
    story_title = st.title if st else ""
    ek = ""
    if st and st.epic_label:
        ek = st.epic_label
    else:
        m = re.match(r"^(M\d+E\d+)", sid)
        ek = m.group(1) if m else ""
    mk = ""
    if ek:
        m2 = re.match(r"^(M\d+)", ek)
        mk = m2.group(1) if m2 else ""
    if mk:
        out.append({"id": mk, "kind": "milestone", "title": f"Milestone {mk}"})
    if ek:
        epic_title = ek
        for eid, title, _ in wbs.epics:
            if eid == ek:
                epic_title = title
                break
        out.append({"id": ek, "kind": "epic", "title": epic_title})
    out.append(
        {
            "id": sid,
            "kind": "story",
            "title": story_title or sid,
        }
    )
    out.append({"id": spark_id, "kind": "spark", "title": spark_id})
    return out


def _gaps_for_spark(
    model: ForgeWorkModel,
    wbs: WbsModel,
    wbs_rel: str,
    story_id: str,
) -> list[str]:
    gaps: list[str] = []
    sn = model.nodes.get(story_id)
    if sn and sn.kind == "story":
        dids = (sn.extra or {}).get("decision_ref_ids") or []
        if not dids:
            gaps.append("No graph-linked decisions (Ember)")
    story = wbs.stories.get(story_id)
    if story:
        slots, _ = synthesize_wbs_slots(story, wbs_rel)
        ev = (slots.get("evidence_of_done") or {}).get("text", "").strip()
        if not ev:
            gaps.append("Evidence of done not filled (story)")
    return gaps[:4]


def _spark_owner(wbs: WbsModel, spark_id: str, file_hat: str) -> str:
    task = wbs.tasks.get(spark_id)
    if task and task.row:
        o = _row_get_ci(
            task.row,
            "owner",
            "assignee",
            "hat",
            "driver",
        )
        if o:
            return o
    return file_hat


def _blocker_text(
    wbs: WbsModel,
    spark_id: str,
    blocker_row: dict[str, Any] | None,
) -> str:
    task = wbs.tasks.get(spark_id)
    wbs_b = list(task.blockers) if task else []
    if wbs_b:
        return "; ".join(wbs_b)
    if blocker_row:
        return str(blocker_row.get("blocker") or "").strip()
    return ""


def _next_action(
    charge_intent: str,
    blocker_row: dict[str, Any] | None,
    has_blocker: bool,
) -> str:
    if blocker_row:
        act = str(blocker_row.get("action") or "").strip()
        if act:
            return act
    if has_blocker and not (blocker_row and str(blocker_row.get("action") or "").strip()):
        return "Unblock or escalate"
    if charge_intent.strip():
        return charge_intent.strip()
    return "Review WBS / Charge"


def plan_href(
    wbs_rel: str,
    repo_hint: str,
    roadmap_rel: str | None,
    node_id: str,
) -> str:
    """Build `/plan` URL for a work node (canonical ids)."""
    q = f"wbs_p={quote(wbs_rel)}&repo={quote(repo_hint)}"
    if roadmap_rel:
        q += f"&roadmap_p={quote(roadmap_rel)}"
    q += f"&id={quote(node_id)}"
    return f"/plan?{q}"


def _ordered_spark_ids(
    active_rows: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    banking: list[dict[str, Any]],
) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for row in active_rows:
        sid = str(row.get("spark_id") or "").strip()
        if sid and sid not in seen:
            seen.add(sid)
            out.append(sid)
    for row in blockers:
        sid = str(row.get("spark_id") or "").strip()
        if sid and sid not in seen:
            seen.add(sid)
            out.append(sid)
    for row in banking:
        sid = str(row.get("spark_id") or "").strip()
        if sid and sid not in seen:
            seen.add(sid)
            out.append(sid)
    return out


def build_today_charge_payload(
    workspace_root: Path,
    *,
    repo_hint: str,
    wbs_rel: str,
    roadmap_rel: str | None = None,
) -> dict[str, Any]:
    """
    JSON for GET /api/today-charge.

    Classification precedence: banked → terminal → blocked → active.
    Recently resolved = terminal rows from the Active Sparks table (same file), capped.
    """
    wr = workspace_root.resolve()
    wbs_path = wr / wbs_rel.replace("\\", "/").strip("/")
    if not wbs_path.is_file():
        return {"ok": False, "error": "wbs_not_found", "wbs_rel": wbs_rel}

    base = _repo_base(wr, repo_hint)
    charge_path = base / "forge" / "charge.md"
    charge_md = ""
    if charge_path.is_file():
        charge_md = charge_path.read_text(encoding="utf-8", errors="replace")

    fm = parse_charge_frontmatter(charge_md)
    active_rows = parse_charge_sparks(charge_md)
    blocker_rows = parse_charge_blockers(charge_md)
    banking_rows = parse_charge_banking(charge_md)

    blocker_by_spark: dict[str, dict[str, Any]] = {}
    for br in blocker_rows:
        sid = str(br.get("spark_id") or "").strip()
        if sid:
            blocker_by_spark[sid] = br

    banking_ids = {str(r.get("spark_id") or "").strip() for r in banking_rows if r.get("spark_id")}

    wbs_text = wbs_path.read_text(encoding="utf-8", errors="replace")
    wbs = parse_wbs_markdown(wbs_rel, wbs_text)
    model = build_forge_work_model(
        wr,
        repo_hint=repo_hint,
        wbs_rel=wbs_rel,
        roadmap_rel=roadmap_rel,
    )

    versona_root = base / "forge-logs" / "versona"
    sessions = index_versona_sessions(wr, versona_root)
    pending_versona: list[dict[str, Any]] = []
    for s in sessions:
        ref = s.get("ember_log_ref")
        if ref is not None and isinstance(ref, str) and ref.strip():
            continue
        refs = s.get("work_item_refs") or []
        plan_links: list[dict[str, str]] = []
        for r in refs:
            rid = str(r).strip()
            if rid in model.nodes:
                plan_links.append(
                    {
                        "id": rid,
                        "plan_href": plan_href(
                            wbs_rel, repo_hint, roadmap_rel, rid
                        ),
                    }
                )
        pending_versona.append(
            {
                "session_id": str(s.get("session_id") or ""),
                "path": str(s.get("path") or ""),
                "view_href": str(s.get("view_href") or ""),
                "work_item_refs": [str(x) for x in refs if x],
                "plan_links": plan_links,
            }
        )

    charge_rel = ""
    if charge_path.is_file():
        try:
            charge_rel = str(charge_path.relative_to(wr)).replace("\\", "/")
        except ValueError:
            charge_rel = "forge/charge.md"

    roadmap_p = roadmap_rel or ""
    spark_ids = _ordered_spark_ids(active_rows, blocker_rows, banking_rows)

    active_rows_by_spark: dict[str, dict[str, Any]] = {}
    for row in active_rows:
        sid = str(row.get("spark_id") or "").strip()
        if sid:
            active_rows_by_spark[sid] = row

    phase_prefixes: set[str] = set()
    for sid in spark_ids:
        pp = _phase_prefix(sid)
        if pp:
            phase_prefixes.add(pp)
    sorted_phases = sorted(phase_prefixes, key=lambda x: (len(x), x))

    spark_payloads: list[dict[str, Any]] = []
    for spid in spark_ids:
        crow = active_rows_by_spark.get(spid, {})
        status_s = str(crow.get("status") or "").strip().lower()
        intent = str(crow.get("intent") or "").strip()
        phase = str(crow.get("phase") or "").strip()

        banked = spid in banking_ids or status_banked(status_s)
        terminal = status_terminal(status_s)
        blk_row = blocker_by_spark.get(spid)
        task = wbs.tasks.get(spid)
        wbs_blockers = list(task.blockers) if task else []
        blocker_txt = _blocker_text(wbs, spid, blk_row)
        has_wbs_block = bool(wbs_blockers)
        has_table_block = bool(blk_row and str(blk_row.get("blocker") or "").strip())
        blocked = (
            not banked
            and not terminal
            and (
                has_wbs_block
                or has_table_block
                or status_blocked_word(status_s)
            )
        )

        story_id = _story_id_from_spark(spid)
        title = ""
        if task:
            title = task.title
        n = model.nodes.get(spid)
        if n and n.title:
            title = n.title

        owner = _spark_owner(wbs, spid, fm.get("hat") or "")
        br_text = blocker_txt
        next_act = _next_action(intent, blk_row, bool(br_text))

        gaps = _gaps_for_spark(model, wbs, wbs_rel, story_id)
        trail = _breadcrumb(model, wbs, spid)

        def _label(kind: str) -> str:
            for x in trail:
                if x.get("kind") == kind:
                    return str(x.get("id") or "")
            return ""

        spark_payloads.append(
            {
                "spark_id": spid,
                "title": title or spid,
                "story_id": story_id,
                "phase_prefix": _phase_prefix(spid),
                "phase": phase,
                "intent": intent,
                "status": status_s,
                "owner": owner,
                "blocker": br_text,
                "next_action": next_act,
                "gaps": gaps,
                "breadcrumb": trail,
                "forge_labels": {
                    "spark": spid,
                    "story": story_id,
                    "epic": _label("epic"),
                    "milestone": _label("milestone"),
                },
                "plan_href": plan_href(wbs_rel, repo_hint, roadmap_p or None, spid),
                "flags": {
                    "banked": banked,
                    "blocked": blocked,
                    "terminal": terminal,
                    "done": terminal,
                },
            }
        )

    active_out: list[dict[str, Any]] = []
    blocked_out: list[dict[str, Any]] = []
    banked_out: list[dict[str, Any]] = []
    resolved_out: list[dict[str, Any]] = []

    for sp in spark_payloads:
        f = sp["flags"]
        if f["banked"]:
            banked_out.append(sp)
            continue
        if f["terminal"]:
            resolved_out.append(sp)
            continue
        if f["blocked"]:
            blocked_out.append(sp)
        else:
            active_out.append(sp)

    resolved_out = resolved_out[:_RECENTLY_RESOLVED_CAP]

    return {
        "ok": True,
        "repo_hint": repo_hint,
        "wbs_rel": wbs_rel,
        "roadmap_rel": roadmap_p,
        "spark_rows": spark_payloads,
        "charge": {
            "path": charge_rel,
            "view_href": workspace_md_view_link(charge_rel) if charge_rel else "",
            "hat": fm.get("hat") or "",
            "date": fm.get("date") or "",
            "iteration": fm.get("iteration") or "",
        },
        "phase_prefixes": sorted_phases,
        "sections": {
            "active": active_out,
            "blocked": blocked_out,
            "banked": banked_out,
            "recently_resolved": resolved_out,
            "pending_versona": pending_versona,
        },
        "notes": {
            "recently_resolved_scope": "Terminal-status sparks from this Charge file's Active Sparks table only (not git history).",
        },
    }
