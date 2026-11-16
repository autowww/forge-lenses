"""HTTP API handbook vs ``lenses/serve.py`` parity (see generator/collect_lenses_api_routes.py)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_GEN = ROOT / "generator"
if str(_GEN) not in sys.path:
    sys.path.insert(0, str(_GEN))

from collect_lenses_api_routes import (  # noqa: E402
    SERVE_DEFAULT,
    collect_api_route_signatures,
    documented_in_md,
)


def test_http_handbook_documents_every_inventory_route():
    md = (ROOT / "lenses" / "website" / "http-api-and-routes.md").read_text(encoding="utf-8")
    assert SERVE_DEFAULT.is_file()
    for sig in collect_api_route_signatures():
        assert documented_in_md(sig, md), f"{sig.method} {sig.signature}"


def test_collector_stable_order():
    first = collect_api_route_signatures()
    second = collect_api_route_signatures()
    assert [s.signature for s in first] == [s.signature for s in second]

