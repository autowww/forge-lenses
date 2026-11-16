#!/usr/bin/env python3
"""Validate ``docs/nav.yml`` and optional coverage of ``docs/handbook-public/``.

Usage (from repo root):

    python3 scripts/check-docs-nav.py [--strict-handbook-public]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError as e:
    print("check-docs-nav: install PyYAML", file=sys.stderr)
    raise SystemExit(2) from e


REPO_ROOT = Path(__file__).resolve().parent.parent

_STRICT_HP_NAV_EXCLUDE = frozenset(
    {
        # Internal CI fixture — excluded from public nav.yml but kept on disk for full-profile builds.
        "docs/handbook-public/98-doc-ci-canary.md",
    }
)


def _nav_paths() -> list[str]:
    nav = REPO_ROOT / "docs" / "nav.yml"
    raw = yaml.safe_load(nav.read_text(encoding="utf-8"))
    out: list[str] = []
    for sec in raw.get("sections", []):
        for ent in sec.get("entries", []) or sec.get("pages", []) or []:
            if isinstance(ent, str):
                out.append(ent.replace("\\", "/"))
            else:
                p = ent.get("path") or ent.get("source")
                if p:
                    out.append(str(p).replace("\\", "/"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--strict-handbook-public",
        action="store_true",
        help="Require every docs/handbook-public/*.md to appear in nav.yml",
    )
    args = ap.parse_args()

    nav = REPO_ROOT / "docs" / "nav.yml"
    if not nav.is_file():
        print(f"check-docs-nav: missing {nav}", file=sys.stderr)
        return 1

    missing: list[str] = []
    paths = _nav_paths()
    for rel in paths:
        if not (REPO_ROOT / rel).is_file():
            missing.append(rel)

    if missing:
        for m in missing:
            print(f"MISSING (nav.yml): {m}", file=sys.stderr)
        return 1

    if args.strict_handbook_public:
        hp = REPO_ROOT / "docs" / "handbook-public"
        nav_set = set(paths)
        orphans = sorted(
            str(p.relative_to(REPO_ROOT))
            for p in hp.glob("*.md")
            if str(p.relative_to(REPO_ROOT)).replace("\\", "/") not in nav_set
            and str(p.relative_to(REPO_ROOT)).replace("\\", "/") not in _STRICT_HP_NAV_EXCLUDE
        )
        if orphans:
            for o in orphans:
                print(f"ORPHAN (not in nav.yml): {o}", file=sys.stderr)
            return 1

    print("check-docs-nav: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
