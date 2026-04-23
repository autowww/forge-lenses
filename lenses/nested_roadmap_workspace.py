"""Workspace-backed nested roadmap HTML for Lenses Studio (GET /nested-roadmap-view.html)."""

from __future__ import annotations

import re
import urllib.parse
from pathlib import Path
from typing import Any


def _slug(s: str, fallback: str) -> str:
    x = re.sub(r"[^a-zA-Z0-9]+", "-", (s or "").strip().lower()).strip("-")
    return (x or fallback)[:48]


def _month_label(col_id: str) -> str:
    if col_id == "unscheduled":
        return "Unscheduled"
    return col_id


def _milestone_child_roadmap(milestone: dict[str, Any]) -> dict[str, Any] | None:
    by_wbs = milestone.get("by_wbs") or {}
    if not isinstance(by_wbs, dict) or not by_wbs:
        return None
    used_track_ids: set[str] = set()
    used_bar_ids: set[str] = set()
    tracks: list[dict[str, str]] = []
    bars: list[dict[str, Any]] = []
    for j, wbs_rel in enumerate(sorted(by_wbs.keys())):
        info = by_wbs.get(wbs_rel) or {}
        if not isinstance(info, dict):
            continue
        short = wbs_rel.split("/")[-1] if "/" in str(wbs_rel) else str(wbs_rel)
        tid = _unique_slug(short or f"wbs-{j}", used_track_ids)
        tracks.append({"id": tid, "label": (short or wbs_rel)[:56]})
        cnt = int(info.get("story_count") or 0)
        label = f"{cnt} stories" if cnt else "Linked"
        bars.append(
            {
                "id": _unique_slug(f"cell-{j}-{short}", used_bar_ids),
                "label": label,
                "trackId": tid,
                "startColumnId": "c1",
                "endColumnId": "c1",
                "summary": str(wbs_rel)[:200],
            }
        )
    if not tracks:
        return None
    return {
        "version": 1,
        "title": str(milestone.get("title") or "WBS roll-up")[:120],
        "columns": [{"id": "c1", "label": "Roll-up"}],
        "tracks": tracks,
        "bars": bars,
    }


def _unique_slug(base: str, used: set[str]) -> str:
    s = _slug(base, "item")
    cand = s
    n = 2
    while cand in used:
        cand = f"{s}-{n}"
        n += 1
    used.add(cand)
    return cand


def build_nested_roadmap_config_from_workspace(
    workspace_root: Path,
    state: dict[str, Any],
    *,
    repo_filter: str,
    roadmap_focus: str,
) -> dict[str, Any]:
    """Build Kitchen Sink nested-roadmap JSON from ``/api/roadmaps-matrix`` aggregation."""
    from lenses.roadmaps_matrix_api import build_roadmaps_matrix_payload

    rf = (repo_filter or "all").strip() or "all"
    payload = build_roadmaps_matrix_payload(workspace_root, state, repo_filter=rf)
    if not payload.get("ok"):
        err = str(payload.get("error") or "matrix_unavailable")
        return {
            "version": 1,
            "title": "Roadmaps",
            "columns": [{"id": "c1", "label": "—"}],
            "tracks": [{"id": "t1", "label": "Status"}],
            "bars": [
                {
                    "id": "matrix-unavailable",
                    "label": "Matrix unavailable",
                    "trackId": "t1",
                    "startColumnId": "c1",
                    "endColumnId": "c1",
                    "summary": err,
                }
            ],
        }

    roadmaps: list[dict[str, Any]] = [r for r in (payload.get("roadmaps") or []) if isinstance(r, dict)]
    col_order: list[str] = list(payload.get("column_order") or ["unscheduled"])
    cols = [{"id": c, "label": _month_label(str(c))} for c in col_order]
    col_ids = {c["id"] for c in cols}

    if not roadmaps:
        return {
            "version": 1,
            "title": "Roadmaps",
            "columns": cols,
            "tracks": [{"id": "t1", "label": "Milestones"}],
            "bars": [
                {
                    "id": "no-roadmaps",
                    "label": "No roadmap data",
                    "trackId": "t1",
                    "startColumnId": col_order[0],
                    "endColumnId": col_order[0],
                    "summary": "No ROADMAP.md / WBS pairs matched this repository filter.",
                }
            ],
        }

    focus = (roadmap_focus or "").strip().replace("\\", "/")
    selected: list[dict[str, Any]] = []
    if focus:
        for r in roadmaps:
            rel = str(r.get("roadmap_rel") or "").replace("\\", "/")
            if rel == focus or rel.endswith(focus) or focus in rel:
                selected.append(r)
    if not selected:
        selected = [roadmaps[0]]

    rm = selected[0]
    title = str(rm.get("roadmap_rel") or "Roadmap").replace("\\", "/")
    milestones_raw = rm.get("milestones") or []
    milestones = [m for m in milestones_raw if isinstance(m, dict)]

    themes_raw = sorted(
        {str(m.get("theme") or "").strip() for m in milestones if str(m.get("theme") or "").strip()}
    )
    used_track_ids: set[str] = set()
    if themes_raw:
        tracks = [{"id": _unique_slug(t, used_track_ids), "label": t[:56]} for t in themes_raw]
        theme_to_tid = {t: tracks[i]["id"] for i, t in enumerate(themes_raw)}
    else:
        tid = _unique_slug("milestones", used_track_ids)
        tracks = [{"id": tid, "label": "Milestones"}]
        theme_to_tid = {t: tid for t in ("",)}

    bars: list[dict[str, Any]] = []
    used_bar_ids: set[str] = set()
    for i, m in enumerate(milestones):
        theme = str(m.get("theme") or "").strip()
        tid = theme_to_tid.get(theme) or tracks[0]["id"]
        mb = str(m.get("month_bucket") or "unscheduled")
        if mb not in col_ids:
            mb = "unscheduled" if "unscheduled" in col_ids else col_order[0]
        mk = str(m.get("milestone_key") or f"m{i}")
        bid = _unique_slug(f"{mk}-{i}", used_bar_ids)
        label = str(m.get("title") or "Milestone").strip() or "Milestone"
        if len(label) > 80:
            label = label[:77] + "…"
        ek = str(m.get("epic_key") or "").strip()
        scount = int(m.get("unique_story_count") or 0)
        summary_bits = [b for b in (ek, f"{scount} stories") if b]
        summary = " · ".join(summary_bits)
        bar: dict[str, Any] = {
            "id": bid,
            "label": label,
            "trackId": tid,
            "startColumnId": mb,
            "endColumnId": mb,
            "summary": summary,
        }
        child = _milestone_child_roadmap(m)
        if child and (child.get("bars") or []):
            bar["child"] = child
        bars.append(bar)

    if not bars:
        bars.append(
            {
                "id": "no-milestones",
                "label": "No milestones in matrix",
                "trackId": tracks[0]["id"],
                "startColumnId": col_order[0],
                "endColumnId": col_order[0],
                "summary": "Spine data did not yield milestone rows for this roadmap.",
            }
        )

    return {
        "version": 1,
        "title": title,
        "columns": cols,
        "tracks": tracks,
        "bars": bars,
    }


