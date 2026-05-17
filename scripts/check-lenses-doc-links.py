#!/usr/bin/env python3
"""Verify internal handbook links resolve after ``generator/build-lenses-docs.py``.

Checks:
1. Every ``*.html`` referenced from ``docs/index.md`` (Markdown link targets) exists under
   ``lenses-docs/`` (default ``--output-dir``).
2. With ``--scan-html``, every same-directory ``*.html`` href in built pages exists on disk.

Does not follow external https links.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "lenses-docs"
INDEX_MD = REPO_ROOT / "docs" / "index.md"

# Markdown link target: (something.html) or (something.html#anchor)
_MD_HTML_TARGET = re.compile(
    r"\]\(\s*([^)#\s]+)(?:#[^)]*)?\)",
    re.MULTILINE,
)

# href="foo.html" | href='foo.html' — skip http(s), mailto, anchors-only
_HREF_LOCAL_HTML = re.compile(
    r'href=["\'](?!https?:)(?!mailto:)([^"\'#?]+?\.html(?:\?[^"\']*)?)["\']',
    re.IGNORECASE,
)


def _index_md_targets() -> list[str]:
    if not INDEX_MD.is_file():
        return []
    text = INDEX_MD.read_text(encoding="utf-8")
    out: list[str] = []
    for m in _MD_HTML_TARGET.finditer(text):
        target = m.group(1).strip()
        if target.startswith("http://") or target.startswith("https://"):
            continue
        base = target.split("/")[-1]
        if not base.endswith(".html"):
            continue
        out.append(base)
    return out


def _scan_built_html(output_dir: Path) -> list[tuple[str, str]]:
    """Return (referrer_basename, missing_target_basename) for broken links."""
    by_name = {p.name: p for p in output_dir.glob("*.html")}
    missing: list[tuple[str, str]] = []
    for path in sorted(by_name.values()):
        html = path.read_text(encoding="utf-8", errors="replace")
        for m in _HREF_LOCAL_HTML.finditer(html):
            raw = m.group(1).strip()
            name = Path(raw).name
            if not name.endswith(".html"):
                continue
            if name not in by_name:
                missing.append((path.name, name))
    return missing


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Built handbook directory (default: {DEFAULT_OUT})",
    )
    ap.add_argument(
        "--no-build",
        action="store_true",
        help="Skip running generator/build-lenses-docs.py first",
    )
    ap.add_argument(
        "--scan-html",
        action="store_true",
        help="Also verify all local *.html hrefs in every built page",
    )
    args = ap.parse_args()

    if not args.no_build:
        env = dict(**__import__("os").environ)
        env.setdefault("LENSES_DOCS_BUILD_PROFILE", "public")
        r = subprocess.run(
            [sys.executable, str(REPO_ROOT / "generator" / "build-lenses-docs.py")],
            cwd=REPO_ROOT,
            env=env,
            check=False,
        )
        if r.returncode != 0:
            print("check-lenses-doc-links: build-lenses-docs.py failed", file=sys.stderr)
            return r.returncode

    out_dir: Path = args.output_dir
    if not out_dir.is_dir():
        print(f"check-lenses-doc-links: missing output dir {out_dir}", file=sys.stderr)
        return 2

    failures = 0
    for name in sorted(set(_index_md_targets())):
        p = out_dir / name
        if not p.is_file():
            print(f"MISSING (from docs/index.md): {name}", file=sys.stderr)
            failures += 1

    if args.scan_html:
        for ref, tgt in _scan_built_html(out_dir):
            print(f"MISSING (from {ref}): {tgt}", file=sys.stderr)
            failures += 1

    if failures:
        print(f"check-lenses-doc-links: {failures} broken link(s)", file=sys.stderr)
        return 1
    print(f"check-lenses-doc-links: OK → {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
