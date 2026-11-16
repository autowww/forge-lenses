# Private Firebase handbook (`forge-lenses-website`)

The **Forge Lenses** Markdown that ships in this repo (`docs/`, `lenses/website/`, ADRs, etc.) can be published as a **static handbook** from the separate **`autowww/forge-lenses-website`** repository. That repo embeds **`forge-lenses`** as a submodule and runs **forge-autodoc** (`generator/build-site.py`) to emit HTML under **`website/`**, then deploys to Firebase Hosting project **`lenses-d0fdb`** (site id **`lenses-d0fdb`**).

## When you change Lenses docs

1. Edit and commit in **`autowww/forge-lenses`** (this repo).
2. In **`forge-lenses-website`**, bump the **`forge-lenses`** submodule (`git submodule update --remote forge-lenses` or pin a commit), run **`python3 generator/build-site.py`**, commit **`website/`** when the team tracks built output there, and deploy (CI on **`main`** or **`./deploy-websites.sh --only forge-lenses-website`** from the workspace hub).

### Static site build profiles

The website generator uses **`FORGE_LENSES_WEBSITE_BUILD_PROFILE`** (default **`public`**):

- **`public`** — emit only pages listed in **`docs/nav.yml`** (production **lenses.forgesdlc.com**).
- **`full`** — emit the entire maintainer handbook set for local review (`FORGE_LENSES_WEBSITE_BUILD_PROFILE=full python3 generator/build-site.py`).

Canonical SEO origin is **`https://lenses.forgesdlc.com`** (see **`generator/build-site.py`**).

Do **not** mirror docs by wiping the submodule’s **`.git`** (avoid blind **`rsync --delete`** into the submodule root). Prefer normal git submodule advances.

## Distinction

- **`forge-lenses`** — runtime (`python3 -m lenses`), Studio bundle, and **source** Markdown.
- **`forge-lenses-website`** — Kitchen Sink + autodoc **build** + Firebase; does not replace this repo as the spec source of truth.

## Markdown policy

Handbook-bound pages should follow workspace policy: **no Mermaid** in Markdown meant for forge-autodoc output; use lists, tables, or prose (see blueprints / Forge handbook conventions).
