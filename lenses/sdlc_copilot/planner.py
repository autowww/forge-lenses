"""Build scoped subtask plans for Copilot map-reduce."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from lenses import search_db
from lenses.sdlc_copilot.intent import CopilotStrategy


@dataclass
class Subtask:
    subtask_id: str
    label: str
    scope_site: str
    related_md_rel_paths: list[str]
    fts_query: str
    user_sub_prompt: str
    max_citations: int = 8
    repo_names: list[str] = field(default_factory=list)


@dataclass
class Plan:
    strategy: CopilotStrategy
    subtasks: list[Subtask]
    truncated: bool = False
    truncation_note: str = ""


def _map_batch_size() -> int:
    raw = (os.environ.get("LENSES_COPILOT_MAP_BATCH_SIZE") or "").strip()
    if raw.isdigit():
        v = int(raw)
        if 1 <= v <= 8:
            return v
    return 1


def _max_subtasks() -> int:
    raw = (os.environ.get("LENSES_COPILOT_MAP_MAX_SUBTASKS") or "").strip()
    if raw.isdigit():
        v = int(raw)
        if 4 <= v <= 60:
            return v
    return 30


def _repo_related_md(workspace_root: Path, repo_name: str) -> list[str]:
    rel = f"{repo_name}/forge/charge.md".replace("\\", "/")
    candidate = (workspace_root / rel).resolve()
    wr = workspace_root.resolve()
    try:
        candidate.relative_to(wr)
    except ValueError:
        return []
    if candidate.is_file() and candidate.suffix.lower() == ".md":
        return [rel]
    return []


def _scan_git_repos(scan_state: dict[str, Any]) -> list[str]:
    children = scan_state.get("children") if isinstance(scan_state, dict) else None
    if not isinstance(children, list):
        return []
    names: list[str] = []
    for ch in children:
        if not isinstance(ch, dict) or not ch.get("is_git"):
            continue
        name = str(ch.get("name") or "").strip()
        if name:
            names.append(name)
    return sorted(names, key=lambda x: x.lower())


def _scan_all_children(scan_state: dict[str, Any]) -> list[str]:
    children = scan_state.get("children") if isinstance(scan_state, dict) else None
    if not isinstance(children, list):
        return []
    names: list[str] = []
    for ch in children:
        if not isinstance(ch, dict):
            continue
        name = str(ch.get("name") or "").strip()
        if name:
            names.append(name)
    return sorted(names, key=lambda x: x.lower())


def _fts_query_for_repo(user_message: str, repo_name: str) -> str:
    stop = frozenset(
        "the a an and or for to of in on is are was were be been being it this that these those "
        "with from at by as not no yes how what when where why who which each every all project "
        "repo repository workspace portfolio describe summarize sentence line brief folder".split()
    )
    parts = [
        p
        for p in re.sub(r"[^\w\s-]", " ", user_message or "").split()
        if len(p) > 2 and p.lower() not in stop
    ]
    tail = " ".join(parts[:6])
    base = f"{repo_name} readme forge charge project"
    return f"{base} {tail}".strip()[:220]


def _map_sub_prompt(user_message: str, labels: list[str]) -> str:
    names = ", ".join(labels)
    return (
        f"For workspace {'entry' if len(labels) == 1 else 'entries'}: {names}. "
        f"Using ONLY the numbered context below, answer this part of the operator question: "
        f"{user_message.strip()}\n"
        "Reply with one concise line per entry (prefix with the entry name). "
        "If context is insufficient for an entry, say so explicitly. Cite [n] for each claim."
    )


def _chunk_list(items: list[str], size: int) -> list[list[str]]:
    if size <= 1:
        return [[x] for x in items]
    out: list[list[str]] = []
    for i in range(0, len(items), size):
        out.append(items[i : i + size])
    return out


def build_portfolio_plan(
    *,
    workspace_root: Path,
    user_message: str,
    scan_state: dict[str, Any],
    include_folders: bool = False,
) -> Plan:
    """One subtask per repo (or batched batch_size), scoped FTS + charge.md when present."""
    if include_folders:
        targets = _scan_all_children(scan_state)
    else:
        targets = _scan_git_repos(scan_state)
    batch = _map_batch_size()
    max_st = _max_subtasks()
    truncated = False
    note = ""
    chunks = _chunk_list(targets, batch)
    if len(chunks) > max_st:
        truncated = True
        note = f"Plan capped at {max_st} batches ({len(targets)} entries in workspace)."
        chunks = chunks[:max_st]

    subtasks: list[Subtask] = []
    for idx, group in enumerate(chunks):
        label = group[0] if len(group) == 1 else ", ".join(group[:3]) + ("…" if len(group) > 3 else "")
        scope = group[0] if len(group) == 1 else ""
        md_paths: list[str] = []
        for repo in group:
            md_paths.extend(_repo_related_md(workspace_root, repo))
        fts = _fts_query_for_repo(user_message, group[0])
        if len(group) > 1:
            fts = " ".join(f"{g} readme" for g in group[:4])[:220]
        subtasks.append(
            Subtask(
                subtask_id=f"portfolio-{idx + 1}",
                label=label,
                scope_site=scope,
                related_md_rel_paths=md_paths[:8],
                fts_query=fts,
                user_sub_prompt=_map_sub_prompt(user_message, group),
                max_citations=8,
                repo_names=list(group),
            )
        )
    return Plan(strategy="portfolio_map_reduce", subtasks=subtasks, truncated=truncated, truncation_note=note)


def _site_from_search_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    path = urlparse(u).path or u
    parts = [unquote(p) for p in path.split("/") if p]
    for i, p in enumerate(parts):
        if p == "local-site" and i + 1 < len(parts):
            return parts[i + 1]
    return ""


def build_search_plan(
    *,
    workspace_root: Path,
    user_message: str,
    scan_state: dict[str, Any],
) -> Plan:
    """Subtasks from top FTS hits grouped by local-site repo."""
    sites: list[str] = []
    try:
        conn = search_db.connect(workspace_root)
        try:
            q = (user_message or "").strip()[:120] or "workspace"
            res = search_db.search(conn, q, limit=40, offset=0)
            seen: set[str] = set()
            for h in res.get("hits") or []:
                if not isinstance(h, dict):
                    continue
                site = _site_from_search_url(str(h.get("url") or ""))
                if site and site not in seen:
                    seen.add(site)
                    sites.append(site)
        finally:
            conn.close()
    except OSError:
        sites = []

    if not sites:
        return build_portfolio_plan(
            workspace_root=workspace_root,
            user_message=user_message,
            scan_state=scan_state,
        )

    max_st = _max_subtasks()
    truncated = len(sites) > max_st
    if truncated:
        sites = sites[:max_st]

    subtasks: list[Subtask] = []
    for idx, site in enumerate(sites):
        md_paths = _repo_related_md(workspace_root, site)
        subtasks.append(
            Subtask(
                subtask_id=f"search-{idx + 1}",
                label=site,
                scope_site=site,
                related_md_rel_paths=md_paths,
                fts_query=_fts_query_for_repo(user_message, site),
                user_sub_prompt=_map_sub_prompt(user_message, [site]),
                max_citations=8,
                repo_names=[site],
            )
        )
    note = f"Grouped {len(sites)} sites from search hits." if sites else ""
    if truncated:
        note = f"Search plan capped at {max_st} sites. " + note
    return Plan(
        strategy="search_map_reduce",
        subtasks=subtasks,
        truncated=truncated,
        truncation_note=note.strip(),
    )


def build_plan(
    *,
    strategy: CopilotStrategy,
    workspace_root: Path,
    user_message: str,
    scan_state: dict[str, Any],
    studio_route: str = "",
    page_context_summary: str | None = None,
) -> Plan | None:
    if strategy == "portfolio_map_reduce":
        include_folders = bool(
            re.search(r"\bfolder(s)?\b", user_message or "", re.I)
            or re.search(r"\beach project\b", user_message or "", re.I)
        )
        return build_portfolio_plan(
            workspace_root=workspace_root,
            user_message=user_message,
            scan_state=scan_state,
            include_folders=include_folders,
        )
    if strategy == "search_map_reduce":
        return build_search_plan(
            workspace_root=workspace_root,
            user_message=user_message,
            scan_state=scan_state,
        )
    return None
