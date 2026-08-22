#!/usr/bin/env python3
"""Validate ``docs/redirects.yaml`` against emitted handbook HTML filenames.

Each entry maps ``from.html -> to.html`` (meta refresh stub targets).

Run **after** ``python3 generator/build-lenses-docs.py`` because ``check-docs.sh`` already emits ``lenses-docs/``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml  # type: ignore[import-untyped]
except ImportError as e:
    print("check-docs-redirects: install PyYAML", file=sys.stderr)
    raise SystemExit(2) from e

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HTML_ROOT = REPO_ROOT / "lenses-docs"
REDIRECT_DOC = REPO_ROOT / "docs" / "redirects.yaml"


def _load_pairs(path: Path) -> dict[str, str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    blob = data.get("redirects")
    if blob is None:
        return {}
    if not isinstance(blob, dict):
        raise ValueError("`redirects` must be a mapping")
    out: dict[str, str] = {}
    for raw_k, raw_v in blob.items():
        k = str(raw_k).strip()
        v = str(raw_v).strip()
        if not k.endswith(".html") or not v.endswith(".html"):
            raise ValueError(f"redirect keys/values must be *.html filenames, got {k!r} -> {v!r}")
        out[k] = v
    return dict(sorted(out.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html-root", type=Path, default=DEFAULT_HTML_ROOT, help="Built handbook root")
    args = parser.parse_args()

    if not REDIRECT_DOC.is_file():
        print(f"check-docs-redirects: missing {REDIRECT_DOC}", file=sys.stderr)
        return 1

    html_root = args.html_root.resolve()
    if not html_root.is_dir():
        print(f"check-docs-redirects: HTML root missing: {html_root}", file=sys.stderr)
        print("hint: python3 generator/build-lenses-docs.py", file=sys.stderr)
        return 1

    try:
        redirects = _load_pairs(REDIRECT_DOC)
    except ValueError as exc:
        print(f"check-docs-redirects: {exc}", file=sys.stderr)
        return 1

    errors: list[str] = []
    for src, dst in redirects.items():
        src_path = html_root / src
        dst_path = html_root / dst
        if not dst_path.is_file():
            errors.append(f"destination {dst} missing ({dst_path})")
            # Source stub may intentionally be omitted until generated — still flag missing destination.
        _ = src_path  # source HTML may remain ungenerated if operator creates stub manually — do not enforce.

    if errors:
        for line in errors:
            print(f"BAD_REDIRECT: {line}", file=sys.stderr)
        return 1

    print(f"check-docs-redirects: OK ({len(redirects)} stub(s) validated against {html_root})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
