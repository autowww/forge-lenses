"""Dual wiki on the go — parse proposal surfaces and compare handbook freshness."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_DUAL_WIKI_HEADING_RE = re.compile(r"^##\s+Dual\s+wiki\s*$", re.I | re.M)
_TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")


def _split_table_row(line: str) -> list[str]:
    parts = [c.strip() for c in line.strip().strip("|").split("|")]
    return parts


def parse_dual_wiki_surfaces(
    proposal_md: str,
    *,
    repo_hint: str = "",
) -> list[dict[str, str]]:
    """Return declared wiki sides from ``## Dual wiki`` table rows.

    Each side: ``in_repo``, ``handbook_shell`` (``bpw`` | ``flsw`` | ``forgesdlc`` | ``none``), ``notes``.
    Empty or missing section → defaults by repo kind.
    """
    sides: list[dict[str, str]] = []
    m = _DUAL_WIKI_HEADING_RE.search(proposal_md or "")
    if m:
        tail = proposal_md[m.end() :]
        in_table = False
        headers: list[str] = []
        for line in tail.splitlines():
            if line.startswith("## "):
                break
            if "|" not in line:
                if in_table:
                    break
                continue
            cells = _split_table_row(line)
            if not cells or all(re.match(r"^[-:]+$", c) for c in cells):
                in_table = True
                continue
            if not in_table:
                headers = [c.lower() for c in cells]
                in_table = True
                continue
            row = {headers[i] if i < len(headers) else f"col{i}": cells[i] for i in range(len(cells))}
            in_repo = (
                row.get("in-repo path")
                or row.get("in-repo")
                or row.get("in_repo")
                or row.get("path")
                or ""
            ).strip()
            shell = (
                row.get("handbook shell")
                or row.get("handbook_shell")
                or row.get("shell")
                or row.get("*w")
                or ""
            ).strip().lower()
            notes = (row.get("notes") or row.get("note") or "").strip()
            if in_repo or shell:
                sides.append(
                    {
                        "in_repo": in_repo,
                        "handbook_shell": shell or "none",
                        "notes": notes,
                    }
                )

    if sides:
        return sides

    hint = (repo_hint or "").lower()
    if "lenses" in hint or hint.endswith("/forge-lenses"):
        return [
            {
                "in_repo": "docs/website/ui-map-workflow.md",
                "handbook_shell": "flsw",
                "notes": "default Lenses operator",
            }
        ]
    return [
        {
            "in_repo": "sdlc/methodologies/forge/SPEC-FLOW-BOARD.md",
            "handbook_shell": "bpw",
            "notes": "default methodology",
        }
    ]


def _resolve_workspace_paths(workspace_root: Path) -> dict[str, Path]:
    wr = workspace_root.resolve()
    code = wr
    home = Path.home()
    candidates = {
        "blueprints": [
            code / "blueprints",
            home / "Code" / "blueprints",
            wr / "blueprints",
        ],
        "bpw": [
            code / "blueprints-website",
            home / "Code" / "blueprints-website",
            wr / "blueprints-website",
        ],
        "flsw": [
            code / "forge-lenses-website",
            home / "Code" / "forge-lenses-website",
            wr / "forge-lenses-website",
        ],
        "forgesdlc": [
            code / "forgesdlc",
            home / "Code" / "forgesdlc",
            wr / "forgesdlc",
        ],
    }
    out: dict[str, Path] = {}
    for key, paths in candidates.items():
        for p in paths:
            if p.is_dir():
                out[key] = p.resolve()
                break
    return out


def _shell_website_dir(shell: str, paths: dict[str, Path]) -> Path | None:
    mapping = {
        "bpw": "bpw",
        "blueprints-website": "bpw",
        "flsw": "flsw",
        "forge-lenses-website": "flsw",
        "forgesdlc": "forgesdlc",
    }
    key = mapping.get(shell.lower(), "")
    if not key or key not in paths:
        return None
    website = paths[key] / "website"
    return website if website.is_dir() else None


def _resolve_in_repo_path(in_repo: str, paths: dict[str, Path], repo_base: Path) -> Path | None:
    raw = in_repo.strip().replace("\\", "/")
    if not raw:
        return None
    if raw.startswith("blueprints/"):
        rel = raw[len("blueprints/") :]
        bp = paths.get("blueprints")
        if bp:
            p = bp / rel
            if p.is_file():
                return p
    for base in (repo_base, paths.get("blueprints"), paths.get("bpw")):
        if not base:
            continue
        p = base / raw
        if p.is_file():
            return p
    return None


def _html_candidates_for_source(source: Path, website_dir: Path) -> list[Path]:
    stem = source.stem.replace(".", "-")
    hits = list(website_dir.glob(f"*{stem}*.html"))
    if hits:
        return hits
    # Broader: last path segment only
    tail = source.name.replace(".md", "").replace(".", "-")
    return list(website_dir.glob(f"*{tail}*.html"))


def freshness(
    workspace_root: Path,
    *,
    repo_base: Path,
    proposal_md: str,
    repo_hint: str = "",
) -> dict[str, Any]:
    """Return ``{ stale, sides[], reasons[] }`` for declared dual-wiki surfaces."""
    paths = _resolve_workspace_paths(workspace_root)
    declared = parse_dual_wiki_surfaces(proposal_md, repo_hint=repo_hint)
    sides_out: list[dict[str, Any]] = []
    reasons: list[str] = []
    any_checked = False
    stale = False

    for side in declared:
        in_repo = side.get("in_repo", "")
        shell = (side.get("handbook_shell") or "none").lower()
        entry: dict[str, Any] = {
            "in_repo": in_repo,
            "handbook_shell": shell,
            "notes": side.get("notes", ""),
            "fresh": True,
            "skipped": False,
        }
        if shell in ("none", ""):
            entry["skipped"] = True
            entry["reason"] = "handbook_shell_absent"
            sides_out.append(entry)
            continue

        website = _shell_website_dir(shell, paths)
        if website is None:
            entry["skipped"] = True
            entry["reason"] = "handbook_shell_absent"
            sides_out.append(entry)
            continue

        src = _resolve_in_repo_path(in_repo, paths, repo_base)
        if not src:
            entry["fresh"] = False
            entry["reason"] = "source_missing"
            reasons.append(f"missing source: {in_repo}")
            stale = True
            sides_out.append(entry)
            continue

        any_checked = True
        candidates = _html_candidates_for_source(src, website)
        if not candidates:
            entry["fresh"] = False
            entry["reason"] = "html_missing"
            reasons.append(f"no handbook HTML for {in_repo}")
            stale = True
        else:
            newest = max(candidates, key=lambda p: p.stat().st_mtime)
            if newest.stat().st_mtime < src.stat().st_mtime:
                entry["fresh"] = False
                entry["reason"] = "html_older_than_source"
                reasons.append(f"stale HTML for {in_repo}")
                stale = True
            entry["html_path"] = str(newest)

        sides_out.append(entry)

    if not any_checked and not stale:
        stale = False

    return {"stale": stale, "sides": sides_out, "reasons": reasons}


def dual_wiki_hub_payload(
    workspace_root: Path,
    *,
    repo_base: Path,
    proposal_md: str,
    repo_hint: str = "",
) -> dict[str, Any]:
    """Shape for ``GET /api/epic-hub`` ``dual_wiki`` field."""
    fr = freshness(
        workspace_root,
        repo_base=repo_base,
        proposal_md=proposal_md,
        repo_hint=repo_hint,
    )
    return {
        "stale": bool(fr.get("stale")),
        "sides": fr.get("sides") or [],
        "reasons": (fr.get("reasons") or [])[:8],
        "refresh_allowed": True,
    }
