"""Dependency board: initiatives, teams, repos, releases, environments."""

from __future__ import annotations

from typing import Any


def build_dependency_board(doc: dict[str, Any], scan_children: list[dict[str, Any]]) -> dict[str, Any]:
    nodes_in = [n for n in doc.get("dependency_nodes") or [] if isinstance(n, dict)]
    edges_in = [e for e in doc.get("dependency_edges") or [] if isinstance(e, dict)]

    nodes: list[dict[str, Any]] = [dict(n) for n in nodes_in]
    seen = {str(n.get("id")) for n in nodes if n.get("id")}

    for c in scan_children:
        if not isinstance(c, dict) or not c.get("is_git"):
            continue
        name = str(c.get("name") or "").strip()
        if not name or name in seen:
            continue
        rid = f"repo:{name}"
        if rid in seen:
            continue
        seen.add(rid)
        nodes.append(
            {
                "id": rid,
                "kind": "repo",
                "label": name,
                "source": "workspace_scan",
                "workspace_child": name,
            }
        )

    edges: list[dict[str, Any]] = []
    for e in edges_in:
        edges.append(
            {
                "from_id": str(e.get("from_id") or ""),
                "to_id": str(e.get("to_id") or ""),
                "relation": str(e.get("relation") or "depends_on"),
                "note": str(e.get("note") or ""),
            }
        )

    return {"nodes": nodes, "edges": edges}
