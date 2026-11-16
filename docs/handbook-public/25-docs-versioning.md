---

nav_title: Docs versioning
public_publish: true
audience: public
product_area: lenses
learning_level: overview
section: resources
description: How Forge Lenses semver, handbook snapshots, and published HTML relate.
status: shipped
tier: resource
handbook_area: resources
page_type: topic
---

# Docs versioning

## Two rhythms

| Artifact | Version signal |
|----------|----------------|
| **Python package / runtime** (`python3 -m lenses`) | Git tags + **`CHANGELOG`** on **`forge-lenses`** |
| **Public handbook HTML** (**lenses.forgesdlc.com**) | Submodule pin in **`forge-lenses-website`** + Firebase deploy |

Docs can ship **hours after** runtime commits when only Markdown changes — CI still runs **`scripts/check-docs.sh`** so broken links and route drift fail PRs.

## What “same version” means for operators

1. Record **`git describe`** or **`pip show lenses`** when filing bugs.
2. When comparing Studio bundles, note **`lenses-enterprise`** git SHA embedded in maintainer release notes when relevant.

## Maintainer bump workflow

Follow the **[Publishing handbook on GitHub](https://github.com/autowww/forge-lenses/blob/main/docs/maintainer/release-docs.md)** — submodule bump → **`generator/build-site.py`** → Hosting deploy.

## Publication fingerprints

Traceable fingerprints that tie static HTML drops to **`public`** handbook sources:

| Artifact | Produced by |
| -------- | ----------- |
| `lenses-docs/public-manifest.json` | `generator/build-lenses-docs.py` (forge-autodoc) |
| `docs/generated/schema-index.json` | `generator/export_schema_index.py` |
| `docs/generated/openapi.json` | `generator/export_openapi.py` (derived route rollup) |
| `docs/strategy/documentation-inventory.json` | `generator/export-docs-inventory.py` |

Use **`scripts/check-public-build-parity.py`**, **`scripts/check-docs-inventory-fresh.py`**, and **`scripts/score-docs-readiness.py`** after `bash scripts/check-docs.sh` to prove those files match the Markdown + nav story you intend to publish.
