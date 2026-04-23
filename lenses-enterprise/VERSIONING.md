# Forge Studio — version policy

This document applies to **Forge Studio**, the React + Vite SPA in **`lenses-enterprise/`**, built into **`lenses/static/studio/`** and served at **`/studio/`** by the **forge-lenses** Python package.

**Shared policy** (semver surfaces, changelog discipline, optional git hook) lives in Blueprints: **`blueprints/sdlc/methodologies/forge/setup/VERSIONING-AND-RELEASES.md`**. This file keeps **Studio-specific** rules (routes, `/api/*`, Electron) below.

## Semantic versioning (Studio)

The **Studio** release line is **`MAJOR.MINOR.PATCH`** in **`package.json`** (`version` field), following [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html):

| Bump | When |
|------|------|
| **MAJOR** | Breaking changes for Studio users: removed or renamed routes, incompatible API contract changes for **`/api/*`** used only by Studio, required browser baseline change, or other changes that force coordinated upgrades or break saved local state formats owned by Studio. |
| **MINOR** | New user-visible features, new routes, or new optional capabilities without breaking existing flows. |
| **PATCH** | Bug fixes, visual polish, accessibility improvements, performance, or internal refactors with no intended user-visible behavior change. |

Pre-release identifiers (e.g. **`1.1.0-beta.1`**) are allowed if you need to signal instability; prefer **MINOR** bumps for experimental features that ship behind flags when possible.

## Relationship to **forge-lenses** (Python)

The **forge-lenses** repository versions the **server and Classic UI** separately from this **`package.json`** line. In practice:

- A given **Studio** **PATCH** should remain compatible with the **forge-lenses** commit it ships beside (same tree). If the Python server introduces a **breaking** API change for Studio, bump Studio **MAJOR** or **MINOR** as appropriate and document it in **[CHANGELOG.md](./CHANGELOG.md)**.
- Prefer **additive** API changes (new fields, new endpoints) for server updates that older Studio bundles might still call during local dev; use deprecation periods when feasible.

## Changelog and releases

1. Update **[CHANGELOG.md](./CHANGELOG.md)** under **`[Unreleased]`** as you merge work; at release time, rename that section to a dated **`[x.y.z]`** heading and start a fresh **`[Unreleased]`**.
2. Bump **`package.json`** `version` to match the release you just documented.
3. Optionally publish a **[GitHub Release](https://github.com/autowww/forge-lenses/releases)** for the **forge-lenses** repo (even without attachments) and include Studio highlights when Studio changed—see the root **[README.md](../README.md)** release notes bullet.

**Automation (optional):** with **`.forge/version-release.json`** at the repo root and `bash blueprints/sdlc/methodologies/forge/setup/install-version-release-hook.sh`, commits that touch **`lenses-enterprise/`**, **`lenses/`**, or **`desktop/`** append a bullet under **`[Unreleased]`** from the commit subject, then **auto-increment `PATCH`** in **`lenses-enterprise/package.json`** when you did not edit the **`version`** field yourself in that commit. When **`MAJOR`** or **`MINOR`** increases vs the parent commit (human line change), the hook folds **`[Unreleased]`** into the new version heading (not on PATCH-only bumps). Use **`[skip-changelog]`** in the commit message to skip the hook. See Blueprints **`VERSIONING-AND-RELEASES.md`**.

### Automatic PATCH on Studio build

Each **`npm run build`** and **`npm run build:museum`** runs **`node scripts/bump-studio-patch-version.mjs`** first, which increments **`MAJOR.MINOR.PATCH`** by **one PATCH** in **`package.json`** (only the numeric core: anything after the third number group, such as **`-beta.1`** or **`+metadata`**, is preserved unchanged). The Vite step then bundles that new version. **`npm run watch`** and **`npm run dev`** do **not** bump the version.

To run a production build **without** mutating **`package.json`** (e.g. CI compile check): **`SKIP_STUDIO_VERSION_BUMP=1 npm run build`**.

## Build metadata (not semver)

Each **`npm run build`** (and each rebuild under **`npm run watch`**) embeds via the **`virtual:studio-build-meta`** Vite plugin:

- **Release version** — from **`package.json`** at bundle build time after the optional **PATCH** bump described above (so each **`npm run build`** normally advances PATCH once unless **`SKIP_STUDIO_VERSION_BUMP`** is set).
- **Source commit** — `git rev-parse --short HEAD` from **`lenses-enterprise/`**, or **`unknown`** if unavailable.
- **Build time** — ISO-8601 UTC timestamp when that bundle was produced.

These strings are for **support and reproducibility**; they do not replace semver. The virtual module is **invalidated on every Rollup `buildStart`**, so watch-mode rebuilds get a fresh **build time** (and commit when `HEAD` moves). **`npm run watch`** does not bump **`package.json`**, so the bundled semver stays whatever was on disk when you started the watcher; run **`npm run build`** to advance **PATCH** again.

**About → Version** in the UI shows one line: **`{semver} · {commit|no-git} · {ISO UTC time}`** — the leading semver matches **`package.json`** after the pre-build bump (when enabled); commit and UTC time still distinguish bundles built at the same PATCH.

The **Electron** desktop shell (`forge-lenses/desktop/`) reads **`lenses/static/studio/studio-build-meta.json`** (written next to **`index.html`** on each Studio **`npm run build`**) for the frameless startup splash line **`v{semver} · {commit|no-git} · {ISO UTC}`**. If that file is missing (Studio not built yet), it falls back to **`lenses-enterprise/package.json`** plus **`git rev-parse --short HEAD`** and omits the timestamp segment (`—`).
