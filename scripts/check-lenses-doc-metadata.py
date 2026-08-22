#!/usr/bin/env python3
"""Validate ``docs/nav.yml`` paths exist and optionally smoke-test a public doc build."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_nav_paths() -> list[str]:
    try:
        import yaml
    except ImportError as e:
        print("check-lenses-doc-metadata: install PyYAML", file=sys.stderr)
        raise SystemExit(2) from e

    nav = REPO_ROOT / "docs" / "nav.yml"
    if not nav.is_file():
        print(f"check-lenses-doc-metadata: missing {nav}", file=sys.stderr)
        return []
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
        "--no-build-smoke",
        action="store_true",
        help="Skip running generator/build-lenses-docs.py (public profile)",
    )
    args = ap.parse_args()

    missing: list[str] = []
    for rel in _load_nav_paths():
        p = REPO_ROOT / rel
        if not p.is_file():
            missing.append(rel)

    if missing:
        for m in missing:
            print(f"MISSING (nav.yml): {m}", file=sys.stderr)
        return 1

    if not args.no_build_smoke:
        env = dict(**__import__("os").environ)
        env["LENSES_DOCS_BUILD_PROFILE"] = "public"
        r = subprocess.run(
            [sys.executable, str(REPO_ROOT / "generator" / "build-lenses-docs.py")],
            cwd=REPO_ROOT,
            env=env,
            check=False,
        )
        if r.returncode != 0:
            return r.returncode
        idx = REPO_ROOT / "lenses-docs" / "index.html"
        if not idx.is_file():
            print("check-lenses-doc-metadata: lenses-docs/index.html missing after build", file=sys.stderr)
            return 1
        blob = idx.read_text(encoding="utf-8", errors="replace").lower()
        if "reference handbook (internal)" in blob:
            print(
                "check-lenses-doc-metadata: public index still contains legacy internal headline",
                file=sys.stderr,
            )
            return 1

    print("check-lenses-doc-metadata: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
