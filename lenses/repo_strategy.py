"""Repo layout and branching data for /projects/<name>/strategy (no external diagram DSLs)."""

from __future__ import annotations

import configparser
import html
import re
import subprocess
from pathlib import Path
from typing import Any

SUBMODULE_STATUS_TIMEOUT_SEC = 8.0
SUBMODULE_STATUS_MAX_LINES = 200


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def _run_git(cwd: Path, *args: str, timeout: float = 12.0) -> str | None:
    try:
        r = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if r.returncode != 0:
            return None
        return (r.stdout or "").strip() or ""
    except (OSError, subprocess.TimeoutExpired):
        return None


def parse_gitmodules(repo_path: Path) -> list[dict[str, str]]:
    """Entries from .gitmodules: path, url, optional branch (submodule key name)."""
    gm = repo_path / ".gitmodules"
    if not gm.is_file():
        return []
    try:
        text = gm.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    cp = configparser.ConfigParser(interpolation=None)
    try:
        cp.read_string(text)
    except configparser.Error:
        return _parse_gitmodules_fallback(text)
    out: list[dict[str, str]] = []
    for sec in cp.sections():
        if not sec.strip().lower().startswith("submodule"):
            continue
        path = (cp.get(sec, "path", fallback="") or "").strip()
        url = (cp.get(sec, "url", fallback="") or "").strip()
        branch = (cp.get(sec, "branch", fallback="") or "").strip()
        m = re.search(r"submodule\s+\"([^\"]+)\"", sec, re.I)
        key_name = m.group(1).strip() if m else sec
        if path or url:
            out.append(
                {
                    "submodule_key": key_name,
                    "path": path,
                    "url": url,
                    "branch": branch,
                }
            )
    return out


def _parse_gitmodules_fallback(text: str) -> list[dict[str, str]]:
    """Loose parse when ConfigParser fails on unusual .gitmodules."""
    entries: list[dict[str, str]] = []
    cur: dict[str, str] | None = None
    for line in text.splitlines():
        msec = re.match(r'^\s*\[submodule\s+"([^"]+)"\s*\]\s*$', line, re.I)
        if msec:
            cur = {"submodule_key": msec.group(1), "path": "", "url": "", "branch": ""}
            entries.append(cur)
            continue
        if cur is None:
            continue
        mk = re.match(r"^\s*(\w+)\s*=\s*(.*)$", line)
        if not mk:
            continue
        k, v = mk.group(1).lower(), mk.group(2).strip()
        if k == "path":
            cur["path"] = v
        elif k == "url":
            cur["url"] = v
        elif k == "branch":
            cur["branch"] = v
    return entries


