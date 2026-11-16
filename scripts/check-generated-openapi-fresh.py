#!/usr/bin/env python3
"""Fail when ``docs/generated/openapi.json`` drifts from ``generator/export_openapi.py`` output."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_GEN = REPO_ROOT / "generator"
COMMITTED = REPO_ROOT / "docs" / "generated" / "openapi.json"

sys.path.insert(0, str(_GEN))

from export_openapi import build_openapi_spec_from_disk  # noqa: E402


def main() -> int:
    if not COMMITTED.is_file():
        print(f"check-generated-openapi-fresh: missing {COMMITTED}", file=sys.stderr)
        print("run: python3 generator/export_openapi.py", file=sys.stderr)
        return 1
    expected = build_openapi_spec_from_disk()
    if expected is None:
        print("check-generated-openapi-fresh: cannot build spec (missing api-routes.json?)", file=sys.stderr)
        return 1
    try:
        actual = json.loads(COMMITTED.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"check-generated-openapi-fresh: invalid JSON {COMMITTED}: {exc}", file=sys.stderr)
        return 1
    if actual != expected:
        print(
            "check-generated-openapi-fresh: docs/generated/openapi.json is stale. Run:",
            file=sys.stderr,
        )
        print("  python3 generator/export_openapi.py", file=sys.stderr)
        return 1
    print("check-generated-openapi-fresh: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
