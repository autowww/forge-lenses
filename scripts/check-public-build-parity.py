#!/usr/bin/env python3
"""Verify ``lenses-docs/public-manifest.json`` matches the repo nav and emitted HTML."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    manifest_path = REPO_ROOT / "lenses-docs" / "public-manifest.json"
    if not manifest_path.is_file():
        print(
            "check-public-build-parity: lenses-docs/public-manifest.json missing "
            "(run LENSES_DOCS_BUILD_PROFILE=public python3 generator/build-lenses-docs.py)",
            file=sys.stderr,
        )
        return 1
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    out_dir = REPO_ROOT / "lenses-docs"
    errors: list[str] = []

    nav_rel = str(data.get("source_nav_path") or "docs/nav.yml").replace("\\", "/")
    nav_path = (REPO_ROOT / nav_rel).resolve()
    if not nav_path.is_file():
        errors.append(f"nav file missing at {nav_rel}")
    else:
        live_hash = _sha256_file(nav_path)
        expect = data.get("nav_sha256") or ""
        if live_hash != expect:
            errors.append(f"nav_sha256 mismatch manifest={expect!r} disk={live_hash!r}")

    ef = data.get("effective_public_page_count")
    pages = data.get("pages")
    if not isinstance(pages, list):
        errors.append("manifest.pages must be a list")
        return 1

    if isinstance(ef, int) and ef != len(pages):
        errors.append(f"effective_public_page_count ({ef}) != len(pages) ({len(pages)})")

    for row in pages:
        if not isinstance(row, dict):
            errors.append("invalid page row in manifest")
            continue
        slug = str(row.get("output_slug", "")).strip()
        src = str(row.get("source_path", "")).strip()
        title = str(row.get("page_title_heading", "")).strip()
        desc = str(row.get("description", "")).strip()
        if not slug:
            errors.append(f"manifest page missing output_slug ({src})")
            continue
        hp = out_dir / slug
        if not hp.is_file():
            errors.append(f"missing emitted HTML for {slug} (source {src})")
        if not title.strip():
            errors.append(f"missing manifest page_title_heading for {src}")
        # description may be filled in during metadata prompt; do not block parity on empty

    if errors:
        for e in errors:
            print(f"check-public-build-parity: {e}", file=sys.stderr)
        return 1

    print("check-public-build-parity: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
