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


def _route_is_projects(studio_route: str | None) -> bool:
    r = (studio_route or "").strip().lower()
    return r == "projects"


def _focused_project_scope(scope_site: str) -> bool:
    """True when Copilot should answer about one workspace child, not the whole portfolio."""
    return bool((scope_site or "").strip())


def _safe_repo_child_md(workspace_root: Path, scope_site: str, rel: str) -> Path | None:
    """Resolve ``rel`` under a direct workspace child folder (``scope_site``) when it is markdown."""
    site = (scope_site or "").strip()
    if not site or ".." in site or "/" in site or "\\" in site:
        return None
    rel_norm = rel.replace("\\", "/").strip("/")
    if not rel_norm or ".." in rel_norm.split("/"):
        return None
    wr = workspace_root.resolve()
    repo_root = (wr / site).resolve()
    try:
        repo_root.relative_to(wr)
    except ValueError:
        return None
    if repo_root.parent != wr or not repo_root.is_dir():
        return None
    candidate = (repo_root / rel_norm).resolve()
    try:
        candidate.relative_to(repo_root)
    except ValueError:
        return None
    if not candidate.is_file() or candidate.suffix.lower() != ".md":
        return None
    return candidate


def _repo_identity_md_snippets(workspace_root: Path, scope_site: str) -> list[tuple[str, str]]:
    """README / charge excerpts for a focused repository dashboard."""
    out: list[tuple[str, str]] = []
    for rel in ("README.md", "forge/charge.md", "sdlc/README.md"):
        spath = _safe_repo_child_md(workspace_root, scope_site, rel)
        if spath is None:
            continue
        try:
            body = spath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if body.strip():
            out.append((f"{scope_site.strip()}/{rel}", body))
    return out