def _fallback_document(title: str, body_html: str) -> bytes:
    inner = (
        "<!DOCTYPE html>\n"
        '<html lang="en" data-bs-theme="dark">\n<head>\n'
        '<meta charset="utf-8"/>\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>\n'
        f"<title>{title}</title>\n"
        '<link rel="stylesheet" href="/__ks/css/forge-theme.css" />\n'
        "</head>\n"
        '<body style="margin:0;padding:1.25rem;font-family:system-ui,sans-serif;color:#e5e7eb;">\n'
        f"{body_html}\n"
        "</body>\n</html>\n"
    )
    return inner.encode("utf-8")


def nested_roadmap_view_document_bytes(
    lenses_repo_root: Path,
    workspace_root: Path,
    state: dict[str, Any],
    query: str,
) -> bytes:
    """Serve at ``GET /nested-roadmap-view.html`` — embedded in Plan, Matrix, Timeline, Roadmap section."""
    from lenses.ks_layout import _ensure_ks_import_path, ks_assets_available

    if not ks_assets_available(lenses_repo_root):
        return _fallback_document(
            "Roadmap horizon — unavailable",
            "<p>Kitchen Sink assets are missing under <code>forge-lenses/kitchensink</code>.</p>",
        )

    _ensure_ks_import_path(lenses_repo_root)
    try:
        from nested_roadmap import render_nested_roadmap  # type: ignore[import-untyped]
    except ImportError:
        return _fallback_document(
            "Roadmap horizon — update Kitchen Sink",
            "<p>Bump the <code>kitchensink</code> submodule so <code>nested_roadmap</code> and assets exist.</p>",
        )

    qs = urllib.parse.parse_qs(query or "", keep_blank_values=True)
    repo = (qs.get("repo") or [""])[0].strip() or "all"
    roadmap_p = (qs.get("roadmap_p") or qs.get("p") or [""])[0].strip()

    cfg = build_nested_roadmap_config_from_workspace(
        workspace_root,
        state,
        repo_filter=repo,
        roadmap_focus=roadmap_p,
    )
    inner = render_nested_roadmap(
        config=cfg,
        roadmap_id="lenses-nested-roadmap-embed",
        include_modal_shell=True,
    )

    head = (
        '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" '
        'rel="stylesheet" crossorigin="anonymous" />\n'
        '<link rel="stylesheet" href="/__ks/css/forge-theme.css" />\n'
        '<link rel="stylesheet" href="/__ks/css/forgesdlc-theme.css" />\n'
        '<link rel="stylesheet" href="/__ks/css/nested-roadmap.css" />\n'
        "<style>\n"
        "body.lenses-nested-roadmap-view { margin:0; padding:0.75rem 0.9rem; "
        "background: var(--bs-body-bg, #0f172a); color: var(--bs-body-color, #e2e8f0); }\n"
        "</style>\n"
    )
    scripts = (
        '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" '
        'crossorigin="anonymous"></script>\n'
        '<script src="/__ks/js/nested-roadmap.js" defer></script>\n'
    )

    doc = (
        "<!DOCTYPE html>\n"
        '<html lang="en" data-bs-theme="dark">\n<head>\n'
        '<meta charset="utf-8"/>\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>\n'
        "<title>Roadmap horizon</title>\n"
        f"{head}"
        "</head>\n"
        '<body class="lenses-nested-roadmap-view">\n'
        f"{inner}\n"
        f"{scripts}"
        "</body>\n</html>\n"
    )
    return doc.encode("utf-8")
