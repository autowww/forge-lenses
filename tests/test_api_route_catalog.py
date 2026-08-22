"""Generated API route catalog structure (``docs/generated/api-routes.json``)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG = REPO_ROOT / "docs" / "generated" / "api-routes.json"
MD = REPO_ROOT / "docs" / "generated" / "api-routes.md"
_GEN = REPO_ROOT / "generator"
sys.path.insert(0, str(_GEN))

from export_api_routes_docs import build_catalog  # noqa: E402


@pytest.mark.skipif(not CATALOG.is_file(), reason="generated api-routes.json missing")
def test_committed_api_routes_matches_serve_py() -> None:
    assert json.loads(CATALOG.read_text(encoding="utf-8")) == build_catalog()


def test_catalog_families_cover_routes() -> None:
    cat = build_catalog()
    assert cat.get("version") == 1
    routes = cat["routes"]
    families = cat["families"]
    assert isinstance(routes, list)
    assert isinstance(families, dict)
    assert len(routes) == cat["route_count"]
    for r in routes:
        fam = r["family"]
        assert fam in families
        assert r["method"] in families[fam]


@pytest.mark.skipif(not MD.is_file(), reason="generated api-routes.md missing")
def test_api_routes_markdown_has_family_sections() -> None:
    cat = build_catalog()
    md_text = MD.read_text(encoding="utf-8")
    for fam in cat["families"]:
        assert f"### `{fam}`" in md_text
