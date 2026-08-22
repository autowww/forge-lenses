#!/usr/bin/env python3
"""Emit a **partial** OpenAPI 3.1 document sourced from docs/generated/api-routes.json."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ROUTES_JSON = REPO_ROOT / "docs" / "generated" / "api-routes.json"
OUTPUT = REPO_ROOT / "docs" / "generated" / "openapi.json"


def _slugify(signature: str) -> str:
    """Turn a collector signature into a stable-ish OpenAPI path token."""
    s = signature.split("?", 1)[0].strip()
    s = re.sub(r"[^\w/+{}-]+", "-", s)
    s = s.strip("-") or "root"
    if not s.startswith("/"):
        s = "/" + s
    return s


def build_openapi_spec_from_disk() -> dict[str, object] | None:
    """Parse ``docs/generated/api-routes.json`` into an OpenAPI 3.1 dict, or ``None`` if missing."""
    if not ROUTES_JSON.is_file():
        return None
    catalog = json.loads(ROUTES_JSON.read_text(encoding="utf-8"))
    routes = catalog.get("routes", [])
    if not isinstance(routes, list):
        print("[export-openapi] malformed catalog: routes is not a list", file=sys.stderr)
        return None

    by_path: dict[str, dict[str, object]] = defaultdict(dict)
    for row in routes:
        if not isinstance(row, dict):
            continue
        method = str(row.get("method", "GET")).lower()
        signature = str(row.get("signature", "/"))
        open_path = _slugify(signature)
        summary = signature if len(signature) <= 96 else signature[:93] + "…"
        by_path.setdefault(open_path, {})[method] = {
            "summary": summary,
            "responses": {
                "200": {"description": "Success (schema varies by handler — see handbook)."},
                "default": {
                    "description": (
                        "Structured error envelopes mirror https://lenses.forgesdlc.com/schemas/api-error.schema.json."
                    ),
                },
            },
        }

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Forge Lenses HTTP API (derived)",
            "version": str(catalog.get("version", 1)),
            "description": (
                "Machine-derived **partial** OpenAPI rollup from docs/generated/api-routes.json — "
                "method inventory only. Handlers reuse query strings for actions; authoritative semantics "
                "remain in lenses/serve.py and the handbook (Schemas and API for builders)."
            ),
            "contact": {"name": "Forge Lenses", "url": "https://github.com/autowww/forge-lenses"},
            "license": {"name": "See forge-lenses repository LICENSE"},
            "x-lenses-docs-coverage": "partial-route-inventory-only",
            "x-lenses-source": "generator/export_openapi.py",
        },
        "tags": [{"name": "forge-lenses-derived", "description": "Emitted from tracked route signatures."}],
        "paths": {path: verbs for path, verbs in sorted(by_path.items())},
        "x-lenses-route-count": len(routes),
        "x-lenses-route-catalog-version": catalog.get("version", 1),
    }


def main() -> int:
    spec = build_openapi_spec_from_disk()
    if spec is None:
        print(f"[export-openapi] missing {ROUTES_JSON} — run generator/export_api_routes_docs.py")
        return 1
    by_path = spec.get("paths")
    npaths = len(by_path) if isinstance(by_path, dict) else 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    print(f"[export-openapi] wrote {OUTPUT.relative_to(REPO_ROOT)} ({npaths} path group(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
