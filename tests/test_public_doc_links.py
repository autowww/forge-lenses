"""Regression tests for docs link hygiene helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_checker():
    path = Path(__file__).resolve().parents[1] / "scripts" / "check-public-doc-links.py"
    spec = importlib.util.spec_from_file_location("_pub_doc_links", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_public_link_scan_blocks_lens_website_relative(tmp_path: Path) -> None:
    chk = _load_checker()
    (tmp_path / "docs" / "handbook-public").mkdir(parents=True)
    (tmp_path / "lenses" / "website").mkdir(parents=True)

    leaky = tmp_path / "docs" / "handbook-public" / "evil.md"
    target = tmp_path / "lenses" / "website" / "http-api-and-routes.md"
    target.write_text("# t\n")
    leaky.write_text(
        "---\n"
        "audience: public\nsection: builders\nlearning_level: reference\nproduct_area: lenses\nstatus: shipped\n---\n"
        "\n[oops](../../lenses/website/http-api-and-routes.md)\n",
        encoding="utf-8",
    )
    sources = [leaky.resolve()]
    allow = {"docs/handbook-public/evil.md"}
    violations = chk.scan_sources(repo_root=tmp_path, allow_rels=allow, sources=sources)
    assert violations, "expected lenses/website relative link to fail"
    assert any("internal route narrative" in v[3] for v in violations)


def test_public_link_scan_allows_github_https(tmp_path: Path) -> None:
    chk = _load_checker()
    (tmp_path / "docs" / "handbook-public").mkdir(parents=True)

    md = tmp_path / "docs" / "handbook-public" / "ok.md"
    md.write_text(
        "---\n"
        "audience: public\nsection: builders\nlearning_level: reference\nproduct_area: lenses\nstatus: shipped\n---\n"
        "\n[Fleet](https://github.com/autowww/forge-lenses/blob/main/README.md)\n",
        encoding="utf-8",
    )
    allow = {"docs/handbook-public/ok.md"}
    violations = chk.scan_sources(
        repo_root=tmp_path, allow_rels=allow, sources=[md.resolve()]
    )
    assert not violations