def git_submodule_status_text(repo_path: Path) -> tuple[str, bool, str | None]:
    """
    Run `git submodule status` in repo_path.
    Returns (display_text, truncated, error_message_or_none).
    """
    try:
        r = subprocess.run(
            ["git", "-C", str(repo_path), "submodule", "status"],
            capture_output=True,
            text=True,
            timeout=SUBMODULE_STATUS_TIMEOUT_SEC,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return ("", False, str(e))
    raw = (r.stdout or "") + (r.stderr or "")
    lines = raw.splitlines()
    truncated = len(lines) > SUBMODULE_STATUS_MAX_LINES
    lines = lines[:SUBMODULE_STATUS_MAX_LINES]
    text = "\n".join(lines).strip()
    if r.returncode != 0 and not text:
        err = (r.stderr or r.stdout or "git submodule status failed").strip()
        return ("", False, err[:500])
    return (text, truncated, None)


def remote_default_branch(repo_path: Path) -> str:
    """Best-effort: tracked remote default (e.g. main). Empty if unknown."""
    out = _run_git(repo_path, "rev-parse", "--abbrev-ref", "origin/HEAD")
    if not out:
        return ""
    if out == "HEAD":
        return ""
    if out.startswith("origin/"):
        return out[len("origin/") :]
    return out


def workspace_child_names(state: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for c in state.get("children") or []:
        if isinstance(c, dict):
            n = str(c.get("name", "")).strip()
            if n:
                names.add(n)
    return names


def sibling_workspace_hint(
    submodule_path: str, workspace_names: set[str], project_name: str
) -> str | None:
    """If the submodule directory name matches another workspace top-level folder, return a note."""
    seg = submodule_path.replace("\\", "/").rstrip("/").split("/")[-1]
    if not seg or seg == project_name:
        return None
    if seg in workspace_names:
        return (
            f"This folder name matches workspace sibling <code>{_esc(seg)}</code> "
            "(edit the standalone clone; submodule copy is read-only in consumers)."
        )
    return None


def svg_submodule_layout_svg(
    project_label: str, submodule_paths: list[str], *, width: int = 520
) -> str:
    """Simple inline SVG: root box → arrows → one box per submodule path."""
    paths = [p.replace("\\", "/") for p in submodule_paths if p.strip()]
    if not paths:
        return ""
    n = min(len(paths), 12)
    paths = paths[:n]
    h = 120
    root_y = 18
    row_y = 78
    margin = 16
    usable = width - 2 * margin
    slot = usable / max(n, 1)
    box_w = min(100.0, slot * 0.85)
    pl_short = project_label[:28] + ("…" if len(project_label) > 28 else "")

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {h}" '
        f'role="img" aria-label="Submodule layout" style="width:100%;max-width:{width}px;height:auto">',
        '<rect width="100%" height="100%" fill="transparent"/>',
        f'<rect x="{(width - 200) / 2:.1f}" y="{root_y:.1f}" width="200" height="28" rx="4" '
        f'fill="rgba(6,182,212,0.15)" stroke="rgba(6,182,212,0.5)"/>',
        f'<text x="{width / 2:.1f}" y="{root_y + 19:.1f}" text-anchor="middle" '
        f'fill="var(--bs-body-color,#e2e8f0)" font-size="11" font-family="system-ui,sans-serif">'
        f"{_esc(pl_short)}</text>",
    ]
    cx = width / 2
    root_bottom = root_y + 28
    mid_y = (root_bottom + row_y) / 2
    parts.append(
        f'<line x1="{cx:.1f}" y1="{root_bottom:.1f}" x2="{cx:.1f}" y2="{mid_y:.1f}" '
        f'stroke="rgba(148,163,184,0.6)" stroke-width="1.2"/>'
    )
    centers: list[float] = []
    for i in range(n):
        cx_i = margin + slot * (i + 0.5)
        centers.append(cx_i)
    for i in range(n - 1):
        parts.append(
            f'<line x1="{centers[i]:.1f}" y1="{mid_y:.1f}" x2="{centers[i + 1]:.1f}" '
            f'y2="{mid_y:.1f}" stroke="rgba(148,163,184,0.35)" stroke-width="1"/>'
        )
    for cx_i in centers:
        parts.append(
            f'<line x1="{cx_i:.1f}" y1="{mid_y:.1f}" x2="{cx_i:.1f}" y2="{row_y:.1f}" '
            f'stroke="rgba(148,163,184,0.6)" stroke-width="1.2"/>'
        )
    for i, pth in enumerate(paths):
        cx_i = centers[i]
        label = pth.split("/")[-1][:18] + ("…" if len(pth.split("/")[-1]) > 18 else "")
        bx = cx_i - box_w / 2
        parts.append(
            f'<rect x="{bx:.1f}" y="{row_y:.1f}" width="{box_w:.1f}" height="32" rx="4" '
            f'fill="rgba(30,41,59,0.9)" stroke="rgba(148,163,184,0.45)"/>'
        )
        parts.append(
            f'<text x="{cx_i:.1f}" y="{row_y + 20:.1f}" text-anchor="middle" '
            f'fill="var(--bs-secondary-color,#94a3b8)" font-size="10" font-family="system-ui,sans-serif">'
            f"{_esc(label)}</text>"
        )
    parts.append("</svg>")
    return "\n".join(parts)


DEFAULT_MAINTENANCE_BULLETS = [
    "Standalone repos are the source of truth; nested submodules under consumers are read-only copies.",
    "One commit per repository when changing that repo; bump submodule pointers in consumers separately.",
    "After changing shared design system code, update the kitchensink submodule in each consumer and rebuild.",
]


def strategy_registry_entry(
    registry: dict[str, Any], project_name: str
) -> dict[str, Any]:
    raw = registry.get("project_strategy")
    if not isinstance(raw, dict):
        return {}
    ent = raw.get(project_name)
    return ent if isinstance(ent, dict) else {}


def load_optional_strategy_markdown(repo_path: Path) -> str | None:
    """If LENSES-REPO-STRATEGY.md exists at repo root, return raw text."""
    for name in ("LENSES-REPO-STRATEGY.md", "LENSES-REPO-STRATEGY.MD"):
        p = repo_path / name
        if p.is_file():
            try:
                return p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return None
    return None


def markdown_to_html_fragment(text: str) -> str:
    try:
        import markdown  # type: ignore[import-untyped]
    except ImportError:
        return f'<pre class="small mb-0">{_esc(text)}</pre>'
    out = markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "nl2br"],
        output_format="html5",
    )
    if not isinstance(out, str):
        return f'<pre class="small mb-0">{_esc(text)}</pre>'
    return out
