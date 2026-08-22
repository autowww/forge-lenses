"""Hydrate sticker boards from Forge work model (WBS / plan paths)."""

from __future__ import annotations

import secrets
import string
from pathlib import Path
from typing import Any

from lenses.forge_work_model import build_forge_work_model
from lenses.sticker_board import MAX_STICKERS
from lenses.wbs_management import WORKSPACE_PROJECT_KEY, build_wbs_project_rows

_HORIZON_NOW = frozenset({"now", "h1", "current"})
_HORIZON_NEXT = frozenset({"next", "h2", "near"})
_HORIZON_LATER = frozenset({"later", "h3", "future", "backlog"})


def _sticker_uid() -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "s-" + "".join(secrets.choice(alphabet) for _ in range(10))


def resolve_project_plan_paths(
    workspace_root: Path,
    state: dict[str, Any],
    project_slug: str,
) -> dict[str, str]:
    """Default repo hint and relative WBS / roadmap paths for a workspace child."""
    slug = (project_slug or "").strip()
    repo = "" if slug in ("", "_unassigned", WORKSPACE_PROJECT_KEY) else slug
    wbs_p = ""
    roadmap_p = ""
    rows = build_wbs_project_rows(state)
    row = next((r for r in rows if r.key == slug), None)
    if row and row.wbs_entries:
        wbs_p = str(row.wbs_entries[0].get("rel_path", "")).strip()
    for rm in state.get("roadmaps") or []:
        if not isinstance(rm, dict):
            continue
        hint = str(rm.get("repo_hint", "")).strip()
        rel = str(rm.get("rel_path", "")).strip()
        if not rel:
            continue
        if repo and hint == repo:
            roadmap_p = rel
            break
        if not repo and hint in ("", "docs"):
            roadmap_p = rel
            break
    if repo and not roadmap_p:
        for rm in state.get("roadmaps") or []:
            if not isinstance(rm, dict):
                continue
            if str(rm.get("repo_hint", "")).strip() == repo:
                roadmap_p = str(rm.get("rel_path", "")).strip()
                break
    return {"repo": repo, "wbs_p": wbs_p, "roadmap_p": roadmap_p}


def _column_id_for_product_map(kind: str, horizon: str | None) -> str:
    h = (horizon or "").strip().lower()
    if h in _HORIZON_NOW:
        return "now"
    if h in _HORIZON_NEXT:
        return "next"
    if h in _HORIZON_LATER:
        return "later"
    if kind == "epic":
        return "capabilities"
    if kind == "milestone":
        return "parking"
    if kind == "story":
        return "journey"
    return "parking"


def _column_id_for_roadmap(horizon: str | None, default_col: str) -> str:
    h = (horizon or "").strip().lower()
    if h in _HORIZON_NOW:
        return "now"
    if h in _HORIZON_NEXT:
        return "next"
    if h in _HORIZON_LATER:
        return "later"
    return default_col


def hydrate_board_from_product_map(
    workspace_root: Path,
    board_state: dict[str, Any],
    *,
    repo: str,
    wbs_p: str,
    roadmap_p: str = "",
    session_template: str = "product_map_workshop",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Add stickers from work model. Returns (board_state, meta) with keys
    prefill_ok, prefill_message, stickers_added.
    """
    meta: dict[str, Any] = {
        "prefill_ok": False,
        "prefill_message": "",
        "stickers_added": 0,
    }
    wbs_rel = (wbs_p or "").strip()
    if not wbs_rel:
        meta["prefill_message"] = "no_wbs_for_project"
        return board_state, meta

    model = build_forge_work_model(
        workspace_root,
        repo_hint=repo,
        wbs_rel=wbs_rel,
        roadmap_rel=roadmap_p or None,
    )
    if not model.sources_present.get("wbs"):
        meta["prefill_message"] = "wbs_file_missing"
        return board_state, meta

    col_ids = {c["id"] for c in board_state.get("columns") or [] if isinstance(c, dict)}
    stickers: list[dict[str, Any]] = list(board_state.get("stickers") or [])
    order_by_col: dict[str, int] = {}

    def append_sticker(
        *,
        title: str,
        body: str,
        column_id: str,
        source_node_id: str,
        source_kind: str,
    ) -> None:
        if len(stickers) >= MAX_STICKERS:
            return
        cid = column_id if column_id in col_ids else (next(iter(col_ids), None) or "parking")
        if cid not in order_by_col:
            order_by_col[cid] = 0
        st = {
            "id": _sticker_uid(),
            "title": title[:200],
            "body": body[:16000] if body else "",
            "column_id": cid,
            "order": order_by_col[cid],
            "x": 0.0,
            "y": 0.0,
            "source_node_id": source_node_id,
            "source_kind": source_kind,
        }
        order_by_col[cid] += 1
        stickers.append(st)

    for nid, node in sorted(model.nodes.items()):
        kind = node.kind
        if kind not in ("milestone", "epic", "story"):
            continue
        horizon = None
        if isinstance(node.extra, dict):
            horizon = node.extra.get("horizon") or node.extra.get("roadmap_horizon")
        if session_template == "roadmap_session":
            cid = _column_id_for_roadmap(horizon, "parking")
        else:
            cid = _column_id_for_product_map(kind, horizon)
        body_parts = []
        if node.status:
            body_parts.append(f"Status: {node.status}")
        if node.dependencies:
            body_parts.append("Dependencies: " + ", ".join(node.dependencies[:8]))
        append_sticker(
            title=node.title,
            body="\n".join(body_parts),
            column_id=cid,
            source_node_id=nid,
            source_kind=kind,
        )

    board_state["stickers"] = stickers
    board_state["prefill_applied"] = True
    meta["prefill_ok"] = True
    meta["stickers_added"] = len(stickers)
    meta["prefill_message"] = "ok"
    return board_state, meta
