"""Optional reference-page screenshots for lenses-docs (html2image + local HTTP).

Level-1 slugs come from ``docs/index.md`` Markdown links to ``*.html``.
Screenshots use a short-lived ``ThreadingHTTPServer`` on 127.0.0.1, first free
port in 8090–8200, and fixed viewport (no full-page height — browser paints one window).

Enable with ``--previews`` or env ``LENSES_BUILD_DOC_PREVIEWS=1``.
Requires Chromium/Chrome on PATH or standard locations, plus ``pip install html2image``.
"""
from __future__ import annotations

import re
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from collections.abc import Callable
from pathlib import Path

# First port tried is 8090; last is 8200 (111 candidates).
# Import lenses helper after REPO_ROOT is on sys.path (see build-lenses-docs.py).
_PREVIEW_PORT_MIN = 8090
_PREVIEW_PORT_MAX = 8200
_PREVIEW_HOST = "127.0.0.1"
_VIEWPORT: tuple[int, int] = (1280, 900)

# Links like ](architecture.html) or ](./foo.html)
_MD_HTML_LINK = re.compile(r"\]\(([^)]+\.html)\)", re.IGNORECASE)


def parse_reference_html_slugs(index_md_path: Path) -> list[str]:
    """Extract local ``*.html`` link targets from ``docs/index.md``, preserve order, dedupe."""
    if not index_md_path.is_file():
        return []
    text = index_md_path.read_text(encoding="utf-8")
    seen: set[str] = set()
    out: list[str] = []
    for m in _MD_HTML_LINK.finditer(text):
        raw = m.group(1).strip().strip('"').strip("'")
        raw = raw.split()[0] if raw else ""
        if not raw or raw.startswith(("http://", "https://", "//")):
            continue
        base = Path(raw).name
        if not base.lower().endswith(".html"):
            continue
        slug = base[:-5]
        if not slug or slug in seen:
            continue
        seen.add(slug)
        out.append(slug)
    return out


def reference_preview_slugs(index_md_path: Path, built_slugs: set[str]) -> list[str]:
    """Slugs linked from index that exist in the built handbook."""
    return [s for s in parse_reference_html_slugs(index_md_path) if s in built_slugs]


def _make_handler_class(directory: Path) -> type[SimpleHTTPRequestHandler]:
    root = str(directory.resolve())

    class _DocsPreviewHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=root, **kwargs)

        def log_message(self, format: str, *log_args) -> None:  # noqa: A003
            pass

    return _DocsPreviewHandler


def _try_bind_server(
    output_dir: Path,
    host: str,
    port: int,
) -> ThreadingHTTPServer | None:
    Handler = _make_handler_class(output_dir)
    try:
        return ThreadingHTTPServer((host, port), Handler)
    except OSError:
        return None


def start_preview_server(output_dir: Path) -> tuple[ThreadingHTTPServer, int] | None:
    """Bind first free port in ``_PREVIEW_PORT_MIN``..``_PREVIEW_PORT_MAX`` on ``host``."""
    for port in range(_PREVIEW_PORT_MIN, _PREVIEW_PORT_MAX + 1):
        httpd = _try_bind_server(output_dir, _PREVIEW_HOST, port)
        if httpd is not None:
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            return httpd, port
    return None


def capture_reference_previews(
    output_dir: Path,
    slugs: list[str],
) -> list[str]:
    """Write ``previews/{slug}.png`` for each slug. Returns list of slugs captured successfully."""
    if not slugs:
        return []

    try:
        import html2image  # noqa: F401
    except ImportError:
        print(
            "[lenses-docs] previews: html2image not installed — pip install html2image",
            file=sys.stderr,
        )
        return []

    from lenses.html2image_capture import capture_url_to_png

    print("[lenses-docs] Capturing reference previews …")

    previews_dir = output_dir / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)

    # Drop stale PNGs for slugs we are about to refresh; remove orphans from previous index lists
    for p in previews_dir.glob("*.png"):
        stem = p.stem
        if stem not in slugs:
            try:
                p.unlink()
            except OSError:
                pass

    started = start_preview_server(output_dir)
    if started is None:
        print(
            f"[lenses-docs] previews: no free port on {_PREVIEW_HOST} "
            f"in {_PREVIEW_PORT_MIN}–{_PREVIEW_PORT_MAX} — skipping captures",
            file=sys.stderr,
        )
        return []

    httpd, port = started
    ok: list[str] = []

    try:
        base = f"http://{_PREVIEW_HOST}:{port}"
        for slug in slugs:
            url = f"{base}/{slug}.html"
            name = f"{slug}.png"
            dest = previews_dir / name
            if capture_url_to_png(
                url,
                dest,
                size=_VIEWPORT,
                virtual_time_budget_ms=8000,
            ):
                ok.append(slug)
                print(f"  ✓ previews/{name}")
            else:
                print(
                    f"  ✗ previews/{name} (capture failed or html2image missing)",
                    file=sys.stderr,
                )
    finally:
        httpd.shutdown()
        httpd.server_close()

    return ok


def reference_preview_gallery_html(
    slugs: list[str],
    titles_by_slug: dict[str, str],
    esc: Callable[[str], str],
) -> str:
    """Bootstrap grid of cards linking to reference pages with preview images."""
    if not slugs:
        return ""
    cards: list[str] = []
    for slug in slugs:
        title = titles_by_slug.get(slug, slug.replace("-", " ").title())
        cards.append(
            '<div class="col-md-6 col-lg-4">'
            f'<a class="text-decoration-none forge-card d-block p-2 h-100 lenses-doc-preview-card" '
            f'href="{esc(slug)}.html">'
            f'<img src="previews/{esc(slug)}.png" alt="" class="img-fluid rounded mb-2 w-100" '
            'style="object-fit:cover;aspect-ratio:16/10;max-height:220px;background:var(--bs-body-bg,#0A0E17)"/>'
            f'<span class="text-cyan small fw-semibold">{esc(title)}</span>'
            "</a>"
            "</div>"
        )
    return (
        '<section class="lenses-doc-reference-previews mt-4 pt-3 border-top border-secondary" '
        'aria-labelledby="lenses-doc-reference-previews-heading">'
        '<h2 id="lenses-doc-reference-previews-heading" class="h5 text-cyan mb-3">'
        "Reference page previews</h2>"
        f'<div class="row g-3">{"".join(cards)}</div>'
        "</section>"
    )
