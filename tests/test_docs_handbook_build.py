"""Handbook build profiles (public vs full) for static Lenses docs."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "generator" / "build-lenses-docs.py"


def _run_build(profile: str) -> None:
    env = dict(os.environ)
    env["LENSES_DOCS_BUILD_PROFILE"] = profile
    env["PYTHONPATH"] = str(ROOT)
    r = subprocess.run(
        [sys.executable, str(BUILD)],
        cwd=str(ROOT),
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr


def test_public_static_tree_has_no_adr_nav_hrefs() -> None:
    _run_build("public")
    out = ROOT / "lenses-docs"
    href_adr = re.compile(r'href=["\'][^"\']*adr-[^"\']*["\']', re.IGNORECASE)
    for html in out.glob("*.html"):
        blob = html.read_text(encoding="utf-8", errors="replace")
        matches = href_adr.findall(blob)
        assert not matches, f"{html.name}: unexpected ADR href {matches[:3]}"


def test_public_publish_false_canary_not_in_output() -> None:
    marker = "BODY_UNIQUE_7C1A9E_LENSES_DOC"
    canary_md = ROOT / "docs" / "handbook-public" / "98-doc-ci-canary.md"
    assert marker in canary_md.read_text(encoding="utf-8")
    _run_build("public")
    out = ROOT / "lenses-docs"
    for html in out.glob("*.html"):
        assert marker not in html.read_text(encoding="utf-8", errors="replace")


def test_public_manifest_excludes_ci_canary_path() -> None:
    _run_build("public")
    manifest_path = ROOT / "lenses-docs" / "public-manifest.json"
    assert manifest_path.is_file()

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    pages = data.get("pages") or []
    paths = []
    assert isinstance(pages, list)
    for row in pages:
        if isinstance(row, dict):
            p = str(row.get("source_path") or "").replace("\\", "/")
            paths.append(p.lower())
            assert "98-doc-ci-canary" not in p.lower()


def test_full_build_exposes_at_least_one_adr_page() -> None:
    try:
        _run_build("full")
        out = ROOT / "lenses-docs"
        names = {p.name for p in out.glob("*.html")}
        assert any(n.lower().startswith("adr-") for n in names), "expected an adr-*.html in full build"
    finally:
        _run_build("public")
