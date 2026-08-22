#!/usr/bin/env python3
"""Forge Lenses handbook navigation UX budgets (site IA + manifest sanity).

Fails when horizontal menus exceed policy, dropdown groups are oversized,
``docs/nav.yml`` references internal CI fixtures for public IA, or
``lens_manifest_sections`` ids do not resolve to ``nav.yml`` sections.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError as e:
    print("check-docs-nav-budget: install PyYAML", file=sys.stderr)
    raise SystemExit(2) from e

REPO_ROOT = Path(__file__).resolve().parent.parent

MAX_TOP_LEVEL_MENUS = 7
MAX_DROPDOWN_CHILDREN = 8


def main() -> int:
    errors: list[str] = []

    nav_yml = REPO_ROOT / "docs/nav.yml"
    site_nav = REPO_ROOT / "docs/site-nav.yaml"
    if not nav_yml.is_file():
        errors.append(f"missing {nav_yml.relative_to(REPO_ROOT)}")
        print("\n".join(errors), file=sys.stderr)
        return 1
    if not site_nav.is_file():
        errors.append(f"missing {site_nav.relative_to(REPO_ROOT)}")
        print("\n".join(errors), file=sys.stderr)
        return 1

    raw_nav = yaml.safe_load(nav_yml.read_text(encoding="utf-8"))
    section_ids = {str(s.get("id", "")).strip() for s in raw_nav.get("sections", []) if s.get("id")}
    section_ids.discard("")

    raw_site = yaml.safe_load(site_nav.read_text(encoding="utf-8"))
    top = raw_site.get("top_level") or []
    if not isinstance(top, list):
        errors.append("site-nav.yaml top_level must be a list")
    elif len(top) > MAX_TOP_LEVEL_MENUS:
        errors.append(
            f"site-nav.yaml has {len(top)} top menus (max {MAX_TOP_LEVEL_MENUS}); collapse IA further."
        )

    nav_paths: list[str] = []
    for sec in raw_nav.get("sections", []):
        for ent in sec.get("entries", []) or []:
            if isinstance(ent, str):
                nav_paths.append(ent.replace("\\", "/"))
            else:
                p = ent.get("path") or ent.get("source")
                if p:
                    nav_paths.append(str(p).replace("\\", "/"))

    banned_substrings = ("98-doc-ci-canary",)
    for rel in nav_paths:
        low = rel.lower()
        if any(b in low for b in banned_substrings):
            errors.append(f"nav.yml must not reference internal CI fixtures ({rel})")

    if isinstance(top, list):
        for block in top:
            if not isinstance(block, dict):
                continue
            tid = str(block.get("id", ""))
            children = block.get("children") or []
            if isinstance(children, list) and len(children) > MAX_DROPDOWN_CHILDREN:
                errors.append(
                    f"{tid}: dropdown children {len(children)} exceed max {MAX_DROPDOWN_CHILDREN}"
                )
            cap_raw = block.get("dropdown_max_items")
            if cap_raw is not None:
                try:
                    cap = int(cap_raw)
                except (TypeError, ValueError):
                    cap = -1
                if cap > MAX_DROPDOWN_CHILDREN:
                    errors.append(
                        f"{tid}: dropdown_max_items={cap} exceeds policy max {MAX_DROPDOWN_CHILDREN}"
                    )

            lens_secs = block.get("lens_manifest_sections") or []
            if lens_secs is None:
                continue
            if not isinstance(lens_secs, list):
                errors.append(f"{tid}: lens_manifest_sections must be a list")
                continue
            for sid in lens_secs:
                s = str(sid).strip()
                if s and s not in section_ids:
                    errors.append(
                        f"{tid}: lens_manifest_sections references unknown nav.yml section id {s!r}"
                    )

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    print("check-docs-nav-budget: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
