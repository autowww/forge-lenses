#!/usr/bin/env python3
"""Validate ``forge/docs-contract.yaml`` — paths and README requirements."""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError as e:
    print("check-forge-docs-contract: install PyYAML", file=sys.stderr)
    raise SystemExit(2) from e

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT = REPO_ROOT / "forge" / "docs-contract.yaml"
README = REPO_ROOT / "README.md"


def main() -> int:
    if not CONTRACT.is_file():
        print(f"check-forge-docs-contract: missing {CONTRACT}", file=sys.stderr)
        return 1

    data = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        print("check-forge-docs-contract: expected version: 1", file=sys.stderr)
        return 1

    errs: list[str] = []

    for root in data.get("doc_roots") or []:
        p = REPO_ROOT / str(root)
        if not p.is_dir() and not p.is_file():
            errs.append(f"doc_roots entry missing: {root}")

    readme_text = README.read_text(encoding="utf-8")
    for heading in data.get("readme_required_sections") or []:
        if not re.search(rf"^##\s+{re.escape(str(heading))}\s*$", readme_text, re.MULTILINE):
            errs.append(f"README.md missing ## {heading}")

    if data.get("require_adr"):
        adrs = list((REPO_ROOT / "docs").glob("adr-*.md"))
        if not adrs:
            errs.append("require_adr: no docs/adr-*.md files")

    if data.get("require_release_note"):
        if not (REPO_ROOT / "docs" / "handbook-public" / "24-release-notes.md").is_file():
            errs.append("require_release_note: missing docs/handbook-public/24-release-notes.md")

    if data.get("require_architecture_diagram"):
        if not (REPO_ROOT / "docs" / "handbook-public" / "diagram-catalog-lenses.md").is_file():
            errs.append("require_architecture_diagram: missing diagram catalog page")

    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        return 1

    print("check-forge-docs-contract: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
