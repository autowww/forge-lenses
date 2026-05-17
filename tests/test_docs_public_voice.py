"""Regression tests for Lenses public documentation voice and nav manifest."""

from __future__ import annotations

from pathlib import Path


def test_product_docs_index_not_internal_voice() -> None:
    root = Path(__file__).resolve().parents[1]
    idx = (root / "docs" / "index.md").read_text(encoding="utf-8")
    assert "reference handbook (internal)" not in idx.lower()
    assert "lenses.forgesdlc.com" in idx


def test_nav_yml_paths_exist() -> None:
    import yaml

    root = Path(__file__).resolve().parents[1]
    raw = yaml.safe_load((root / "docs" / "nav.yml").read_text(encoding="utf-8"))
    for sec in raw.get("sections", []):
        for ent in sec.get("entries", []):
            if isinstance(ent, str):
                rel = ent
            else:
                rel = ent.get("path") or ent.get("source")
            assert rel, f"bad entry in section {sec.get('id')}"
            assert (root / rel).is_file(), f"missing {rel}"
