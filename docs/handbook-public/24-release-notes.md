---

nav_title: Release notes
public_publish: true
audience: public
product_area: lenses
learning_level: overview
section: resources
description: Where Forge Lenses runtime releases and handbook updates are announced.
status: shipped
tier: resource
handbook_area: resources
page_type: topic
---

# Release notes

## Runtime (forge-lenses)

- **Tagged builds** — **[GitHub Releases](https://github.com/autowww/forge-lenses/releases)** for semver tags and binaries/source snapshots.
- **Commit history** — default branch commits between tags include fixes not yet packaged.

## Handbook (this site)

Static HTML under **[lenses.forgesdlc.com](https://lenses.forgesdlc.com)** tracks **`docs/`** on **`forge-lenses`** plus the **`forge-lenses-website`** build (Firebase Hosting).

| Topic | Detail |
|-------|--------|
| **Preview locally** | `LENSES_DOCS_BUILD_PROFILE=public bash scripts/check-docs.sh` |
| **Evidence bundle** | `lenses-docs/public-manifest.json`, `docs/generated/schema-index.json`, `docs/generated/openapi.json`, `docs/strategy/documentation-inventory.json`, plus `build/docs-readiness.{json,md}` from `scripts/score-docs-readiness.py` |
| **Publish** | Maintainer handbook on **[release workflow (GitHub)](https://github.com/autowww/forge-lenses/blob/main/docs/maintainer/release-docs.md)** and **[publishing overview (GitHub)](https://github.com/autowww/forge-lenses/blob/main/docs/maintainer/publishing.md)** |

### May 2026 — docs gap-bridge rollup

Aligned release engineering + handbook CI now share the same toolchain: **`check-public-doc-links`**, **`public-manifest.json` parity**, richer JSON schema fixtures (12 bundles), **`export_schema_index.py`**, **`export_openapi.py`**, inventory freshness guards, redirects validator, and a readiness scorecard surfaced for operators validating **lenses.forgesdlc.com** freshness.

See also **[Docs versioning](25-docs-versioning.md)** for how handbook freshness relates to git tags.
