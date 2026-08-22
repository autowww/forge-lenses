#!/usr/bin/env python3
"""Emit docs/generated/api-routes.{json,md} from the lenses/serve.py route collector.

Regenerate whenever ``lenses/serve.py`` routing changes; CI compares ``api-routes.json`` via
``scripts/check-generated-api-routes-fresh.py``.

JSON shape (``version`` 1): ``families`` (method counts per URL prefix family), ``routes``
(method, signature, family, audience).
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_GEN = REPO_ROOT / "generator"
sys.path.insert(0, str(_GEN))

from collect_lenses_api_routes import collect_api_route_signatures  # noqa: E402

JSON_OUT = REPO_ROOT / "docs" / "generated" / "api-routes.json"
MD_OUT = REPO_ROOT / "docs" / "generated" / "api-routes.md"


def api_route_family_key(signature: str) -> str:
    """Group paths by first two URL segments (same heuristic as documentation inventory)."""
    s = signature
    if s.startswith("PREFIX:"):
        rest = s[7:].rstrip("/")
        parts = [p for p in rest.split("/") if p]
        if len(parts) >= 2:
            return f"/{parts[0]}/{parts[1]}"
        return rest or "PREFIX"
    path = s.split("?", 1)[0].strip()
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2:
        return f"/{parts[0]}/{parts[1]}"
    return path or "/"


def api_route_audience(signature: str) -> str:
    """Coarse audience tag for handbook tables (not authorization)."""
    low = signature.split("?", 1)[0].casefold()
    if "admin" in low:
        return "admin"
    if "/api/auth" in low or "/auth/" in low:
        return "auth"
    if "docs-health" in low:
        return "docs-health"
    if "blueprints/wizard" in low:
        return "wizard"
    return "general"


def build_catalog() -> dict[str, object]:
    sigs = collect_api_route_signatures()
    routes: list[dict[str, str]] = []
    fam_methods: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for s in sigs:
        fam = api_route_family_key(s.signature)
        aud = api_route_audience(s.signature)
        routes.append({"method": s.method, "signature": s.signature, "family": fam, "audience": aud})
        fam_methods[fam][s.method] += 1

    families_out = {k: dict(v) for k, v in sorted(fam_methods.items())}
    return {
        "version": 1,
        "route_count": len(routes),
        "families": families_out,
        "routes": routes,
    }


def _render_markdown(catalog: dict[str, object]) -> str:
    routes = catalog["routes"]
    assert isinstance(routes, list)
    fm = """---
audience: public
section: builders
learning_level: reference
product_area: lenses
status: shipped
tier: builder
handbook_area: builders
public_publish: true
description: Machine-generated inventory of HTTP routes parsed from lenses/serve.py.
nav_title: HTTP API route catalog
---

"""
    lines = [
        "# HTTP API route inventory",
        "",
        "Auto-generated from `lenses/serve.py` via `generator/collect_lenses_api_routes.py`. "
        "Do not edit by hand — run `python3 generator/export_api_routes_docs.py`.",
        "",
        "See also [Builders — route families](../handbook-public/builders-route-families.md), "
        "[Schemas and API (builders)](../handbook-public/16-schemas-and-api-for-builders.md), "
        "and historical maintainer narrative on GitHub: "
        "[lenses/website/http-api-and-routes.md]"
        "(https://github.com/autowww/forge-lenses/blob/main/lenses/website/http-api-and-routes.md).",
        "",
        "## Full catalog",
        "",
        "| Method | Family | Audience | Signature |",
        "|--------|--------|----------|-----------|",
    ]
    for r in routes:
        assert isinstance(r, dict)
        method = str(r["method"])
        sig = str(r["signature"]).replace("|", "\\|")
        fam = str(r["family"]).replace("|", "\\|")
        aud = str(r["audience"]).replace("|", "\\|")
        lines.append(f"| {method} | `{fam}` | {aud} | `{sig}` |")
    lines.append("")

    fams = catalog["families"]
    assert isinstance(fams, dict)
    lines.append("## By family")
    lines.append("")
    for fam in sorted(fams.keys()):
        methods = fams[fam]
        assert isinstance(methods, dict)
        total = sum(int(v) for v in methods.values())
        lines.append(f"### `{fam}` — {total} route(s)")
        lines.append("")
        lines.append("| Method | Count |")
        lines.append("|--------|-------|")
        for m in sorted(methods.keys()):
            lines.append(f"| {m} | {methods[m]} |")
        lines.append("")
        lines.append("| Method | Audience | Signature |")
        lines.append("|--------|----------|-----------|")
        for r in routes:
            assert isinstance(r, dict)
            if r["family"] != fam:
                continue
            sig = str(r["signature"]).replace("|", "\\|")
            lines.append(f"| {r['method']} | {r['audience']} | `{sig}` |")
        lines.append("")

    return fm + "\n".join(lines)


def main() -> int:
    catalog = build_catalog()
    routes = catalog["routes"]
    assert isinstance(routes, list)
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    MD_OUT.write_text(_render_markdown(catalog), encoding="utf-8")
    print(f"export_api_routes_docs: wrote {JSON_OUT.relative_to(REPO_ROOT)} ({len(routes)} routes)")
    print(f"export_api_routes_docs: wrote {MD_OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
