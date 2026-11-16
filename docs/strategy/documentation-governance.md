# Documentation governance

Canonical policies for **Forge Lenses** Markdown under [`docs/`](../index.md) and static handbook output.

## Ownership

- **Product handbook** (`docs/handbook-public/`, `docs/index.md`) — Docs + engineering; public voice (no “internal handbook” framing on the product home).
- **Strategy / audit** (`docs/strategy/`) — Architecture + PM-style positioning; may be maintainer-facing (`audience: maintainer`) when needed.
- **Maintainer hub** (`docs/maintainer/`) — Contributor workflows, CI, website deploy notes.

## Merge gates

- **`bash scripts/check-docs.sh`** must pass before publishing static HTML.
- **Nav changes** — Any new `docs/handbook-public/*.md` file must be registered in [`docs/nav.yml`](../nav.yml).
- **HTTP surface** — New routes in `lenses/serve.py` must be mentioned in builder docs (see [`docs-quality.md`](../maintainer/docs-quality.md)).
- **Diagrams** — Use Kitchen Sink fences only (`blueprint-diagram`, `blueprint-diagram-expand`, `blueprint-diagram-ascii`). Do **not** introduce ` ```mermaid ` blocks under `docs/`. The only Mermaid exception is the historical Kitchen Sink showcase museum (`forgesdlc-kitchensink/generator/build-showcase.py` output), which must **not** be copied as a pattern into product docs (see workspace `.cursor/rules/no-mermaid-diagrams.mdc`).

## Deprecation and URLs

- Prefer **additive** handbook URLs. When renaming emitted HTML slugs, add entries to [`docs/redirects.yaml`](../redirects.yaml) and document any **Firebase Hosting** redirect rules in [`release-docs.md`](../maintainer/release-docs.md).

## Security & accuracy

- No secrets, tokens, or customer data in examples.
- Label **experimental** surfaces honestly (Wizard flags, OIDC roadmap, Fleet-only flows).
- Cross-check LLM / Fleet claims against shipped code when touching runtime chapters.
