#!/usr/bin/env python3
"""Fail when docs/generated/api-routes.json drifts from lenses/serve.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_GEN = REPO_ROOT / "generator"
COMMITTED = REPO_ROOT / "docs" / "generated" / "api-routes.json"

sys.path.insert(0, str(_GEN))

from export_api_routes_docs import build_catalog  # noqa: E402


def main() -> int:
    if not COMMITTED.is_file():
        print(f"check-generated-api-routes-fresh: missing {COMMITTED}", file=sys.stderr)
        print("run: python3 generator/export_api_routes_docs.py", file=sys.stderr)
        return 1
    expected = build_catalog()
    try:
        actual = json.loads(COMMITTED.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"check-generated-api-routes-fresh: invalid JSON {COMMITTED}: {exc}", file=sys.stderr)
        return 1
    if actual != expected:
        print(
            "check-generated-api-routes-fresh: docs/generated/api-routes.json is stale "
            "(serve.py routes changed). Run:",
            file=sys.stderr,
        )
        print("  python3 generator/export_api_routes_docs.py", file=sys.stderr)
        return 1
    print("check-generated-api-routes-fresh: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
