#!/usr/bin/env python3
"""Write docs/generated/schema-index.json from docs/schemas/*.schema.json."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO_ROOT / "docs" / "schemas"
OUTPUT = REPO_ROOT / "docs" / "generated" / "schema-index.json"


def main() -> int:
    rows: list[dict[str, object]] = []
    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        data = json.loads(schema_path.read_text(encoding="utf-8"))
        rows.append(
            {
                "file": schema_path.name,
                "id": data.get("$id"),
                "title": data.get("title"),
                "x_lenses_stability": data.get("x-lenses-stability"),
                "additionalProperties": data.get("additionalProperties"),
            }
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    blob = {"version": 1, "schema_count": len(rows), "schemas": rows}
    OUTPUT.write_text(json.dumps(blob, indent=2) + "\n", encoding="utf-8")
    print(f"[export-schema-index] wrote {OUTPUT.relative_to(REPO_ROOT)} ({len(rows)} schema(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
