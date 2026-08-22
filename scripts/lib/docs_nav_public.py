"""Resolve effective public handbook Markdown paths from ``docs/nav.yml``.

Rules match ``scripts/check-public-doc-links.py`` and inventory exports:

- Every ``path`` ending in ``.md`` is a candidate.
- Pages with YAML frontmatter ``public_publish: false`` are suppressed.

Consumer scripts should import from here instead of duplicating nav parsing."""

from __future__ import annotations

import re
from pathlib import Path

import yaml


def nav_yml_markdown_sources(nav_yml_path: Path) -> list[str]:
    """Flatten ``sections[].entries[].path`` to POSIX strings (nav.yml only)."""
    raw = yaml.safe_load(nav_yml_path.read_text(encoding="utf-8"))
    out: list[str] = []
    for sec in raw.get("sections", []) or []:
        for ent in sec.get("entries", []) or []:
            if isinstance(ent, str):
                out.append(ent.replace("\\", "/"))
            else:
                p = ent.get("path") or ent.get("source")
                if p:
                    out.append(str(p).replace("\\", "/"))
    return out


def split_yaml_frontmatter_strings(text: str) -> tuple[dict[str, str], str]:
    """Lightweight frontmatter for ``public_publish`` checks (string values only)."""
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}, text
    block = yaml.safe_load(m.group(1))
    fm: dict[str, str] = {}
    if isinstance(block, dict):
        for k, v in block.items():
            if v is None:
                continue
            fm[str(k)] = str(v)
    return fm, text[m.end() :]


def _public_publish_suppressed(fm: dict[str, str]) -> bool:
    v = fm.get("public_publish", "").strip().lower()
    return v in ("false", "0", "no", "off")


def effective_public_markdown_paths(
    repo_root: Path, *, nav_yml: Path | None = None
) -> list[Path]:
    """Absolute paths to nav-listed Markdown that ships in ``public`` profile."""
    root = repo_root.resolve()
    nav_path = nav_yml or (root / "docs" / "nav.yml")
    resolved: list[Path] = []
    for rel in nav_yml_markdown_sources(nav_path):
        if not rel.endswith(".md"):
            continue
        p = root / rel
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        fm, _ = split_yaml_frontmatter_strings(text)
        if _public_publish_suppressed(fm):
            continue
        resolved.append(p.resolve())
    return resolved


def effective_public_markdown_rel_posix(
    repo_root: Path, *, nav_yml: Path | None = None
) -> set[str]:
    """Set of repo-relative POSIX paths for allowlists."""
    root = repo_root.resolve()
    return {p.relative_to(root).as_posix() for p in effective_public_markdown_paths(root, nav_yml=nav_yml)}


def assert_nav_markdown_entries_exist(repo_root: Path, *, nav_yml: Path | None = None) -> None:
    """Raise ``RuntimeError`` when nav.yml lists a missing ``*.md`` path."""
    root = repo_root.resolve()
    nav_path = nav_yml or (root / "docs" / "nav.yml")
    for rel in nav_yml_markdown_sources(nav_path):
        if not rel.endswith(".md"):
            continue
        if not (root / rel).is_file():
            raise RuntimeError(f"nav.yml lists missing path: {rel}")
