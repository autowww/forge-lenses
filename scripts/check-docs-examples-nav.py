#!/usr/bin/env python3
"""Ensure ``26-examples-scenarios-hub.md`` links match ``examples-scenario-*.md`` pages."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HUB = REPO_ROOT / "docs/handbook-public/26-examples-scenarios-hub.md"
HANDBOOK_PUBLIC = REPO_ROOT / "docs" / "handbook-public"
PREFIX = "examples-scenario-"
LINK_PAT = re.compile(rf"\]\(({PREFIX}[^)]+\.md)\)")


def main() -> int:
    if not HUB.is_file():
        print(f"check-docs-examples-nav: missing {HUB}", file=sys.stderr)
        return 1

    text = HUB.read_text(encoding="utf-8")
    linked = set(LINK_PAT.findall(text))
    errs: list[str] = []

    for name in sorted(linked):
        path = HANDBOOK_PUBLIC / name
        if not path.is_file():
            errs.append(f"hub links missing file: {name}")

    for path in sorted(HANDBOOK_PUBLIC.glob(f"{PREFIX}*.md")):
        if path.name not in linked:
            errs.append(f"scenario page not linked from hub table: {path.name}")

    if errs:
        for line in errs:
            print(line, file=sys.stderr)
        return 1

    print("check-docs-examples-nav: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
