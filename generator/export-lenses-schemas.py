#!/usr/bin/env python3
"""Validate `docs/schemas/*.schema.json` registrations (deterministic no-op helper).

Run after editing schemas or bumping examples so CI and local scripts share the same smoke test.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "docs" / "schemas"


def main() -> int:
    files = sorted(SCHEMA_DIR.glob("*.schema.json"))
    if not files:
        print("export-lenses-schemas: missing docs/schemas/*.schema.json", file=sys.stderr)
        return 1
    for path in files:
        if not path.read_text(encoding="utf-8").strip().startswith("{"):
            print(f"export-lenses-schemas: invalid json file {path}", file=sys.stderr)
            return 2
    print(f"export-lenses-schemas: ok ({len(files)} schema file(s)) → {SCHEMA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
