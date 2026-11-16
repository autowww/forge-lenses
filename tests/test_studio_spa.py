"""Lenses Studio SPA static routing helpers."""

from __future__ import annotations

from pathlib import Path

from lenses.serve import LENSES_REPO_ROOT, _studio_spa_index_fallback


def _index_exists() -> Path | None:
    idx = LENSES_REPO_ROOT / "lenses" / "static" / "studio" / "index.html"
    return idx if idx.is_file() else None


def test_studio_spa_fallback_returns_index_for_client_route() -> None:
    if _index_exists() is None:
        return
    p = _studio_spa_index_fallback(LENSES_REPO_ROOT, "/studio/projects")
    assert p is not None
    assert p.name == "index.html"


def test_studio_spa_fallback_skips_missing_asset() -> None:
    p = _studio_spa_index_fallback(
        LENSES_REPO_ROOT, "/studio/assets/does-not-exist.js"
    )
    assert p is None
