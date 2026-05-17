# Publishing (handbook)

Maintainer workflow for **lenses.forgesdlc.com** and related artifacts lives in **[release-docs.md](release-docs.md)**. Use that document as the single source of truth for submodule bumps, static builds, and Firebase deploy steps.

## Proof stack (recommended)

Before cutting a handbook release:

1. Run **`bash scripts/check-docs.sh`** — builds `lenses-docs/`, verifies nav/frontmatter/link/diagram/tutorial gates, emits **`lenses-docs/public-manifest.json`** and compares against `docs/nav.yml` (**`scripts/check-public-build-parity.py`**).
2. Commit **`docs/strategy/documentation-inventory.json`** whenever doc structure changes materiality (or run **`python3 scripts/check-docs-inventory-fresh.py --write`** beforehand).
3. After Firebase deploy (or before declaring done), optionally run **`python3 scripts/check-live-docs-parity.py --allow-network`** to compare production HTML meta against the repository manifest expectations.

Artifacts such as **`docs/generated/openapi.json`** (partial, machine-oriented) regenerate during `check-docs.sh` for auditors and tooling.

## See also

- Public **[Release notes](../handbook-public/24-release-notes.md)** and **[Docs versioning](../handbook-public/25-docs-versioning.md)**
