# Documentation quality gates

Forge Lenses product docs (`docs/`) are validated before shipping static HTML to **lenses.forgesdlc.com**.

## One command

From the **forge-lenses** repo root (requires `PyYAML`, `markdown`, submodules initialized):

```bash
bash scripts/check-docs.sh
```

Ordered gates (mirror `scripts/check-docs.sh`, **public profile default**):

1. **`generator/collect_lenses_api_routes.py`** writes `build/lenses-api-routes.json` (route inventory fingerprint).
2. Bootstraps **`docs/generated/api-routes.{json,md}`** when missing.
3. **`scripts/check-public-doc-links.py`** blocks public → maintainer-relative Markdown hops (CI early).
4. **`generator/build-lenses-docs.py`** with `LENSES_DOCS_BUILD_PROFILE=public` → **`lenses-docs/`** + **`lenses-docs/public-manifest.json`**.
5. **`scripts/check-public-build-parity.py`** — `docs/nav.yml` ↔ manifest fingerprint / emitted pages.
6. **`scripts/check-live-docs-parity.py`** — compares production only when **`--allow-network`** is supplied.
7. **`scripts/check-lenses-doc-metadata.py --no-build-smoke`** — manifest paths resolve.
8. **`scripts/check-lenses-doc-links.py --scan-html`** — resolves links in emitted HTML.
9. **`scripts/check-docs-nav.py --strict-handbook-public`** — handbook-public completeness vs `nav.yml`.
10. **`scripts/check-docs-examples-nav.py`** — scenario hubs ↔ scenarios.
11. **`scripts/check-docs-frontmatter.py`** — required YAML metadata on manifest pages (**`NAV-FRONTMATTER.md`** contract).
12. **`scripts/check-docs-diagrams.py`** — forbids Mermaid fences; validates Kitchen Sink diagram hygiene.
13. **`scripts/check-api-doc-coverage.py`** — `/lenses/serve.py` routes mirrored in the builders corpus **and** **`docs/strategy/api-family-contracts.json`** stable/beta substrings.
14. **`scripts/check-generated-api-routes-fresh.py`** — tracked JSON matches collectors.
15. **`scripts/check-forge-docs-contract.py`** — Forge docs contract parity (when enabled).
16. **`scripts/check-handbook-tutorial-headings.py`** — scaffold + minimum depth proxies on tutorial-shaped handbook pages (SKIP list semantics documented in **`tutorial-depth-scope.md`**).
17. **`scripts/check-docs-inventory-fresh.py`** — `documentation-inventory.json` matches generator output (`--write` to refresh).
18. **`scripts/check-docs-redirects.py`** — authoring entries in **`docs/redirects.yaml`** line up with real HTML filenames.
19. **`scripts/score-docs-readiness.py --fail-under 90`** — weighted JSON + Markdown rollup under **`build/`** (signals from inventory/manifest/OpenAPI/registry).

Generators invoked during **`check-docs.sh`** (deterministic deltas):

- **`generator/export_api_routes_docs.py`** (when bootstrap needed)
- **`generator/export_schema_index.py`**
- **`generator/export_openapi.py`**
- **`scripts/check-generated-openapi-fresh.py`** — committed **`docs/generated/openapi.json`** stays identical to regenerated output.

Set **`LENSES_API_DOC_COVERAGE_WARN=1`** to downgrade HTTP coverage gaps from fail → warn during staged rollouts only.

## UX budgets & archetypes

- **`scripts/check-docs-nav-budget.py`** — validates `docs/site-nav.yaml` / `docs/nav.yml` linkage (menu counts, dropdown sizing, banned CI fixtures on public rails).
- **`scripts/check-docs-page-budget.py`** — compares approximate word counts against soft rails per `page_type`. Defaults warn only; export **`DOCS_PAGE_BUDGET_STRICT=1`** to fail CI during tightening passes.

## Inventory

Refresh machine-readable nav + fingerprint fields:

```bash
python3 generator/export-docs-inventory.py
python3 scripts/check-docs-inventory-fresh.py --write
```

Artifacts live under **`docs/strategy/documentation-inventory.json`** (referenced by the readiness score).

## Contracts & policy

- [`../NAV-FRONTMATTER.md`](../NAV-FRONTMATTER.md)
- **`scripts/check-public-doc-links.py`** (public→private bans)

## Scorecard drill-down

Detailed JSON + Markdown under **`build/docs-readiness.{json,md}`** summarize schema counts, diagrams, manifests, OpenAPI stubs, redirects, tutorial heuristics, and inventory deltas.

### Live parity drill

Operators with outbound access should run **`python3 scripts/check-live-docs-parity.py --allow-network`** immediately after Hosting deploy plus a hard refresh of any CDN/browser caches.

## CI

GitHub Actions **docs-links** job executes `scripts/check-docs.sh`; **python-tests** runs **`pytest`** (includes schema + docs fixtures).

## Related

- [`PROMPT-PACK-GAP-CHECKLIST.md`](../strategy/PROMPT-PACK-GAP-CHECKLIST.md)
- [`documentation-governance.md`](../strategy/documentation-governance.md)
- [`forge-lenses-website-handbook.md`](forge-lenses-website-handbook.md)
