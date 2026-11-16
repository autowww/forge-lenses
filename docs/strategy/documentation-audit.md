---
audience: maintainer
section: strategy
nav_order: 5
description: Executive documentation audit and prioritized backlog for Forge Lenses product docs.
---

# Forge Lenses documentation audit (strategy)

This page is the **strategy-level** companion to the working notes in [`docs/plans/DOCUMENTATION-AUDIT.md`](../plans/DOCUMENTATION-AUDIT.md). Counts and nav paths are **machine-generated** — refresh them whenever `docs/nav.yml` or HTTP routes change:

```bash
python3 generator/export-docs-inventory.py
```

Output: [`documentation-inventory.json`](documentation-inventory.json).

## Snapshot (replace numbers after running the exporter)

| Metric | Source | Notes |
|--------|--------|--------|
| Public nav pages | `documentation-inventory.json` → `public_nav_page_count` (currently **41** declared paths; **40** emitted in `public` when one `public_publish: false` canary is listed) | Paths declared in [`docs/nav.yml`](../nav.yml) |
| API route signatures | Same file → `api_routes.count` | Static extract from `lenses/serve.py` via [`generator/collect_lenses_api_routes.py`](../../generator/collect_lenses_api_routes.py) |
| Route fingerprint | `api_routes.sha256_prefix` | Detect drift in CI or audit diffs |

## User / operator / builder / maintainer problems (summary)

1. **Operators** need a linear path from install → workspace → Studio/Wizard without internal jargon or ADR noise on the public site.
2. **Builders** need stable HTTP + schema references and parity checks when `serve.py` gains endpoints.
3. **Maintainers** need one orchestrated doc gate (`check-docs.sh`) and clear policies for nav, diagrams, and publishing.
4. **Everyone** benefits from **Kitchen Sink native diagrams only** in handbook-bound Markdown (no Mermaid in `docs/` per workspace policy; KS showcase demo excepted).

## Shipped vs planned / experimental

| Area | Status |
|------|--------|
| Public manifest-only builds, grouped sidebar | Shipped (`build_profile=public`, `docs/nav.yml`) |
| Maintainer-only and ADR Markdown | **Full** profile / not in public manifest |
| `public_publish` frontmatter gate | Shipped (forge-autodoc skips `false` on public builds) |
| Strategy inventory JSON | Shipped (this audit + exporter) |
| Doc quality scripts + CI | See [`docs-quality.md`](../maintainer/docs-quality.md) |
| Studio route doc coverage test | Shipped ([`studio-route-doc-coverage.yaml`](studio-route-doc-coverage.yaml) + `tests/test_studio_route_doc_coverage.py`) |

## Prompt pack (`forge_lenses_docs_refactor_prompt_pack.zip`) — coverage notes

The pack often names **`docs/public/...`** paths; this repo implements the **same intents** under **`docs/handbook-public/`** + **`docs/nav.yml`** (no separate `docs/public/` tree).

| Pack prompt | Implemented as |
|-------------|------------------|
| 01 Audit + inventory | [`documentation-audit.md`](documentation-audit.md), [`documentation-inventory.json`](documentation-inventory.json), `build/lenses-api-routes.json` from `check-docs.sh` |
| 02–03 IA + product home | [`nav.yml`](../nav.yml), [`index.md`](../index.md), tutorial hubs |
| 04–05 Tutorials + examples/diagrams | Hub pages, [`19-examples-hub.md`](../handbook-public/19-examples-hub.md), [`diagram-catalog-lenses.md`](../handbook-public/diagram-catalog-lenses.md), KS fences + `check-docs-diagrams.py` |
| 06 Studio atlas | [`14-studio-route-map.md`](../handbook-public/14-studio-route-map.md) + coverage test |
| 07 Wizard enterprise | [`08-wizard-overview.md`](../handbook-public/08-wizard-overview.md) + handbook chapters (`status: experimental` where appropriate) |
| 08 Builder reference | [`16-schemas-and-api-for-builders.md`](../handbook-public/16-schemas-and-api-for-builders.md) + `check-api-doc-coverage.py` — *not* the full multi-page `docs/public/builders/*` tree |
| 09 Enterprise ops | [`17-security-and-local-first.md`](../handbook-public/17-security-and-local-first.md) — *not* the full `docs/public/enterprise/*` page matrix |
| 10 Generator | forge-autodoc `simple_build` + [`build-lenses-docs.py`](../../generator/build-lenses-docs.py) |
| 11 Maintainer split | Public manifest + maintainer index + `public_publish` |
| 12 CI | [`check-docs.sh`](../../scripts/check-docs.sh), `check-docs-frontmatter.py`, CI workflow |
| 13 Release / cross-site | [`cross-site-map.md`](../handbook-public/cross-site-map.md), [`release-docs.md`](../maintainer/release-docs.md), support/glossary/changelog/roadmap pages |

**Remaining gaps vs literal pack filenames:** per-topic **`docs/public/examples/*.md` scenario files**, **`docs/public/studio/*.md`** subsite, **`docs/public/wizard/*.md`** mirror tree, **`docs/generated/api-routes.md`**, OpenAPI, “every tutorial uses the Outcome/Verify/Recover template verbatim”, and a generated env-var matrix — extend incrementally if product needs those artifacts under stable URLs.

Grouped to match the prompt pack:

1. **IA & governance** — Keep `nav.yml` authoritative; document deprecations and redirects in `docs/redirects.yaml` + hosting notes.
2. **Content depth** — Tutorial hubs, time estimates, verification steps, concrete scenarios; examples hub.
3. **Diagrams** — Maintain ≥10 `blueprint-diagram*` / `blueprint-diagram-ascii` fences across public docs; **no** ` ```mermaid ` in `docs/`.
4. **Builder reference** — Keep `16-schemas-and-api-for-builders.md` and `http-api-and-routes.md` aligned with `collect_lenses_api_routes.py`.
5. **Enterprise ops** — Backups, upgrades, OIDC/audit narrative in `17-security-and-local-first.md` (accurate; mark *planned* where needed).
6. **Generator** — `public_publish`, duplicate slug failure, redirect stubs, tests (forge-autodoc + forge-lenses).
7. **CI** — `check-docs.sh` (build + metadata + links + nav + diagrams + API coverage MVP).

## Related

- [`documentation-governance.md`](documentation-governance.md) — ownership and merge gates.
- [`../maintainer/docs-quality.md`](../maintainer/docs-quality.md) — how to run checks locally and in CI.
