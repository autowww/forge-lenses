#!/usr/bin/env python3
"""Ensure HTTP routes from ``lenses/serve.py`` are mentioned in builder-facing Markdown.

Uses the same heuristics as ``collect_lenses_api_routes.documented_in_md`` for legacy
route-signature prose coverage, plus **family contracts** in
``docs/strategy/api-family-contracts.json``.

Environment:

- ``LENSES_API_DOC_COVERAGE_WARN=1`` — print missing routes but exit 0 (gradual adoption).

Usage:

    python3 scripts/check-api-doc-coverage.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_GEN = REPO_ROOT / "generator"
CONTRACT_JSON = REPO_ROOT / "docs" / "strategy" / "api-family-contracts.json"
sys.path.insert(0, str(_GEN))

from collect_lenses_api_routes import (  # noqa: E402
    documented_in_md,
    collect_api_route_signatures,
)


def _slug_exempt_token(family: str) -> str:
    tail = family.strip().lower().lstrip("/").replace("/", "_").replace("-", "_")
    return f"SCHEMA_EXEMPT_{tail}"


def _doc_corpus() -> str:
    parts: list[str] = []
    for rel in (
        "lenses/website/http-api-and-routes.md",
        "docs/handbook-public/16-schemas-and-api-for-builders.md",
        "docs/handbook-public/builders-schemas.md",
        "docs/handbook-public/builders-openapi.md",
        "docs/handbook-public/15-docs-health.md",
    ):
        p = REPO_ROOT / rel
        if p.is_file():
            parts.append(p.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def _load_family_contract_entries() -> list[dict[str, object]] | None:
    """Return contract rows, or ``None`` if corrupt / unreadable."""

    if not CONTRACT_JSON.is_file():
        return []
    try:
        data = json.loads(CONTRACT_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"check-api-doc-coverage: corrupt {CONTRACT_JSON}: {exc}", file=sys.stderr)
        return None
    entries = data.get("entries")
    return entries if isinstance(entries, list) else []


def _missing_family_checks(corpus: str) -> list[str]:
    issues: list[str] = []
    entries = _load_family_contract_entries()
    if entries is None:
        return ["api-family-contracts.json invalid"]
    if not entries:
        return issues

    lower = corpus.lower()
    for row in entries:
        if not isinstance(row, dict):
            issues.append("contract entries must be objects")
            continue
        family = str(row.get("family", "")).strip()
        stab = str(row.get("stability", "")).strip()
        reqs = row.get("must_substrings")
        if not family or stab not in ("stable", "beta"):
            issues.append(f"family contract missing family or stability: {row!r}")
            continue
        exempt = _slug_exempt_token(family).lower()
        if exempt in lower:
            continue
        if not isinstance(reqs, list) or not reqs or not all(isinstance(s, str) for s in reqs):
            issues.append(f"{family} ({stab}): must_substrings must be a non-empty string list")
            continue
        missing_reqs = [s for s in reqs if s.strip() and s.strip().lower() not in lower]
        if missing_reqs:
            issues.append(f"{family} ({stab}) missing handbook substrings: {missing_reqs!r}")

    return issues


def main() -> int:
    warn_only = os.environ.get("LENSES_API_DOC_COVERAGE_WARN", "").strip() in ("1", "true", "yes")
    corpus = _doc_corpus()
    if not corpus.strip():
        print("check-api-doc-coverage: no documentation corpus found", file=sys.stderr)
        return 1

    missing_family = _missing_family_checks(corpus)
    if missing_family:
        for line in missing_family:
            print(f"MISSING_FAMILY_DOC: {line}", file=sys.stderr)

    missing_sig: list[str] = []
    for sig in collect_api_route_signatures():
        if not documented_in_md(sig, corpus):
            missing_sig.append(f"{sig.method} {sig.signature}")

    if missing_sig:
        for line in missing_sig:
            print(f"MISSING_DOC: {line}", file=sys.stderr)

    if warn_only:
        if missing_family or missing_sig:
            print("check-api-doc-coverage: WARN (see MISSING_* lines)", file=sys.stderr)
        else:
            print("check-api-doc-coverage: OK")
        return 0

    if missing_family or missing_sig:
        return 1

    print("check-api-doc-coverage: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
