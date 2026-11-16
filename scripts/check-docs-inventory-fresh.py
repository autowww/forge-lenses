#!/usr/bin/env python3
"""Ensure ``documentation-inventory.json`` matches regenerated inventory (excluding volatile keys)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = REPO_ROOT / "docs" / "strategy" / "documentation-inventory.json"

_VOLATILE = frozenset({"generated_at", "git_commit"})


def _load_builder():
    script = REPO_ROOT / "generator" / "export-docs-inventory.py"
    spec = importlib.util.spec_from_file_location("export_docs_inventory", script)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _strip(blob: dict[str, object]) -> dict[str, object]:
    out = dict(blob)
    for k in _VOLATILE:
        out.pop(k, None)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", type=Path, default=DEFAULT_PATH, help="inventory JSON path")
    ap.add_argument(
        "--write",
        action="store_true",
        help="Rewrite the inventory JSON from current repo state.",
    )
    args = ap.parse_args()

    mod = _load_builder()
    if args.write:
        import subprocess

        proc = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "generator" / "export-docs-inventory.py"),
                "--output",
                str(args.path),
            ],
            cwd=str(REPO_ROOT),
            check=False,
        )
        return int(proc.returncode)

    fresh = mod.build_inventory_document()
    disk_text = args.path.read_text(encoding="utf-8")
    disk = json.loads(disk_text)

    a = json.dumps(_strip(disk), sort_keys=True)
    b = json.dumps(_strip(fresh), sort_keys=True)
    if a != b:
        print("check-docs-inventory-fresh: documentation-inventory.json is stale.", file=sys.stderr)
        print("  Regenerate: python3 generator/export-docs-inventory.py", file=sys.stderr)
        return 1
    print("check-docs-inventory-fresh: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
