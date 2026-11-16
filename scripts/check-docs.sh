#!/usr/bin/env bash
# Orchestrate Forge Lenses documentation quality checks (public profile).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p build
echo "[check-docs] API routes JSON (prompt 01 / 08 artifact)"
python3 generator/collect_lenses_api_routes.py --output build/lenses-api-routes.json

if [[ ! -f docs/generated/api-routes.json ]] || [[ ! -f docs/generated/api-routes.md ]]; then
  echo "[check-docs] bootstrap docs/generated/api-routes.* (first clone or new workspace)"
  python3 generator/export_api_routes_docs.py
fi

echo "[check-docs] schema index + OpenAPI stubs"
python3 generator/export_schema_index.py
python3 generator/export_openapi.py
python3 scripts/check-generated-openapi-fresh.py

echo "[check-docs] public→private Markdown link gate"
python3 scripts/check-public-doc-links.py

export LENSES_DOCS_BUILD_PROFILE="${LENSES_DOCS_BUILD_PROFILE:-public}"
export PYTHONPATH="$ROOT"

echo "[check-docs] build (profile=$LENSES_DOCS_BUILD_PROFILE)"
python3 generator/build-lenses-docs.py

echo "[check-docs] offline public build parity manifest"
python3 scripts/check-public-build-parity.py

echo "[check-docs] public output hygiene (canary / internal markers)"
python3 scripts/check-public-output-hygiene.py

echo "[check-docs] live parity (instructions only unless --allow-network on script)"
python3 scripts/check-live-docs-parity.py

echo "[check-docs] nav metadata (no second build)"
python3 scripts/check-lenses-doc-metadata.py --no-build-smoke

echo "[check-docs] HTML link scan"
python3 scripts/check-lenses-doc-links.py --scan-html

echo "[check-docs] nav.yml"
python3 scripts/check-docs-nav.py --strict-handbook-public

echo "[check-docs] navigation UX budgets"
python3 scripts/check-docs-nav-budget.py

echo "[check-docs] examples scenario hub vs pages"
python3 scripts/check-docs-examples-nav.py

echo "[check-docs] frontmatter (nav pages)"
python3 scripts/check-docs-frontmatter.py

echo "[check-docs] page-type word budgets"
python3 scripts/check-docs-page-budget.py

echo "[check-docs] diagrams"
python3 scripts/check-docs-diagrams.py

echo "[check-docs] API route coverage vs docs"
python3 scripts/check-api-doc-coverage.py

echo "[check-docs] generated API routes freshness"
python3 scripts/check-generated-api-routes-fresh.py

echo "[check-docs] forge docs contract"
python3 scripts/check-forge-docs-contract.py

echo "[check-docs] handbook tutorial headings"
python3 scripts/check-handbook-tutorial-headings.py

echo "[check-docs] documentation inventory freshness"
python3 scripts/check-docs-inventory-fresh.py

echo "[check-docs] redirects authoring vs build output"
python3 scripts/check-docs-redirects.py

echo "[check-docs] docs readiness scorecard"
python3 scripts/score-docs-readiness.py --fail-under 88

echo "[check-docs] all checks passed"
