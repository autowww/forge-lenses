#!/usr/bin/env python3
"""Build static lenses documentation using kitchensink showcase_page.

Run from lenses repo root:
    pip install markdown
    python3 generator/build-lenses-docs.py

Optional reference-page PNG previews (``docs/index.md`` linked ``*.html`` only):
    pip install html2image
    LENSES_BUILD_DOC_PREVIEWS=1 python3 generator/build-lenses-docs.py --previews
    # Requires Chromium/Chrome. Uses a local HTTP server on 127.0.0.1:8090–8200.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    print("Install markdown: pip install markdown", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
GEN_ROOT = Path(__file__).resolve().parent
_REPO_STR = str(REPO_ROOT)
if _REPO_STR not in sys.path:
    sys.path.insert(0, _REPO_STR)
DOCS_SRC = REPO_ROOT / "docs"
WEBSITE_DOCS = REPO_ROOT / "lenses" / "website"
OUTPUT_DIR = REPO_ROOT / "lenses-docs"
KS_ROOT = REPO_ROOT / "kitchensink"

sys.path.insert(0, str(GEN_ROOT))
sys.path.insert(0, str(KS_ROOT / "components"))
sys.path.insert(0, str(KS_ROOT / "generator"))

from components import e  # noqa: E402
from layouts import showcase_page  # noqa: E402

from doc_previews import (  # noqa: E402
    capture_reference_previews,
    reference_preview_gallery_html,
    reference_preview_slugs,
)


def _slug_from_stem(stem: str) -> str:
    return stem.lower().replace(" ", "-")


def _page_dict_from_md(md: Path) -> dict:
    slug = "index" if md.stem.lower() in ("index", "readme") else _slug_from_stem(md.stem)
    text = md.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else md.stem.replace("-", " ").title()
    return {
        "slug": slug,
        "title": title,
        "source": md,
        "text": text,
    }


def _load_pages() -> list[dict]:
    """Handbook sources: docs/*.md first, then lenses/website/*.md (package reference)."""
    pages: list[dict] = []
    if DOCS_SRC.is_dir():
        for md in sorted(DOCS_SRC.glob("*.md")):
            pages.append(_page_dict_from_md(md))
    if WEBSITE_DOCS.is_dir():
        for md in sorted(WEBSITE_DOCS.glob("*.md")):
            pages.append(_page_dict_from_md(md))
    by_slug: dict[str, dict] = {}
    for p in pages:
        by_slug[p["slug"]] = p
    return sorted(by_slug.values(), key=lambda p: (0 if p["slug"] == "index" else 1, p["slug"]))


def _build_sidebar(pages: list[dict], current_slug: str) -> str:
    lines: list[str] = []
    lines.append('<p class="nav-section-label">lenses docs</p>')
    lines.append('<div class="nav-rail">')
    for p in pages:
        active = " active" if p["slug"] == current_slug else ""
        lines.append(
            f'<a class="doc-sidebar-link{active}" href="{p["slug"]}.html">{e(p["title"])}</a>'
        )
    lines.append("</div>")
    return "\n".join(lines)


def _breadcrumb(page: dict) -> str:
    return (
        '<nav aria-label="breadcrumb">'
        '<ol class="breadcrumb mb-1" style="font-size:0.75rem">'
        '<li class="breadcrumb-item">'
        '<a href="index.html" class="text-cyan" style="text-decoration:none">lenses</a>'
        '</li>'
        f'<li class="breadcrumb-item active text-dim" aria-current="page">'
        f'{e(page["title"])}</li>'
        '</ol></nav>'
    )


def _toc_from_html(html: str) -> str:
    """Rough ToC from h2 ids."""
    lines: list[str] = []
    for m in re.finditer(r'<h2[^>]*id="([^"]+)"[^>]*>(.*?)</h2>', html, re.DOTALL):
        aid, inner = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
        lines.append(f'<a class="nav-link" href="#{e(aid)}">{e(inner.strip())}</a>')
    return "\n".join(lines)


def _slugify_heading(text: str, used: dict[str, int]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"
    n = used.get(base, 0)
    used[base] = n + 1
    return base if n == 0 else f"{base}-{n}"


def _add_h2_ids(html: str) -> str:
    used: dict[str, int] = {}

    def repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        plain = re.sub(r"<[^>]+>", "", inner).strip()
        hid = _slugify_heading(plain, used)
        return f'<h2 id="{e(hid)}">{inner}</h2>'

    return re.sub(r"<h2>(.*?)</h2>", repl, html, flags=re.DOTALL)


def _render_body_md(text: str) -> str:
    body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "nl2br"],
    )
    return _add_h2_ids(body)


def _footer() -> str:
    return (
        '<hr class="forge-divider">'
        '<footer class="text-center pb-4">'
        '<p class="forge-support">lenses · local workspace visualization</p>'
        '</footer>'
    )


def _render_page(
    page: dict,
    all_pages: list[dict],
    *,
    body_suffix: str = "",
) -> str:
    body_html = _render_body_md(page["text"])
    toc_html = _toc_from_html(body_html)
    sidebar_html = _build_sidebar(all_pages, page["slug"])
    doc_wrap = f'<div class="lenses-doc-body">{body_html}</div>{body_suffix}'
    return showcase_page(
        browser_title=f'{page["title"]} — lenses docs',
        brand_name="lenses",
        brand_subtitle="Documentation",
        page_title=page["title"],
        breadcrumb_html=_breadcrumb(page),
        sidebar_html=sidebar_html,
        body_html=doc_wrap,
        toc_html=toc_html,
        footer_html=_footer(),
        extra_css="",
        extra_js=["assets/showcase.js"],
        theme_css_href="assets/forge-theme.css",
        theme_js_href="assets/forge-theme.js",
        has_mermaid=False,
        has_ks_diagram=False,
    )


def _copy_assets() -> None:
    assets_out = OUTPUT_DIR / "assets"
    assets_out.mkdir(parents=True, exist_ok=True)
    for css in (KS_ROOT / "css").glob("*.css"):
        shutil.copy2(css, assets_out / css.name)
    for js in (KS_ROOT / "js").glob("*.js"):
        shutil.copy2(js, assets_out / js.name)
    js_showcase = KS_ROOT / "js" / "showcase.js"
    if js_showcase.is_file():
        shutil.copy2(js_showcase, assets_out / "showcase.js")
    svg_out = assets_out / "svg"
    svg_src = KS_ROOT / "assets" / "svg"
    if svg_src.is_dir():
        if svg_out.exists():
            shutil.rmtree(svg_out)
        shutil.copytree(svg_src, svg_out)


def _wants_previews(args: argparse.Namespace) -> bool:
    if args.previews:
        return True
    v = os.environ.get("LENSES_BUILD_DOC_PREVIEWS", "").strip().lower()
    return v in ("1", "true", "yes")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build lenses-docs static handbook.")
    parser.add_argument(
        "--previews",
        action="store_true",
        help="Capture PNG previews for reference pages linked from docs/index.md (needs html2image + Chrome).",
    )
    args = parser.parse_args()

    if not KS_ROOT.is_dir():
        print("[lenses-docs] kitchensink submodule missing; run scripts/setup.sh", file=sys.stderr)
        sys.exit(1)
    pages = _load_pages()
    if not pages:
        print("[lenses-docs] No markdown in docs/ or lenses/website/", file=sys.stderr)
        DOCS_SRC.mkdir(parents=True, exist_ok=True)
        WEBSITE_DOCS.mkdir(parents=True, exist_ok=True)
        print("Add docs/*.md (and optional lenses/website/*.md) and re-run.", file=sys.stderr)
        sys.exit(1)

    built_slugs = {p["slug"] for p in pages}
    titles_by_slug = {p["slug"]: p["title"] for p in pages}
    index_md = DOCS_SRC / "index.md"
    ref_slugs = reference_preview_slugs(index_md, built_slugs)
    want_previews = _wants_previews(args)

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)
    _copy_assets()
    print("[lenses-docs] Assets copied")

    index_page = next((p for p in pages if p["slug"] == "index"), None)
    others = [p for p in pages if p["slug"] != "index"]

    for page in others:
        slug = page["slug"]
        html = _render_page(page, pages)
        (OUTPUT_DIR / f"{slug}.html").write_text(html, encoding="utf-8")
        print(f"  ✓ {slug}.html")

    if index_page:
        html_idx = _render_page(index_page, pages)
        (OUTPUT_DIR / "index.html").write_text(html_idx, encoding="utf-8")
        print("  ✓ index.html")

    if want_previews and ref_slugs:
        ok_slugs = capture_reference_previews(OUTPUT_DIR, ref_slugs)
        gallery_order = [s for s in ref_slugs if s in set(ok_slugs)]
        if index_page and gallery_order:
            gallery_html = reference_preview_gallery_html(gallery_order, titles_by_slug, e)
            html_idx = _render_page(index_page, pages, body_suffix=gallery_html)
            (OUTPUT_DIR / "index.html").write_text(html_idx, encoding="utf-8")
            print("  ✓ index.html (with reference preview gallery)")
    elif want_previews and not ref_slugs:
        print("[lenses-docs] previews: no reference *.html links in docs/index.md — skipping", file=sys.stderr)

    print(f"[lenses-docs] Done → {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
