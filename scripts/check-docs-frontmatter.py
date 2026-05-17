#!/usr/bin/env python3
"""Validate YAML frontmatter on every ``docs/nav.yml`` Markdown page.

Required keys include ``audience``, ``section``, ``learning_level``, ``product_area``,
``status``, ``nav_title``, ``description``, ``tier``, ``handbook_area``, ``public_publish``,
and ``page_type`` (see ``docs/NAV-FRONTMATTER.md``).

Public pages must use ``audience: public`` (never ``maintainer``).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError as e:
    print("check-docs-frontmatter: install PyYAML", file=sys.stderr)
    raise SystemExit(2) from e

REPO_ROOT = Path(__file__).resolve().parent.parent


def _nav_paths() -> list[str]:
    nav = REPO_ROOT / "docs" / "nav.yml"
    raw = yaml.safe_load(nav.read_text(encoding="utf-8"))
    out: list[str] = []
    for sec in raw.get("sections", []):
        for ent in sec.get("entries", []) or []:
            if isinstance(ent, str):
                out.append(ent.replace("\\", "/"))
            else:
                p = ent.get("path") or ent.get("source")
                if p:
                    out.append(str(p).replace("\\", "/"))
    return out


def _frontmatter(path: Path) -> dict[str, object] | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None
    block = m.group(1)
    data = yaml.safe_load(block)
    if not isinstance(data, dict):
        return None
    return data


def _extra_frontmatter_paths() -> list[str]:
    """Pages kept out of ``nav.yml`` but validated when present."""
    canary = REPO_ROOT / "docs/handbook-public/98-doc-ci-canary.md"
    return ["docs/handbook-public/98-doc-ci-canary.md"] if canary.is_file() else []


def main() -> int:
    required = (
        "audience",
        "section",
        "learning_level",
        "product_area",
        "status",
        "nav_title",
        "description",
        "tier",
        "handbook_area",
        "public_publish",
        "page_type",
    )
    errors: list[str] = []
    for rel in sorted(set(_nav_paths()) | set(_extra_frontmatter_paths())):
        p = REPO_ROOT / rel
        if not p.is_file():
            continue
        fm = _frontmatter(p)
        if fm is None:
            errors.append(f"{rel}: missing or invalid YAML frontmatter")
            continue
        for k in required:
            if k not in fm or fm[k] is None or str(fm[k]).strip() == "":
                errors.append(f"{rel}: missing frontmatter key {k!r}")
        aud = str(fm.get("audience", "")).strip().lower()
        if aud == "maintainer":
            errors.append(f"{rel}: audience must not be maintainer on a public nav page")
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    print("check-docs-frontmatter: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
