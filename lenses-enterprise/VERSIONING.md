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

## Build metadata (not semver)

Each **`npm run build`** embeds:

- **`VITE_STUDIO_VERSION`** — from **`package.json`** at build time.
- **`VITE_STUDIO_BUILD_COMMIT`** — `git rev-parse --short HEAD` from **`lenses-enterprise/`**, or **`unknown`** if unavailable.
- **`VITE_STUDIO_BUILD_TIME`** — ISO-8601 UTC timestamp when Vite produced the bundle.

These strings are for **support and reproducibility**; they do not replace semver.

The **Electron** desktop shell (`forge-lenses/desktop/`) shows **`v{version} · {commit}`** on its frameless startup splash by reading **`lenses-enterprise/package.json`** and **`git rev-parse --short HEAD`** at app launch (not the SPA bundle’s build time). After load, the in-app footer still reflects the **Vite**-inlined metadata from when `npm run build` last ran.
