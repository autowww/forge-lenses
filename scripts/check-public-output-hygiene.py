#!/usr/bin/env python3
"""Fail if public handbook artifacts leak canary/internal markers."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "lenses-docs"
MANIFEST = OUT_DIR / "public-manifest.json"

# Substrings must never appear in emitted public HTML after a public-profile build.
_FORBIDDEN_HTML_SUBSTRINGS = (
    "BODY_UNIQUE_7C1A9E_LENSES_DOC",
    "98-doc-ci-canary",
    "doc-ci-canary",
    "Documentation build canary",
    "<!-- doc-ci-canary",
)

_CANARY_PATH_RE = re.compile(r".*handbook-public/98-doc-ci-canary\.md$", re.IGNORECASE)


def main() -> int:
    if not MANIFEST.is_file():
        print(
            "check-public-output-hygiene: lenses-docs/public-manifest.json missing "
            "(run LENSES_DOCS_BUILD_PROFILE=public python3 generator/build-lenses-docs.py)",
            file=sys.stderr,
        )
        return 1
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if str(data.get("build_profile") or "").strip().lower() != "public":
        print("check-public-output-hygiene: manifest build_profile must be public", file=sys.stderr)
        return 1

    errors: list[str] = []

    pages = data.get("pages")
    if isinstance(pages, list):
        for row in pages:
            if not isinstance(row, dict):
                continue
            src = str(row.get("source_path") or "").replace("\\", "/")
            if _CANARY_PATH_RE.match(src) or "98-doc-ci-canary" in src.lower():
                errors.append(f"canary Markdown path leaked into manifest.pages: {src}")

    html_files = sorted(OUT_DIR.glob("*.html"))
    if not html_files:
        errors.append("no *.html emitted under lenses-docs/")
    for hp in html_files:
        blob = hp.read_text(encoding="utf-8", errors="replace")
        for banned in _FORBIDDEN_HTML_SUBSTRINGS:
            if banned in blob:
                errors.append(f"{hp.name}: forbidden public marker substring {banned!r}")

    if errors:
        for e in errors:
            print(f"check-public-output-hygiene: {e}", file=sys.stderr)
        return 1

    print("check-public-output-hygiene: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
