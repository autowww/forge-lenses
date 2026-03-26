"""Kitchensink path helpers and showcase_page wrapper for the dynamic server."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable


def kitchensink_root(lenses_repo_root: Path) -> Path:
    return lenses_repo_root / "kitchensink"


def ks_assets_available(lenses_repo_root: Path) -> bool:
    root = kitchensink_root(lenses_repo_root)
    return root.is_dir() and (root / "css" / "forge-theme.css").is_file()


def _ensure_ks_import_path(lenses_repo_root: Path) -> None:
    root = kitchensink_root(lenses_repo_root)
    comp = root / "components"
    gen = root / "generator"
    for p in (comp, gen):
        sp = str(p.resolve())
        if sp not in sys.path:
            sys.path.insert(0, sp)


def get_showcase_page(lenses_repo_root: Path) -> Callable[..., str] | None:
    if not ks_assets_available(lenses_repo_root):
        return None
    _ensure_ks_import_path(lenses_repo_root)
    try:
        from layouts import showcase_page  # noqa: WPS433
    except ImportError:
        return None
    return showcase_page


def ks_theme_links() -> str:
    """Extra head links: Forge product theme after base forge-theme (cards / bento)."""
    return (
        '  <link rel="stylesheet" href="/__ks/css/forgesdlc-theme.css" />\n'
        '  <style>.lenses-dash .forge-card { text-decoration: none; color: inherit; }\n'
        "  .lenses-dash a.fs-topic-preview-card { box-sizing: border-box; display: flex; "
        "flex-direction: column; height: 100%; min-height: 10rem; }\n"
        "  .lenses-dash .lenses-pill-row { gap: 0.35rem; flex-wrap: wrap; }\n"
        "  .lenses-ext-bar { height: 0.5rem; border-radius: 4px; background: rgba(6,182,212,0.35); }\n"
        "  .lenses-git-out { white-space: pre-wrap; font-size: 0.8rem; max-height: 12rem; overflow: auto; "
        "background: var(--bs-body-bg, #0f172a); border: 1px solid var(--forge-border, #1e293b); "
        "padding: 0.75rem; border-radius: 6px; }\n"
        "  .lenses-toolset-desc { white-space: pre-wrap; font-size: 0.85rem; max-height: 16rem; overflow: auto; "
        "background: var(--bs-body-bg, #0f172a); border: 1px solid var(--forge-border, #1e293b); "
        "padding: 0.75rem; border-radius: 6px; margin-bottom: 0; }\n"
        "  .lenses-toolset-console { white-space: pre-wrap; font-size: 0.8rem; "
        "max-height: min(70vh, 40rem); overflow: auto; "
        "background: var(--bs-body-bg, #0f172a); border: 1px solid var(--forge-border, #1e293b); "
        "padding: 0.75rem; border-radius: 6px; }\n"
        "  .lenses-sticker-root { min-height: 12rem; }\n"
        "  .lenses-sticker-toolbar { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; margin-bottom: 1rem; }\n"
        "  .lenses-sticker-kanban { display: flex; gap: 0.75rem; align-items: flex-start; overflow-x: auto; padding-bottom: 0.5rem; }\n"
        "  .lenses-sticker-column { flex: 1 1 12rem; min-width: 10rem; max-width: 22rem; "
        "background: var(--bs-body-bg, #0f172a); border: 1px solid var(--forge-border, #1e293b); "
        "border-radius: 8px; padding: 0.5rem; min-height: 14rem; }\n"
        "  .lenses-sticker-column h3 { font-size: 0.85rem; margin: 0 0 0.5rem; color: var(--bs-info, #06b6d4); }\n"
        "  .lenses-sticker-column-body { min-height: 10rem; border-radius: 6px; padding: 0.25rem; "
        "border: 1px dashed rgba(148,163,184,0.25); }\n"
        "  .lenses-sticker-column-body.lenses-drag-over { border-color: rgba(6,182,212,0.6); background: rgba(6,182,212,0.06); }\n"
        "  .lenses-sticker-card { position: relative; cursor: grab; padding: 0.5rem 1.85rem 0.5rem 0.6rem; margin-bottom: 0.4rem; "
        "border-radius: 6px; background: var(--forge-border, #1e293b); border: 1px solid rgba(148,163,184,0.2); "
        "font-size: 0.88rem; user-select: none; }\n"
        "  .lenses-sticker-card-actions { position: absolute; top: 0.15rem; right: 0.15rem; display: flex; gap: 0.1rem; "
        "opacity: 0; transition: opacity 0.12s ease; z-index: 3; }\n"
        "  .lenses-sticker-card:hover .lenses-sticker-card-actions { opacity: 1; }\n"
        "  .lenses-sticker-card-actions .btn { min-width: 1.75rem; min-height: 1.75rem; padding: 0.1rem 0.35rem; "
        "line-height: 1.2; font-size: 0.75rem; }\n"
        "  .lenses-sticker-scope { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.04em; "
        "opacity: 0.75; margin-bottom: 0.15rem; }\n"
        "  .lenses-sticker-card:active { cursor: grabbing; }\n"
        "  .lenses-sticker-card-title { font-weight: 600; margin-bottom: 0.2rem; }\n"
        "  .lenses-sticker-card-preview { font-size: 0.78rem; opacity: 0.85; line-height: 1.35; "
        "display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }\n"
        "  .lenses-sticker-canvas { position: relative; min-height: 28rem; border-radius: 8px; "
        "border: 1px solid var(--forge-border, #1e293b); background: rgba(15,23,42,0.5); overflow: hidden; }\n"
        "  .lenses-sticker-float { position: absolute; width: 11rem; z-index: 2; }\n"
        "  .lenses-sticker-modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.55); z-index: 2000; "
        "display: flex; align-items: center; justify-content: center; padding: 1rem; }\n"
        "  .lenses-sticker-modal { max-width: 32rem; width: 100%; padding: 1rem 1.25rem; border-radius: 10px; "
        "border: 1px solid var(--forge-border, #1e293b); background: var(--bs-body-bg, #0f172a); }\n"
        "  .lenses-sticker-status { font-size: 0.8rem; opacity: 0.8; }\n"
        "  .lenses-overview-lede { font-size: 1.08rem; line-height: 1.6; max-width: 52rem; }\n"
        "  .lenses-overview-kpi { min-height: 100%; transition: border-color 0.15s ease; }\n"
        "  .lenses-overview-kpi:hover { border-color: rgba(6,182,212,0.45) !important; }\n"
        "  .lenses-overview-article { border-left: 3px solid var(--bs-info, #06b6d4); "
        "background: rgba(15,23,42,0.35); border-radius: 0 8px 8px 0; padding: 0.75rem 1rem !important; "
        "border-bottom: 1px solid var(--forge-border, #1e293b); margin-bottom: 0.65rem; }\n"
        "  .lenses-overview-article:last-child { margin-bottom: 0; border-bottom: none; }\n"
        "  .lenses-overview-headline { font-weight: 600; line-height: 1.35; }\n"
        "  .lenses-overview-kicker a { font-weight: 600; text-decoration: none; color: var(--bs-info, #06b6d4); }\n"
        "  .lenses-overview-kicker a:hover { text-decoration: underline; }\n"
        "  .lenses-overview-aside-block { background: rgba(15,23,42,0.45); }\n"
        "  .lenses-overview-hero-wrap .landing-hero-kicker { text-transform: uppercase; letter-spacing: 0.06em; }\n"
        "  .lenses-overview-hero-wrap .fs-landing-hero-band, .lenses-overview-hero-fallback { "
        "padding: 1.25rem 0 0.5rem; border-bottom: 1px solid var(--forge-border, #1e293b); margin-bottom: 0.5rem; }\n"
        "  @media (min-width: 992px) {\n"
        "    .lenses-overview-newsfeed-sticky { position: sticky; top: 0.75rem; max-height: calc(100vh - 1.5rem); "
        "overflow-y: auto; padding-right: 0.25rem; }\n"
        "  }\n"
        "  .lenses-overview-commit-body { white-space: pre-wrap; line-height: 1.45; opacity: 0.92; }\n"
        "  .lenses-overview-hbar-track { height: 0.55rem; border-radius: 4px; "
        "background: rgba(148,163,184,0.2); overflow: hidden; }\n"
        "  .lenses-overview-hbar-fill { height: 100%; border-radius: 4px; min-width: 2px; }\n"
        "  .lenses-overview-hbar-fill--cyan { background: rgba(6,182,212,0.9); }\n"
        "  .lenses-overview-hbar-fill--warning { background: rgba(245,158,11,0.85); }\n"
        "  .lenses-overview-hbar-fill--success { background: rgba(34,197,94,0.8); }\n"
        "  .lenses-overview-metrics-strip { border-radius: 8px; }\n"
        "  .lenses-overview-repo-card { border-radius: 8px; }\n"
        "  .lenses-overview-donut-wrap { display: flex; flex-wrap: wrap; align-items: flex-start; gap: 1rem; }\n"
        "  .lenses-overview-donut-legend { flex: 1 1 10rem; min-width: 8rem; max-width: 18rem; }\n"
        "  .lenses-overview-donut-swatch { display: inline-block; width: 0.65rem; height: 0.65rem; "
        "border-radius: 2px; flex-shrink: 0; }\n"
        "  .lenses-overview-repo-meta { line-height: 1.55; }\n"
        "  .lenses-overview-quick-links a { color: var(--bs-info, #06b6d4); text-decoration: none; }\n"
        "  .lenses-overview-quick-links a:hover { text-decoration: underline; }\n"
        "  .lenses-overview-ext-pill { font-weight: 500; }\n"
        "  .lenses-overview-repo-details summary { cursor: pointer; color: var(--bs-info, #06b6d4); }\n"
        "  .lenses-overview-repo-desc-full { white-space: pre-wrap; word-break: break-word; line-height: 1.45; }\n"
        "  .lenses-overview-repo-lede { line-height: 1.5; }</style>\n"
    )


def lenses_showcase_page(
    lenses_repo_root: Path,
    *,
    browser_title: str,
    page_title: str,
    breadcrumb_html: str,
    sidebar_html: str,
    body_html: str,
    toc_html: str = "",
    footer_html: str = "",
) -> str | None:
    showcase_page = get_showcase_page(lenses_repo_root)
    if showcase_page is None:
        return None
    return showcase_page(
        browser_title=browser_title,
        brand_name="lenses",
        brand_subtitle="Workspace",
        page_title=page_title,
        breadcrumb_html=breadcrumb_html,
        sidebar_html=sidebar_html,
        body_html=f'<div class="lenses-dash">{body_html}</div>',
        toc_html=toc_html,
        footer_html=footer_html,
        extra_css=ks_theme_links(),
        extra_js=[],
        theme_css_href="/__ks/css/forge-theme.css",
        theme_js_href="/__ks/js/forge-theme.js",
        has_mermaid=False,
        has_ks_diagram=False,
    )
