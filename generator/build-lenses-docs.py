#!/usr/bin/env python3
"""Build static Lenses documentation via forge-autodoc (KS handbook_page).

Run from the lenses repo root:

    pip install markdown PyYAML
    python3 generator/build-lenses-docs.py

Matches the **forge-lenses-website** Firebase output shape (same layout, transforms, nav).

Environment:

- ``LENSES_DOCS_BUILD_PROFILE`` — ``full`` (default) or ``public`` (manifest-only pages).
  Use ``public`` to verify the same page set as lenses.forgesdlc.com.

Optional reference-page PNG previews (``docs/index.md`` linked ``*.html`` only):

    pip install playwright && playwright install chromium
    python3 generator/build-lenses-docs.py --previews
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KS_ROOT = REPO_ROOT / "kitchensink"
FORGE_AUTODOC = KS_ROOT / "forge-autodoc"
OUTPUT_DIR = REPO_ROOT / "lenses-docs"

_REPO_STR = str(REPO_ROOT)
if _REPO_STR not in sys.path:
    sys.path.insert(0, _REPO_STR)
sys.path.insert(0, str(KS_ROOT / "components"))
sys.path.insert(0, str(KS_ROOT / "generator"))
sys.path.insert(0, str(FORGE_AUTODOC))

from forge_autodoc.config import HandbookBuildConfig  # noqa: E402
from forge_autodoc.files import DEFAULT_SKIP_DIR_NAMES  # noqa: E402
from forge_autodoc.simple_build import run_simple_build  # noqa: E402

from doc_previews import (  # noqa: E402
    capture_reference_previews,
    reference_preview_gallery_html,
    reference_preview_slugs,
)
from components import e  # noqa: E402


def _forge_lenses_skip_dir_names() -> frozenset[str]:
    parts = set(DEFAULT_SKIP_DIR_NAMES)
    parts.discard("docs")
    parts.update(
        {
            "blueprints",
            "kitchensink",
            ".github",
            ".cursor",
            "lenses-enterprise",
            "tests",
            "desktop",
            ".tox",
            ".venv",
            "venv",
            "dist",
            "htmlcov",
            "build",
            "__pypackages__",
            "tutorial",
            "lenses-docs",
            "node_modules",
            ".lenses-repo",
            ".lenses-local",
            "lenses/tutorials",
            "forge-logs",
        }
    )
    return frozenset(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--previews",
        action="store_true",
        help=(
            "Capture PNG previews for reference pages linked from docs/index.md "
            "(needs playwright + chromium install)."
        ),
    )
    args = parser.parse_args()

    if not KS_ROOT.is_dir():
        print("[lenses-docs] kitchensink submodule missing; run scripts/setup.sh", file=sys.stderr)
        return 1

    profile = (os.environ.get("LENSES_DOCS_BUILD_PROFILE") or "full").strip().lower()
    if profile not in ("full", "public"):
        print(f"[lenses-docs] invalid LENSES_DOCS_BUILD_PROFILE={profile!r}", file=sys.stderr)
        return 1

    index_md = REPO_ROOT / "docs" / "index.md"

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cfg = HandbookBuildConfig(
        content_root=REPO_ROOT.resolve(),
        output_dir=OUTPUT_DIR.resolve(),
        kitchensink=KS_ROOT.resolve(),
        handbook_name="Forge Lenses",
        skip_dir_names=_forge_lenses_skip_dir_names(),
        canonical_url_prefix=None,
        show_canonical_note=True,
        markdown_collect_preset="forge_lens_repo",
        derive_handbook_title_from_readme=False,
        build_profile=profile,
        nav_manifest_path="docs/nav.yml",
        site_nav_yaml="docs/site-nav.yaml",
        handbook_homepage_md_rel="docs/index.md",
        handbook_sidebar_brand_tagline="Product docs · local-first workspace",
        contextual_leaf_sidebar=True,
        lenses_public_manifest_site=(
            "https://lenses.forgesdlc.com" if profile == "public" else None
        ),
    )
    n = run_simple_build(cfg)
    if n < 0:
        return 1
    if n <= 0:
        print("[lenses-docs] build emitted no pages", file=sys.stderr)
        return 1

    built_slug_stems = {p.stem for p in OUTPUT_DIR.glob("*.html")}

    want_previews = args.previews or os.environ.get("LENSES_BUILD_DOC_PREVIEWS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if want_previews and index_md.is_file():
        ref_slugs = reference_preview_slugs(index_md, built_slug_stems)
        if ref_slugs:
            ok_slugs = capture_reference_previews(OUTPUT_DIR, ref_slugs)
            gallery_order = [s for s in ref_slugs if s in set(ok_slugs)]
            if gallery_order:
                gallery_html = reference_preview_gallery_html(
                    gallery_order,
                    {s: s.replace("-", " ").title() for s in gallery_order},
                    e,
                )
                idx_path = OUTPUT_DIR / "index.html"
                html = idx_path.read_text(encoding="utf-8")
                if "</body>" in html:
                    html = html.replace("</body>", gallery_html + "\n</body>", 1)
                    idx_path.write_text(html, encoding="utf-8")
                    print("  ✓ index.html (reference preview gallery injected)")
        else:
            print(
                "[lenses-docs] previews: no reference *.html links in docs/index.md — skipping",
                file=sys.stderr,
            )

    print(f"[lenses-docs] Done → {OUTPUT_DIR}/ ({profile} profile)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
