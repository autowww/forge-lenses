"""Collect citations from search, orchestration graph, product aggregates, and LLM usage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lenses import search_db
from lenses.safe_forge_paths import (
    safe_forge_workspace_file,
    workspace_md_path_pattern_category,
    workspace_md_view_link,
)
from lenses.cross_team_release import build_cross_team_release_overview
from lenses.devsecops_compliance.aggregate import build_devsecops_overview_payload
from lenses.llm_usage_store import get_usage_summary
from lenses.ops_delivery.aggregate import build_ops_delivery_overview
from lenses.orchestration_graph.db import connect as ogs_connect
from lenses.orchestration_graph.query import trace_subgraph
from lenses.test_quality.aggregate import build_quality_overview_payload


def _trunc(s: str, n: int) -> str:
    t = (s or "").strip()
    if len(t) <= n:
        return t
    return t[: n - 1] + "…"


def _norm_related_md_paths(raw: list[str] | None) -> list[str]:
    if not raw:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for x in raw:
        s = str(x or "").replace("\\", "/").strip().strip("/")
        if not s or s in seen:
            continue
        if ".." in s.split("/"):
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= 8:
            break
    return out


def _route_is_docs_health(studio_route: str | None) -> bool:
    r = (studio_route or "").strip().lower()
    return r == "docs-health" or r.startswith("docs-health-")


def build_grounding_bundle(
    workspace_root: Path,
    user_message: str,
    *,
    scan_state: dict[str, Any],
    scope_site: str = "",
    focus_entity_id: str | None = None,
    max_citations: int = 48,
    page_context_summary: str | None = None,
    related_md_rel_paths: list[str] | None = None,
    studio_route: str | None = None,
) -> tuple[str, list[dict[str, Any]], bool]:
    """
    Returns (prompt_block, citations, truncated_flag).

    Citations use 1-based ``id`` fields; the prompt instructs the model to cite as [1], [2], …

    When ``page_context_summary`` and/or ``related_md_rel_paths`` are set (from Studio),
    those become **early** context so the model sees the current page and linked markdown
    before generic FTS and graph slices.

    ``studio_route`` (Forge Studio route id) narrows retrieval on focused screens such as
    **docs-health** so vague questions do not pull unrelated handbook matches, and trims
    demo orchestration / workspace rollup citations that are not about the current view.
    """
    citations: list[dict[str, Any]] = []
    cid = 0
    truncated = False
    docs_health = _route_is_docs_health(studio_route)

    def add(c: dict[str, Any]) -> None:
        nonlocal cid, truncated
        if len(citations) >= max_citations:
            truncated = True
            return
        cid += 1
        c2 = dict(c)
        c2["id"] = cid
        citations.append(c2)

    # --- Studio page context (client-provided; what the operator is looking at) ---
    pcs = _trunc((page_context_summary or "").strip(), 2200)
    if pcs:
        add(
            {
                "kind": "studio_page_context",
                "title": "Studio page context",
                "ref": "",
                "snippet": pcs,
            }
        )

    # --- Related workspace markdown (allowlisted paths only; early in bundle) ---
    for rel in _norm_related_md_paths(related_md_rel_paths):
        spath = safe_forge_workspace_file(workspace_root, rel)
        if spath is None:
            continue
        try:
            body = spath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        cat = workspace_md_path_pattern_category(rel) or "workspace_md"
        add(
            {
                "kind": "related_workspace_md",
                "title": _trunc(rel, 200),
                "ref": workspace_md_view_link(rel),
                "snippet": _trunc(body, 2200),
                "source": cat,
            }
        )

    # --- Local search (docs / site / ingested) ---
    q = search_query_for_grounding(
        user_message, studio_route=studio_route, scope_site=scope_site
    )
    try:
        sconn = search_db.connect(workspace_root)
        try:
            res = search_db.search(
                sconn,
                q,
                limit=14 if docs_health else 10,
                offset=0,
                scope_site=(scope_site or "").strip(),
            )
            for h in res.get("hits") or []:
                if not isinstance(h, dict):
                    continue
                title = str(h.get("title") or h.get("path_key") or "hit")
                url = str(h.get("url") or "")
                snip = str(h.get("snippet") or "")
                add(
                    {
                        "kind": "search_hit",
                        "title": _trunc(title, 200),
                        "ref": url or str(h.get("path_key") or ""),
                        "snippet": _trunc(snip, 400),
                        "source": str(h.get("source") or ""),
                    }
                )
        finally:
            sconn.close()
    except OSError:
        pass

    # --- Orchestration graph ---
    ogs = ogs_connect(workspace_root)
    if ogs is not None:
        try:
            if not docs_health:
                rows = ogs.execute(
                    """
                    SELECT id, kind, display_name, summary
                    FROM ogs_entity
                    WHERE id NOT LIKE 'ogs:demo:%'
                    ORDER BY updated_at DESC
                    LIMIT 14
                    """
                ).fetchall()
                for r in rows:
                    add(
                        {
                            "kind": "orchestration_entity",
                            "title": f"{r['kind']}: {r['display_name']}",
                            "ref": str(r["id"]),
                            "snippet": _trunc(str(r["summary"] or ""), 500),
                        }
                    )
            root_trace = (focus_entity_id or "").strip()
            if root_trace:
                sub = trace_subgraph(ogs, root_trace, direction="both", max_depth=3, max_nodes=80)
                if sub.get("ok"):
                    for n in (sub.get("nodes") or [])[:12]:
                        if not isinstance(n, dict):
                            continue
                        nid = str(n.get("id") or "")
                        if nid.startswith("ogs:demo:"):
                            continue
                        add(
                            {
                                "kind": "orchestration_trace",
                                "title": f"{n.get('kind')}: {n.get('display_name')}",
                                "ref": nid,
                                "snippet": _trunc(str(n.get("summary") or ""), 400),
                            }
                        )
        finally:
            ogs.close()

    # --- Cross-team release (go/no-go, change requests) ---
    if not docs_health:
        try:
            ctr = build_cross_team_release_overview(
                workspace_root=workspace_root, scan_state=scan_state
            )
            pkt = ctr.get("go_no_go_packet") if isinstance(ctr, dict) else None
            md = ""
            if isinstance(pkt, dict):
                md = str(pkt.get("markdown") or "")
            if md.strip():
                add(
                    {
                        "kind": "cross_team_release",
                        "title": "Go / no-go packet (excerpt)",
                        "ref": "cross-team-release:go_no_go_packet",
                        "snippet": _trunc(md, 2200),
                    }
                )
            crs = ctr.get("change_requests") if isinstance(ctr, dict) else None
            if isinstance(crs, list) and crs:
                bits = []
                for cr in crs[:6]:
                    if not isinstance(cr, dict):
                        continue
                    bits.append(
                        json.dumps(
                            {
                                "id": cr.get("id"),
                                "title": cr.get("title"),
                                "risk": cr.get("risk"),
                                "rollback_notes": cr.get("rollback_notes"),
                            },
                            ensure_ascii=False,
                        )
                    )
                if bits:
                    add(
                        {
                            "kind": "change_requests",
                            "title": "Change requests (subset)",
                            "ref": "cross-team-release:change_requests",
                            "snippet": _trunc("\n".join(bits), 1800),
                        }
                    )
        except (OSError, TypeError, ValueError):
            pass

    # --- Test quality summary ---
    if not docs_health:
        try:
            qov = build_quality_overview_payload(
                workspace_root=workspace_root, scan_state=scan_state
            )
            n_plans = len(qov.get("test_plans") or []) if isinstance(qov, dict) else 0
            n_cases = len(qov.get("test_cases") or []) if isinstance(qov, dict) else 0
            n_runs = len(qov.get("test_runs") or []) if isinstance(qov, dict) else 0
            n_def = len(qov.get("defects") or []) if isinstance(qov, dict) else 0
            rq = qov.get("release_quality") if isinstance(qov, dict) else None
            rq_s = ""
            if isinstance(rq, dict):
                rq_s = str(rq.get("summary") or "")
            add(
                {
                    "kind": "test_quality",
                    "title": "Test & quality overview (counts)",
                    "ref": "quality:overview",
                    "snippet": _trunc(
                        f"feature_enabled={qov.get('feature_enabled')} "
                        f"test_plans={n_plans} test_cases={n_cases} test_runs={n_runs} "
                        f"defects={n_def}. release_quality: {rq_s}",
                        1200,
                    ),
                }
            )
        except (OSError, TypeError, ValueError):
            pass

    # --- DevSecOps rollups / risk ---
    if not docs_health:
        try:
            d = build_devsecops_overview_payload(
                workspace_root=workspace_root, scan_state=scan_state
            )
            roll = d.get("rollups") if isinstance(d, dict) else {}
            risk = d.get("risk_score") if isinstance(d, dict) else {}
            gate = d.get("security_release_gate") if isinstance(d, dict) else {}
            rsum = str(risk.get("summary") or "") if isinstance(risk, dict) else ""
            gsum = str(gate.get("summary") or "") if isinstance(gate, dict) else ""
            add(
                {
                    "kind": "devsecops",
                    "title": "DevSecOps / compliance snapshot",
                    "ref": "devsecops:overview",
                    "snippet": _trunc(
                        f"feature_enabled={d.get('feature_enabled')} risk={rsum} gate={gsum} "
                        f"rollups_keys={list(roll.keys()) if isinstance(roll, dict) else []}",
                        1200,
                    ),
                }
            )
        except (OSError, TypeError, ValueError):
            pass

    # --- Ops / incidents (for postmortem / rollback context) ---
    if not docs_health:
        try:
            ops = build_ops_delivery_overview(workspace_root=workspace_root, scan_state=scan_state)
            inc = ops.get("incidents") if isinstance(ops, dict) else []
            pm = ops.get("postmortems") if isinstance(ops, dict) else []
            n_i = len(inc) if isinstance(inc, list) else 0
            n_p = len(pm) if isinstance(pm, list) else 0
            add(
                {
                    "kind": "ops_delivery",
                    "title": "Ops delivery snapshot",
                    "ref": "ops-delivery:overview",
                    "snippet": _trunc(
                        f"feature_enabled={ops.get('feature_enabled')} "
                        f"incidents={n_i} postmortems={n_p}",
                        800,
                    ),
                }
            )
        except (OSError, TypeError, ValueError):
            pass

    # --- Recent LLM execution events (not prompts) ---
    if not docs_health:
        try:
            usage = get_usage_summary(workspace_root)
            rev = usage.get("recent_events") or []
            if isinstance(rev, list) and rev:
                lines = []
                for ev in rev[-8:]:
                    if not isinstance(ev, dict):
                        continue
                    lines.append(
                        f"{ev.get('ts')} provider={ev.get('provider')} ok={ev.get('ok')} "
                        f"model={ev.get('model')} tokens={ev.get('total_tokens')}"
                    )
                add(
                    {
                        "kind": "llm_usage_events",
                        "title": "Recent LLM runs (metadata only)",
                        "ref": "llm-usage:events",
                        "snippet": _trunc("\n".join(lines), 900),
                    }
                )
        except (OSError, TypeError, ValueError):
            pass

    lines_out = [
        "You are the Forge Lenses SDLC copilot. Answer using ONLY the numbered context items below.",
        "Cite every factual claim with [n] matching the context item number. If the context is insufficient, say what is missing.",
    ]
    if docs_health:
        lines_out.append(
            "Context: the operator is on a Forge Studio **Docs health** view — anchor answers in "
            "studio_page_context and repository-scoped search hits; do not invent SDLC process detail "
            "from generic handbook pages unless the context explicitly supports it."
        )
    lines_out.extend(["", "--- CONTEXT ---"])
    for c in citations:
        n = c["id"]
        title = c.get("title", "")
        ref = c.get("ref", "")
        snip = c.get("snippet", "")
        lines_out.append(f"[{n}] ({c.get('kind')}) {title}")
        if ref:
            lines_out.append(f"    ref: {ref}")
        if snip:
            lines_out.append(f"    excerpt: {snip}")
        lines_out.append("")
    lines_out.append("--- END CONTEXT ---")
    return "\n".join(lines_out), citations, truncated


def search_query_for_grounding(
    message: str,
    *,
    studio_route: str | None = None,
    scope_site: str = "",
) -> str:
    """
    Build an FTS query string from the user message.

    On **docs-health** Studio routes, prepend documentation-health anchor terms (and the
    workspace child name when known) so vague prompts like “what's important here?” do not
    collapse to a single generic token such as “important”, which ranks unrelated handbook pages.
    """
    raw = (message or "").strip()
    site = (scope_site or "").strip()
    stop = frozenset(
        """
        the a an and or for to of in on is are was were be been being it this that these those
        with from at by as not no yes how what when where why who which
        """.split()
    )
    parts = [p for p in raw.replace("\n", " ").split() if len(p) > 2 and p.lower() not in stop]
    vague_only = frozenset(
        """
        important page here help summarize overview explain tips advice matters focus
        mean means meaning key keys stuff things point points
        """.split()
    )
    meaningful = [p for p in parts if p.lower() not in vague_only]

    if _route_is_docs_health(studio_route):
        anchor_bits = ["documentation", "health", "scan", "findings", "markdown", "contract"]
        anchor = f"{site} {' '.join(anchor_bits)}".strip() if site else " ".join(anchor_bits)
        tail = " ".join(parts[:8])
        if len(meaningful) < 2:
            merged = f"{anchor} {tail}".strip()
            return merged if merged else anchor
        merged2 = f"{anchor} {tail}".strip()
        return _trunc(merged2, 220) if len(merged2) > 220 else merged2

    if not raw:
        return "workspace"
    if not parts:
        return raw[:80]
    return " ".join(parts[:8])
