#!/usr/bin/env python3
"""Fail if Markdown under the public ``docs/nav.yml`` profile links outside the public allowlist."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_NAV_YML = REPO_ROOT / "docs" / "nav.yml"
_SCRIPTS_LIB = Path(__file__).resolve().parent
if str(_SCRIPTS_LIB) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_LIB))

from lib.docs_nav_public import (  # noqa: E402
    assert_nav_markdown_entries_exist,
    effective_public_markdown_paths,
    split_yaml_frontmatter_strings,
)

_REL_MD_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(\s*([^)]+?)\s*\)")

_DISALLOW_REL_PREFIXES: tuple[tuple[str, str], ...] = (
    ("docs/maintainer/", "maintainer-only tree"),
    ("docs/strategy/", "strategy drafts"),
    ("docs/plans/", "plans drafts"),
    ("lenses/website/", "raw internal route narrative"),
    ("docs/schemas/README.md", "schemas README — use public builders schemas page"),
    ("docs/examples/README.md", "examples README — summarize in handbook or GitHub blob"),
)


def _blocked_rel(rel_posix: str) -> str | None:
    rp = rel_posix.replace("\\", "/")
    if rp.startswith("docs/adr-"):
        return "ADR Markdown"
    for pref, label in _DISALLOW_REL_PREFIXES:
        if rp == pref.rstrip("/") or rp.startswith(pref):
            return label
    if rp.startswith("docs/website/"):
        return "docs website mirror (maintainer-heavy)"
    return None


def _extract_md_href(raw_href: str) -> str | None:
    h = raw_href.strip().split()[0].strip('"').strip("'")
    if not h or h.startswith("#"):
        return None
    lc = h.lower()
    if lc.startswith(("http://", "https://", "mailto:", "ftp://")):
        return None
    path_only = h.split("#", 1)[0].strip()
    return path_only or None


def scan_sources(*, repo_root: Path, allow_rels: set[str], sources: list[Path]) -> list[tuple[str, str, str, str]]:
    violations: list[tuple[str, str, str, str]] = []
    for src in sources:
        text = src.read_text(encoding="utf-8")
        _, body = split_yaml_frontmatter_strings(text)
        md_rel_src = str(src.relative_to(repo_root)).replace("\\", "/")
        for m in _REL_MD_LINK.finditer(body):
            path_part_i = _extract_md_href(m.group(1))
            if path_part_i is None:
                continue
            if not path_part_i.lower().endswith(".md"):
                continue
            target_abs = (src.parent / path_part_i).resolve()
            try:
                rel_pos = str(target_abs.relative_to(repo_root)).replace("\\", "/")
            except ValueError:
                violations.append((md_rel_src, path_part_i, path_part_i, "escapes repo root"))
                continue
            if not target_abs.is_file():
                violations.append((md_rel_src, path_part_i, rel_pos, "broken relative target"))
                continue
            block = _blocked_rel(rel_pos)
            if block:
                violations.append((md_rel_src, path_part_i, rel_pos, block))
                continue
            if rel_pos not in allow_rels:
                violations.append((md_rel_src, path_part_i, rel_pos, "Markdown not in public nav.yml allowlist"))
    return violations


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="Print violations JSON to stdout.")
    args = ap.parse_args()
    try:
        assert_nav_markdown_entries_exist(REPO_ROOT, nav_yml=_NAV_YML)
    except RuntimeError as exc:
        print(f"check-public-doc-links: {exc}", file=sys.stderr)
        return 1
    sources = effective_public_markdown_paths(REPO_ROOT, nav_yml=_NAV_YML)
    allow_rels = {str(p.relative_to(REPO_ROOT)).replace("\\", "/") for p in sources}
    viol = scan_sources(repo_root=REPO_ROOT, allow_rels=allow_rels, sources=sources)

    payload = [{"source": a, "href": b, "resolved": c, "reason": d} for a, b, c, d in viol]
    if args.json:
        print(json.dumps({"violations": payload}, indent=2))
    if viol:
        for src, href, resolved, why in viol:
            print(f"{src} -> {href} -> {resolved} :: {why}", file=sys.stderr)
        return 1
    print("check-public-doc-links: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
