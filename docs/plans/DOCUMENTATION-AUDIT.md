# Forge Lenses documentation audit (evidence-backed)

This artifact satisfies the “current-state audit” step of the enterprise docs refactor. It records **inventory** and **build behavior** as of the refactor implementation.

## Inventory

| Category | Location | Notes |
|----------|----------|--------|
| Public handbook (human-facing) | `docs/handbook-public/*.md` | Primary tutorials and guides; emitted on **lenses.forgesdlc.com** via `docs/nav.yml` |
| Product home | `docs/index.md` | Public landing; no longer framed as “internal reference handbook” |
| Maintainer hub | `docs/maintainer/index.md` | Former `docs/index.md` maintainer index; **full** local/site builds only |
| Navigation manifest | `docs/nav.yml` | Declares **public** build page list + sidebar grouping |
| Reference / schemas | `docs/reference/`, `docs/schemas/`, `docs/examples/` | Builder-oriented; `config-env` is in public nav |
| ADRs & design history | `docs/adr-*.md`, `docs/studio-*.md`, `docs/blueprints/` | **Public** Firebase build excludes these (not listed in `nav.yml`); included under **Maintainers & reference** in **full** profile |
| Runtime maintainer docs | `lenses/website/*.md` | HTTP API map, architecture — **full** profile only unless added to manifest |

## Build outputs

| Command / context | Output | Profile |
|-------------------|--------|---------|
| `forge-lenses-website` → `generator/build-site.py` | `website/` → Firebase **lenses-d0fdb** | **public** (`build_profile=public`, manifest-only pages) |
| `forge-lenses` → `generator/build-lenses-docs.py` | `lenses-docs/` | **full** by default (`LENSES_DOCS_BUILD_PROFILE=public` for parity check) |
| Local Lenses `/docs/` | Served from app | Uses product’s docs server, not this static tree |

## Gaps addressed by this refactor

1. **Mixed navigation** — Previously ADRs and maintainer topics appeared alongside public guides because collection included all `docs/**/*.md`. **public** builds now emit only paths declared in `docs/nav.yml`.
2. **Internal messaging on the public home** — `docs/index.md` claimed Blueprints-only canonicity and “internal handbook”; replaced with product-first positioning and cross-links.
3. **Flat sidebar** — Sidebar is grouped by manifest **sections** (forge-autodoc + `build_grouped_manifest_sidebar`).
4. **Handbook title** — `derive_handbook_title_from_readme=False` on the website build so chrome uses **Forge Lenses**, not README H1.

## Follow-on (content depth)

Many handbook chapters remain short (~&lt;600 words). Expand with time estimates, verification steps, recovery notes, and **blueprint-diagram** fences per the prompt pack (`04`–`09`).
