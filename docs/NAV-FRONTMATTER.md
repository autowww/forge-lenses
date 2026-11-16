# Navigation manifest & frontmatter (Forge Lenses)

## `docs/nav.yml`

- **Single source of truth** for which pages appear on **lenses.forgesdlc.com** (`build_profile=public` in forge-autodoc).
- `enforce_public_frontmatter: true` makes the build fail if any listed page lacks required YAML keys (see below).

## Frontmatter on public pages

Use a leading YAML block on every file listed in `nav.yml`:

```yaml
---
audience: public
section: product
learning_level: overview
product_area: lenses
status: shipped
tier: overview
handbook_area: lenses
public_publish: true
page_type: landing
nav_title: Short title for sidebar and tabs
description: One-line summary for SEO / summaries
---
```

### Required keys (`scripts/check-docs-frontmatter.py` + build)

Every `nav.yml` Markdown target must declare:

| Key | Allowed / notes |
|-----|-----------------|
| `audience` | `public` only (maintainer narratives must not ship on public-only nav paths) |
| `section` | Matches a section `id` in `docs/nav.yml` |
| `learning_level` | `101`, `201`, `301`, `overview`, or `reference` (use `overview` / `reference` outside tutorial tiers) |
| `product_area` | e.g. `lenses`, `studio`, `wizard`, `builders` |
| `status` | `shipped`, `planned`, `internal`, … |
| `nav_title` | Human label for sidebar / breadcrumbs |
| `description` | Non-empty sentence or clause for inventory + meta |
| `tier` | e.g. `overview`, `tutorial`, `studio`, `builder`, `wizard`, `resource`, … |
| `handbook_area` | Aligns reader intent (mirror `section` where helpful, but may be narrower) |
| `public_publish` | `true` / `false` — `false` skips **public-profile** HTML emission while keeping contributor narratives reviewable locally |
| `page_type` | Archetype label enforced by `scripts/check-docs-page-budget.py` (`landing`, `tutorial`, `reference`, … — see **`docs/design/lenses-docs-navigation.md`**) |

Suppressed-but-listed pages (**`public_publish: false`**) were historically used for CI fixtures; **`docs/handbook-public/98-doc-ci-canary.md`** now stays **out** of `nav.yml` while retaining frontmatter checks via `scripts/check-docs-frontmatter.py`.

### Optional keys

| Key | Purpose |
|-----|---------|
| `nav_order` | Integer sort hint when not using manifest order (legacy; manifest wins for public) |
| `hide_from_nav` | `true` to omit from sidebar (page still builds if collected) |

## Public Markdown link policy

- Public nav pages **must never** contain relative Markdown links into maintainer/strategy/GitHub-private paths documented in `scripts/check-public-doc-links.py`.
- Prefer **`https://github.com/autowww/forge-lenses/...`** for maintainer-only narratives referenced from public pages.

## Maintainer pages

Files under `docs/maintainer/` (and other internal sources) should use:

```yaml
---
audience: maintainer
section: maintainers
status: internal
---
```

They appear in **full** builds at the end under **Maintainers & reference** unless listed in the manifest.

## Diagrams

Use Kitchen Sink fences (`blueprint-diagram`, `blueprint-diagram-expand`, `blueprint-diagram-ascii`) with `key:`, `alt:`, and optional `caption:`. Do **not** use Mermaid in handbook-bound Markdown (workspace policy).
