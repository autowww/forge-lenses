# Forge Lenses handbook navigation model

This note complements **`docs/nav.yml`** (vertical manifest ordering + public-profile membership) and **`docs/site-nav.yaml`** (horizontal product IA consumed by Kitchen Sink **forge-autodoc**).

## Files & responsibilities

| File | Purpose |
|------|---------|
| `docs/nav.yml` | Canonical ordered list of Markdown paths grouped into sections (`id`, `title`, `entries`). Public-profile builds iterate this list exactly (minus frontmatter-suppressed pages). |
| `docs/site-nav.yaml` | Fleet-compatible horizontal manifest (`brand_label`, `home_href_md`, `top_level`). Each row maps to **one** sidebar context via `lens_manifest_sections`. |
| `generator/build-lenses-docs.py` | Sets `site_nav_yaml`, `handbook_sidebar_brand_tagline`, `handbook_homepage_md_rel`, and (for `public`) `lenses_public_manifest_site`. |

## Rendering rules

1. **Top navigation** — Bootstrap navbar rendered by `forge_autodoc.fleet_site_nav.build_top_nav_html`. Forge Lenses menus typically link directly to each IA hub (`hub_href_md`) instead of Fleet-style prefix dropdowns.
2. **Contextual rail** — Only `nav.yml` sections listed in `lens_manifest_sections` for the active top menu appear in the grouped sidebar (`forge_autodoc.simple_build`). Legacy Fleet repos continue using prefix-based dropdown mode when `lens_manifest` is absent.
3. **Collapse threshold** — Rails collapse additional links per manifest section behind `<details>` once the rendered link count exceeds **10** (`collapse_extra_after`, set from `forge_autodoc.simple_build`).
4. **Mobile offcanvas** — Uses the **same grouped manifest HTML** as desktop so parity acceptance holds.

## Budget gates

`scripts/check-docs-nav-budget.py` enforces:

- ≤ **7** entries under `site-nav.yaml → top_level`.
- ≤ **8** explicit dropdown children (reserved for future grouped dropdowns).
- `dropdown_max_items`, when authored, must also stay ≤ **8**.
- **No** `docs/handbook-public/98-doc-ci-canary.md` entry inside `docs/nav.yml`.
- Every `lens_manifest_sections` entry resolves to an existing `nav.yml` section `id`.

## Page archetypes

`page_type` frontmatter feeds soft budgets via `scripts/check-docs-page-budget.py`. Allowed tokens today:

`landing`, `hub`, `tutorial`, `how-to`, `concept`, `topic`, `reference`, `troubleshooting`, `runbook`, `internal-ci`.

The **`internal-ci`** archetype applies only to **`docs/handbook-public/98-doc-ci-canary.md`**, which deliberately stays outside `nav.yml` while continuing to participate in contributor-facing checks.

## Chrome subtitle

The handbook sidebar subtitle (“Product docs · local-first workspace”) is injected through `HandbookBuildConfig.handbook_sidebar_brand_tagline` so other Kitchen Sink consumers remain unchanged unless they opt in.
