"""Tests for /view/docs and /view/local-site shell routes and URL helpers."""

from __future__ import annotations

from lenses.render import (
    embed_in_app_doc_url,
    page_view_embed,
    view_lenses_docs_href,
    view_local_site_href,
)
from lenses.serve import LENSES_REPO_ROOT


def test_view_lenses_docs_href() -> None:
    assert view_lenses_docs_href() == "/view/docs"
    assert view_lenses_docs_href("index.html") == "/view/docs/index.html"
    assert "architecture.html" in view_lenses_docs_href("architecture.html")


def test_view_local_site_href() -> None:
    assert view_local_site_href("myrepo", "tutorials/index.html").startswith(
        "/view/local-site/"
    )


def test_embed_in_app_doc_url() -> None:
    assert embed_in_app_doc_url("/docs/foo.html") == "/view/docs/foo.html"
    assert embed_in_app_doc_url("/local-site/r/t.html") == "/view/local-site/r/t.html"
    assert embed_in_app_doc_url("/projects") == "/projects"


def test_page_view_embed_includes_iframe_src() -> None:
    state: dict = {"children": [], "websites": []}
    html = page_view_embed(
        state,
        iframe_src="/docs/index.html",
        raw_open_href="/docs/index.html",
        page_title="Test",
        breadcrumb_parts=[("/", "Overview"), ("", "Test")],
        lenses_repo_root=LENSES_REPO_ROOT,
        handbook_url="https://example.com/h/",
        forge_url="https://example.com/f/",
        missing_message=None,
    )
    assert 'src="/docs/index.html"' in html
    assert "lenses-view-embed-frame" in html


def test_page_view_embed_missing_message() -> None:
    state: dict = {"children": [], "websites": []}
    html = page_view_embed(
        state,
        iframe_src="/docs/missing.html",
        raw_open_href="/docs/missing.html",
        page_title="Missing",
        breadcrumb_parts=[("/", "Overview"), ("", "Missing")],
        lenses_repo_root=LENSES_REPO_ROOT,
        handbook_url="https://example.com/h/",
        forge_url="https://example.com/f/",
        missing_message="Not here",
    )
    assert "Not here" in html
    assert "lenses-view-embed-frame" not in html
