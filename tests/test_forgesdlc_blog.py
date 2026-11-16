"""Tests for forgesdlc.com blog sitemap parsing and URL allowlist."""

from __future__ import annotations

from lenses.forgesdlc_blog import (
    FORGESDLC_BLOG_PREFIX,
    extract_og_image_from_html,
    is_allowed_forgesdlc_blog_url,
    normalize_preview_image_url,
    parse_forgesdlc_blog_urls_from_sitemap,
    slug_from_blog_url,
)

_SAMPLE_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://forgesdlc.com/blog/index.html</loc>
    <lastmod>2026-04-01</lastmod>
  </url>
  <url>
    <loc>https://forgesdlc.com/blog/verification-not-coding.html</loc>
    <lastmod>2026-03-18</lastmod>
  </url>
  <url>
    <loc>https://evil.com/blog/foo.html</loc>
    <lastmod>2026-01-01</lastmod>
  </url>
  <url>
    <loc>https://forgesdlc.com/privacy.html</loc>
    <lastmod>2026-01-01</lastmod>
  </url>
</urlset>
"""


def test_parse_forgesdlc_blog_urls_from_sitemap_filters_host_and_path() -> None:
    rows = parse_forgesdlc_blog_urls_from_sitemap(_SAMPLE_SITEMAP)
    urls = {r["url"] for r in rows}
    assert "https://forgesdlc.com/blog/index.html" in urls
    assert "https://forgesdlc.com/blog/verification-not-coding.html" in urls
    assert "https://evil.com/blog/foo.html" not in urls
    assert "https://forgesdlc.com/privacy.html" not in urls
    by_url = {r["url"]: r["lastmod"] for r in rows}
    assert by_url["https://forgesdlc.com/blog/verification-not-coding.html"] == "2026-03-18"


def test_is_allowed_forgesdlc_blog_url_rejects_traversal_and_other_hosts() -> None:
    assert is_allowed_forgesdlc_blog_url(f"{FORGESDLC_BLOG_PREFIX}foo-bar.html")
    assert not is_allowed_forgesdlc_blog_url("https://forgesdlc.com/blog/../etc/passwd")
    assert not is_allowed_forgesdlc_blog_url("https://other.com/blog/foo.html")


def test_slug_from_blog_url() -> None:
    assert (
        slug_from_blog_url("https://forgesdlc.com/blog/verification-not-coding.html")
        == "verification-not-coding.html"
    )
    assert slug_from_blog_url("https://forgesdlc.com/blog/") is None


def test_extract_og_image_from_html_property_first() -> None:
    html = b'<head><meta property="og:image" content="https://forgesdlc.com/assets/blog/x-preview.svg" />'
    assert extract_og_image_from_html(html) == "https://forgesdlc.com/assets/blog/x-preview.svg"


def test_extract_og_image_from_html_content_first() -> None:
    html = b'<meta content="https://forgesdlc.com/assets/foo.png" property="og:image" />'
    assert extract_og_image_from_html(html) == "https://forgesdlc.com/assets/foo.png"


def test_normalize_preview_image_url_drops_default_og() -> None:
    assert normalize_preview_image_url("https://forgesdlc.com/assets/og-default.svg") is None
    assert normalize_preview_image_url("https://forgesdlc.com/path/og-default.svg") is None


def test_normalize_preview_image_url_keeps_blog_preview() -> None:
    u = "https://forgesdlc.com/assets/blog/verification-not-coding-preview.svg"
    assert normalize_preview_image_url(u) == u
