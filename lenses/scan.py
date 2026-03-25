"""Scan workspace root: git children, toolset, firebase sites, WBS files."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class GitInfo:
    is_repo: bool = False
    top_level: str = ""
    branch: str = ""
    dirty: bool = False
    origin_url: str = ""


@dataclass
class ChildEntry:
    name: str
    path: str
    is_git: bool
    git: dict[str, Any] = field(default_factory=dict)


@dataclass
class WbsEntry:
    repo_hint: str
    rel_path: str
    kind: str


def _run_git(cwd: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode != 0:
            return None
        return r.stdout.strip() or ""
    except (OSError, subprocess.TimeoutExpired):
        return None


def git_info(path: Path) -> GitInfo:
    g = GitInfo()
    inside = _run_git(path, "rev-parse", "--is-inside-work-tree")
    if inside != "true":
        return g
    g.is_repo = True
    tl = _run_git(path, "rev-parse", "--show-toplevel")
    g.top_level = tl or str(path.resolve())
    g.branch = _run_git(path, "branch", "--show-current") or ""
    st = _run_git(path, "status", "--porcelain")
    g.dirty = bool(st)
    g.origin_url = _run_git(path, "remote", "get-url", "origin") or ""
    return g


def resolve_workspace_root(
    lenses_repo_root: Path,
    cli_root: Path | None,
    env_root: str | None,
) -> Path:
    if cli_root is not None:
        return cli_root.resolve()
    if env_root:
        p = Path(env_root).expanduser().resolve()
        if p.is_dir():
            return p
    # Standalone: parent of lenses repo (sibling workspace)
    return lenses_repo_root.resolve().parent


def scan_workspace(
    workspace_root: Path,
    lenses_repo_root: Path,
    registry: dict[str, Any],
) -> dict[str, Any]:
    root = workspace_root.resolve()
    ignore = set(registry.get("ignore_paths") or [])

    children: list[ChildEntry] = []
    if root.is_dir():
        for p in sorted(root.iterdir(), key=lambda x: x.name.lower()):
            if not p.is_dir() or p.name.startswith("."):
                continue
            if p.name in ignore:
                continue
            gi = git_info(p)
            children.append(
                ChildEntry(
                    name=p.name,
                    path=str(p),
                    is_git=gi.is_repo,
                    git=asdict(gi) if gi.is_repo else {},
                )
            )

    toolset_scripts: list[str] = []
    for pattern in ("*.sh",):
        for f in sorted(root.glob(pattern)):
            if f.is_file():
                toolset_scripts.append(f.name)
    cursor_dir = root / ".cursor"

    websites: list[dict[str, Any]] = []
    for c in children:
        cp = root / c.name
        fb = cp / "firebase.json"
        if fb.is_file():
            websites.append({"name": c.name, "path": str(cp), "firebase_json": str(fb)})

    wbs_list: list[WbsEntry] = []
    for md in root.rglob("docs/requirements/WBS.md"):
        try:
            md.relative_to(root)
        except ValueError:
            continue
        if not md.is_file():
            continue
        rel = md.relative_to(root)
        hint = rel.parts[0] if rel.parts else ""
        wbs_list.append(WbsEntry(repo_hint=hint, rel_path=str(rel).replace("\\", "/"), kind="md"))
    for csv in root.rglob("docs/requirements/WBS.csv"):
        try:
            csv.relative_to(root)
        except ValueError:
            continue
        if not csv.is_file():
            continue
        rel = csv.relative_to(root)
        hint = rel.parts[0] if rel.parts else ""
        wbs_list.append(WbsEntry(repo_hint=hint, rel_path=str(rel).replace("\\", "/"), kind="csv"))

    wbs_list.sort(key=lambda w: w.rel_path)

    return {
        "workspace_root": str(root),
        "lenses_repo_root": str(lenses_repo_root.resolve()),
        "resolved_at": datetime.now(timezone.utc).isoformat(),
        "children": [asdict(c) for c in children],
        "toolset": {
            "root_scripts": toolset_scripts,
            "cursor_dir": str(cursor_dir) if cursor_dir.is_dir() else "",
        },
        "websites": websites,
        "wbs": [asdict(w) for w in wbs_list],
    }


def workspace_state_json(state: dict[str, Any]) -> str:
    return json.dumps(state, indent=2, sort_keys=True)
