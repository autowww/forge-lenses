# Prompt-pack gap closure checklist (`forge_lenses_docs_refactor_prompt_pack`)

Tracks implementation status versus **`00-README.md`** acceptance criteria using **`docs/handbook-public/`** + **`docs/nav.yml`** (not literal **`docs/public/`** paths).

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 01 | Evidence-backed audit (`docs/plans/DOCUMENTATION-AUDIT.md`, strategy docs) | Done |
| 02 | Grouped nav (`docs/nav.yml`) — Start, tutorials 101/201/301, product areas, enterprise, builders, troubleshooting, resources | Done |
| 03 | Product home (`docs/index.md`) + get-started ladder pages | Done |
| 04 | Tutorial ladder depth (`handbook-public/*`) | Ongoing content expansion |
| 05 | Examples hub (`19-examples-hub.md`, `docs/examples/*`, scenario stubs `examples-scenario-*.md`) + diagram catalog (`diagram-catalog-lenses.md`) | Done |
| 06–07 | Studio + Wizard chapters + route/trust docs | Done |
| 08 | Builder split (`builders-*.md`), generated routes (`docs/generated/api-routes.{json,md}`, `generator/export_api_routes_docs.py`) | Done |
| 09 | Enterprise hub (`enterprise-index.md`) + topical pages + consolidated **`17-security-and-local-first.md`** | Done |
| 10 | forge-autodoc build (`generator/build-lenses-docs.py`), manifest-driven **public** profile | Done |
| 11 | Maintainer split (`docs/maintainer/index.md`) | Done |
| 12 | **`scripts/check-docs.sh`** gates (links, diagrams, API corpus, generated-route freshness, **`scripts/check-handbook-tutorial-headings.py`**) | Done |
| 13 | Cross-site map (`cross-site-map.md`), release/versioning stubs (`24-release-notes.md`, `25-docs-versioning.md`), support/glossary/changelog/roadmap resources | Done |
| 13 | **`docs/redirects.yaml`** populated entries | Add only when legacy inbound URLs confirmed |

Maintenance: whenever **`serve.py`** routes change, run **`python3 generator/export_api_routes_docs.py`** before merging.
