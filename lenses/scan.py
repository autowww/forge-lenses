"""Scan workspace root: git children, toolset, firebase sites, WBS files."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lenses.site_index import build_html_page_index


@dataclass
class GitInfo:
    is_repo: bool = False
    top_level: str = ""
    branch: str = ""
    dirty: bool = False
    origin_url: str = ""
    head_short: str = ""
    head_full: str = ""
    commit_unix: int = 0
    commit_subject: str = ""
    commit_date: str = ""


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


def git_info(path: Path, *, extended: bool = False) -> GitInfo:
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
    if extended:
        g.head_full = _run_git(path, "rev-parse", "HEAD") or ""
        g.head_short = _run_git(path, "rev-parse", "--short=12", "HEAD") or ""
        log_line = _run_git(path, "log", "-1", "--format=%ct%x00%s%x00%cI")
        if log_line and log_line.count("\x00") >= 2:
            ct, _, rest = log_line.partition("\x00")
            subj, _, cdate = rest.partition("\x00")
            try:
                g.commit_unix = int(ct.strip())
            except ValueError:
                g.commit_unix = 0
            g.commit_subject = subj.strip()
            g.commit_date = cdate.strip()
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


def parse_firebase_hosting(fb_path: Path) -> tuple[str, str]:
    try:
        raw = json.loads(fb_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "website", ""
    hosting = raw.get("hosting")
    if isinstance(hosting, list):
        hosting = hosting[0] if hosting else {}
    if not isinstance(hosting, dict):
        return "website", ""
    pub = str(hosting.get("public") or "website")
    site = str(hosting.get("site") or "")
    return pub, site


def shell_script_leading_comment_lines(path: Path) -> list[str]:
    """Lines from the leading # block after an optional shebang (no # prefix)."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = raw.splitlines()
    i = 0
    if lines and lines[0].lstrip().startswith("#!"):
        i = 1
    out: list[str] = []
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        if stripped.startswith("#"):
            out.append(stripped[1:].lstrip())
            i += 1
            continue
        if not stripped:
            i += 1
            continue
        break
    return out


def shell_script_blurb(path: Path, max_len: int = 220) -> str:
    """Single-line summary from shell comment header for toolset cards."""
    one = " ".join(" ".join(shell_script_leading_comment_lines(path)).split())
    if len(one) > max_len:
        return one[: max_len - 1].rstrip() + "…"
    return one


def shell_script_comment_detail(path: Path, max_len: int = 2000) -> str:
    """Multi-line comment header for toolset run page (capped)."""
    lines = shell_script_leading_comment_lines(path)
    if not lines:
        return ""
    text = "\n".join(lines).strip()
    if len(text) > max_len:
        return text[: max_len - 1].rstrip() + "…"
    return text


def _suggested_commands(name: str, child_path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    g = child_path / "generator"
    if (g / "build-site.py").is_file():
        out["build"] = f"cd {name} && python3 generator/build-site.py"
    elif (g / "build-handbook.py").is_file():
        out["build"] = (
            f"cd {name} && python3 generator/build-handbook.py --all && "
            f"python3 generator/inject-portal-nav.py"
        )
    out["deploy"] = f"cd {name} && firebase deploy --only hosting"
    return out


def resolve_workspace_child_dir(
    workspace_root: Path,
    name: str,
    registry: dict[str, Any] | None = None,
) -> Path | None:
    """Return resolved child path if *name* is a direct non-hidden directory under workspace."""
    if not name or "/" in name or "\\" in name or name.startswith("."):
        return None
    if registry and name in set(registry.get("ignore_paths") or []):
        return None
    root = workspace_root.resolve()
    candidate = (root / name).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if not candidate.is_dir() or candidate.name != name:
        return None
    return candidate


def scan_workspace(
    workspace_root: Path,
    lenses_repo_root: Path,
    registry: dict[str, Any],
    *,
    git_extended: bool = False,
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
            gi = git_info(p, extended=git_extended)
            git_payload: dict[str, Any] = {}
            if gi.is_repo:
                git_payload = asdict(gi)
                git_payload.pop("is_repo", None)
            children.append(
                ChildEntry(
                    name=p.name,
                    path=str(p),
                    is_git=gi.is_repo,
                    git=git_payload,
                )
            )

    toolset_scripts: list[str] = []
    script_cards: list[dict[str, str]] = []
    for f in sorted(root.glob("*.sh")):
        if f.is_file():
            toolset_scripts.append(f.name)
            script_cards.append({"name": f.name, "blurb": shell_script_blurb(f)})
    cursor_dir = root / ".cursor"

    websites: list[dict[str, Any]] = []
    for c in children:
        cp = root / c.name
        fb = cp / "firebase.json"
        if fb.is_file():
            pub, fb_site = parse_firebase_hosting(fb)
            public_path = cp / pub
            idx = build_html_page_index(public_path)
            sugg = _suggested_commands(c.name, cp)
            websites.append(
                {
                    "name": c.name,
                    "path": str(cp),
                    "firebase_json": str(fb),
                    "hosting_public": pub,
                    "firebase_site_id": fb_site,
                    "preview_base": f"/local-site/{c.name}/",
                    "pages": idx["pages"],
                    "html_total": idx["html_total"],
                    "html_indexed": idx["html_indexed"],
                    "index_html_mtime": idx["index_html_mtime"],
                    "suggested_commands": sugg,
                }
            )

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
            "script_cards": script_cards,
            "cursor_dir": str(cursor_dir) if cursor_dir.is_dir() else "",
        },
        "websites": websites,
        "wbs": [asdict(w) for w in wbs_list],
    }


def workspace_state_json(state: dict[str, Any]) -> str:
    return json.dumps(state, indent=2, sort_keys=True)
