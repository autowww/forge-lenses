#!/usr/bin/env python3
"""Ban Mermaid under ``docs/`` and validate Kitchen Sink diagram fence hygiene.

- Fails on `` ```mermaid `` fences in forge-lenses/docs/**/*.md
- For ``blueprint-diagram*`` / legacy ``ks-diagram*`` fences: require ``alt:`` or ``decorative: true``
- Validates ``key:`` against Kitchen Sink catalog keys when present

Usage:

    python3 scripts/check-docs-diagrams.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_ROOT = REPO_ROOT / "docs"
KS_CATALOG = REPO_ROOT / "kitchensink" / "js" / "ks-diagram-catalog.js"

_KEY_LINE = re.compile(r"(?m)^\s*key:\s*(\S+)")
_DECORATIVE_LINE = re.compile(r"(?m)^\s*decorative:\s*true\s*$", re.IGNORECASE)
_ALT_LINE = re.compile(r"(?m)^\s*alt:\s*\S")


def _catalog_keys() -> frozenset[str]:
    if not KS_CATALOG.is_file():
        print(f"check-docs-diagrams: missing catalog {KS_CATALOG}", file=sys.stderr)
        sys.exit(2)
    text = KS_CATALOG.read_text(encoding="utf-8")
    keys = set(re.findall(r"^ {4}([a-z][a-z0-9_]*):\s*\{", text, flags=re.MULTILINE))
    return frozenset(keys)


def _iter_markdown_files() -> list[Path]:
    return sorted(DOCS_ROOT.rglob("*.md"))


def _split_fences(md: str) -> list[tuple[str, str]]:
    """Return list of (lang, body) for fenced blocks."""
    lines = md.splitlines(keepends=True)
    out: list[tuple[str, str]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^```\s*(\S*)\s*$", line)
        if not m:
            i += 1
            continue
        lang = (m.group(1) or "").strip().lower()
        i += 1
        body_chunks: list[str] = []
        while i < len(lines) and not lines[i].strip().startswith("```"):
            body_chunks.append(lines[i])
            i += 1
        if i < len(lines) and lines[i].strip().startswith("```"):
            i += 1
        out.append((lang, "".join(body_chunks)))
    return out


def _scan_file(path: Path, catalog: frozenset[str]) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(REPO_ROOT)
    for lang, body in _split_fences(text):
        if lang == "mermaid":
            errors.append(f"{rel}: forbidden ```mermaid fenced block")
            continue
        if not lang.startswith("blueprint-diagram") and not lang.startswith("ks-diagram"):
            continue
        if _DECORATIVE_LINE.search(body):
            continue
        if not _ALT_LINE.search(body):
            errors.append(f"{rel}: {lang} fence missing alt: (or decorative: true)")
        km = _KEY_LINE.search(body)
        if km:
            key = km.group(1).strip().strip('"').strip("'")
            if key not in catalog:
                errors.append(f"{rel}: unknown diagram key {key!r} (not in ks-diagram-catalog.js)")
        else:
            first_line = next((ln for ln in body.splitlines() if ln.strip()), "")
            token = first_line.strip().split()[0] if first_line.strip() else ""
            if re.match(r"^[a-z][a-z0-9_]*$", token) and token not in catalog:
                errors.append(f"{rel}: shorthand diagram key {token!r} not in catalog")
    return errors


def main() -> int:
    if not DOCS_ROOT.is_dir():
        print("check-docs-diagrams: docs/ missing", file=sys.stderr)
        return 1
    catalog = _catalog_keys()
    problems: list[str] = []
    for md in _iter_markdown_files():
        problems.extend(_scan_file(md, catalog))
    if problems:
        for p in problems:
            print(p, file=sys.stderr)
        return 1
    print("check-docs-diagrams: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