def _workspace_children_roster_snippet(scan_state: dict[str, Any], *, limit: int = 80) -> str:
    children = scan_state.get("children") if isinstance(scan_state, dict) else None
    if not isinstance(children, list):
        return ""
    lines: list[str] = []
    for ch in children[:limit]:
        if not isinstance(ch, dict):
            continue
        name = str(ch.get("name") or "").strip()
        if not name:
            continue
        kind = "git repo" if ch.get("is_git") else "folder"
        branch = str(ch.get("git_branch") or "").strip()
        dirty = ch.get("git_dirty")
        meta: list[str] = [kind]
        if branch:
            meta.append(f"branch={branch}")
        if dirty is True:
            meta.append("dirty")
        lines.append(f"- {name} ({', '.join(meta)})")
    if len(children) > limit:
        lines.append(f"- … and {len(children) - limit} more entries (truncated)")
    return "\n".join(lines)


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
    fts_query_override: str | None = None,
    skip_sections: frozenset[str] | None = None,
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
    projects_route = _route_is_projects(studio_route)
    focused_repo = _focused_project_scope(scope_site)
    skip = skip_sections or frozenset()
    skip_workspace_rollups = docs_health or projects_route or "rollups" in skip
    skip_page_context = "page_context" in skip
    skip_related_md = "related_md" in skip
    skip_roster = "roster" in skip or (projects_route and focused_repo)
    skip_search = "search" in skip
    skip_orchestration = "orchestration" in skip

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
    if pcs and not skip_page_context:
        add(
            {
                "kind": "studio_page_context",
                "title": "Studio page context",
                "ref": "",
                "snippet": pcs,
            }
        )

    # --- Repository identity (README / charge) for a focused project dashboard ---
    if focused_repo and not skip_related_md:
        for rel, body in _repo_identity_md_snippets(workspace_root, scope_site):
            add(
                {
                    "kind": "repo_identity_md",
                    "title": _trunc(rel, 200),
                    "ref": workspace_md_view_link(rel),
                    "snippet": _trunc(body, 2800),
                    "source": "repo_readme",
                }
            )

    # --- Related workspace markdown (allowlisted paths only; early in bundle) ---
    if not skip_related_md:
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

    # --- Workspace project roster (Projects route; enumerate repos/folders) ---
    if projects_route and not skip_roster:
        roster = _workspace_children_roster_snippet(scan_state)
        if roster.strip():
            add(
                {
                    "kind": "workspace_projects_roster",
                    "title": "Workspace repositories and folders (from scan)",
                    "ref": "workspace:children",
                    "snippet": _trunc(roster, 4800),
                }
            )

    # --- Local search (docs / site / ingested) ---
    if not skip_search:
        q = (fts_query_override or "").strip() or search_query_for_grounding(
            user_message, studio_route=studio_route, scope_site=scope_site
        )
        try:
            sconn = search_db.connect(workspace_root)
            try:
                res = search_db.search(
                    sconn,
                    q,
                    limit=14 if docs_health else (16 if projects_route else 10),
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
    if not skip_orchestration:
        ogs = ogs_connect(workspace_root)
        if ogs is not None:
            try:
                if not skip_workspace_rollups:
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
    if not skip_workspace_rollups:
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
    if not skip_workspace_rollups:
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
    if not skip_workspace_rollups:
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
    if not skip_workspace_rollups:
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
    if not skip_workspace_rollups:
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
    elif projects_route and focused_repo:
        site = (scope_site or "").strip()
        lines_out.append(
            f"Context: the operator is on a Forge Studio **project dashboard** for repository "
            f"**{site}**. Answer only about **{site}** using studio_page_context, "
            "**repo_identity_md**, related markdown, and repository-scoped search hits. "
            "Do not list or summarize other workspace repositories unless the user explicitly "
            "asks for the whole portfolio."
        )
    elif projects_route:
        lines_out.append(
            "Context: the operator is on Forge Studio **Projects** — list or summarize workspace "
            "repositories using **workspace_projects_roster** and search hits. Give one line per project "
            "when asked; cite [n] for each factual claim. Say which projects lack enough context instead "
            "of inventing descriptions."
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


_MAP_SKIP = frozenset({"page_context", "roster", "orchestration", "rollups"})


def build_scoped_grounding_for_subtask(
    workspace_root: Path,
    *,
    scan_state: dict[str, Any],
    scope_site: str,
    related_md_rel_paths: list[str] | None,
    fts_query: str,
    max_citations: int = 8,
    studio_route: str | None = None,
) -> tuple[str, list[dict[str, Any]], bool]:
    """Slim grounding bundle for one map-reduce subtask (~search + charge.md only)."""
    block, citations, truncated = build_grounding_bundle(
        workspace_root,
        fts_query,
        scan_state=scan_state,
        scope_site=scope_site,
        max_citations=max(4, min(max_citations, 12)),
        related_md_rel_paths=related_md_rel_paths,
        studio_route=studio_route,
        fts_query_override=fts_query,
        skip_sections=_MAP_SKIP,
    )
    slim_header = [
        "You are a scoped Forge Lenses copilot slice. Answer ONLY from the numbered context.",
        "Cite [n] for each factual claim. If insufficient, say what is missing for this entry.",
        "",
    ]
    if "--- CONTEXT ---" in block:
        ctx_part = block[block.index("--- CONTEXT ---") :]
        return "\n".join(slim_header) + ctx_part, citations, truncated
    return block, citations, truncated


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

    if _route_is_projects(studio_route):
        site = (scope_site or "").strip()
        anchor_bits = ["repository", "project", "readme", "forge", "charge", "workspace"]
        if site:
            anchor_bits = [site, "readme", "repository", "overview", "forge", "charge"]
        anchor = " ".join(anchor_bits)
        tail = " ".join(parts[:10])
        merged = f"{anchor} {tail}".strip()
        vague_this_repo = frozenset(
            """
            this that here repository repo project folder workspace
            """.split()
        )
        if site and len(meaningful) < 2 and all(p.lower() in vague_this_repo for p in parts):
            merged = f"{site} readme overview repository adoption purpose".strip()
        return _trunc(merged, 220) if len(merged) > 220 else merged

    if not raw:
        return "workspace"
    if not parts:
        return raw[:80]
    return " ".join(parts[:8])
