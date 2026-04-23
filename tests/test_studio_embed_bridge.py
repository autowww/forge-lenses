"""Studio preview iframe → parent SPA navigation bridge."""

from __future__ import annotations

from lenses.studio_embed_bridge import inject_studio_iframe_nav_bridge


def test_inject_inserts_before_body() -> None:
    raw = b"<!doctype html><html><body><p>x</p></body></html>"
    out = inject_studio_iframe_nav_bridge(raw)
    assert b"lenses-studio-embed-nav-bridge" in out
    assert b"lenses-studio-same-origin-nav" in out
    assert out.index(b"<p>x</p>") < out.index(b"lenses-studio-embed-nav-bridge")


def test_inject_idempotent() -> None:
    raw = b"<!doctype html><html><body></body></html>"
    once = inject_studio_iframe_nav_bridge(raw)
    twice = inject_studio_iframe_nav_bridge(once)
    assert twice.count(b"lenses-studio-embed-nav-bridge") == 1
