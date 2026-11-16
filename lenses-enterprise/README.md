# Lenses Studio — React + TypeScript + Vite

**Forge Studio** SPA: production build writes to **`../lenses/static/studio/`** (served at **`/studio/`**). Use **Node.js ≥ 20.12** (see **`engines`** in `package.json`) — Vitest 4 / Rolldown require `util.styleText`.

## Version and release notes

| Artifact | Purpose |
|----------|---------|
| **`package.json` → `version`** | Studio [semver](https://semver.org/) — bump when you cut a release (see **[VERSIONING.md](./VERSIONING.md)**). |
| **[CHANGELOG.md](./CHANGELOG.md)** | User-facing history of major fixes and features (Keep a Changelog style). |
| **[VERSIONING.md](./VERSIONING.md)** | When to bump major/minor/patch, and how Studio relates to the **forge-lenses** Python server. |

The built app shows **version · git short SHA** in the **footer**; **Settings (gear) → About Forge Studio** lists full build metadata and links to the changelog and version policy.

## Architecture and Kitchen Sink

Architecture, Electron window contract, **`/__ks/`** assets, and what belongs in KS vs this package: **`forgesdlc-kitchensink/docs/design/lenses-studio-shell.md`** (sibling repo; from here: **`../../forgesdlc-kitchensink/docs/design/lenses-studio-shell.md`**). Sync React primitives from KS: **`npm run sync-kitchensink-react`**.

## Static museum (ks.forgesdlc.com)

**`npm run build:museum`** sets **`VITE_STATIC_MUSEUM=true`** so **`GET /api/…`** reads JSON from **`/studio/museum-data/`** (fixtures live in **`forgesdlc-kitchensink/museum/museum-data/`**). Use **`npm run build`** for normal local development against the Python server.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Vite dev server (proxies `/api` to :8080 when configured). |
| `npm run build` | Typecheck + production bundle into `../lenses/static/studio/`. |
| `npm run watch` | Rebuild bundle on save (single-port workflow with Python on :8080). |
| `npm test` | Vitest. |
| `npm run lint` | ESLint. |
| `npm run test:e2e:docs-health` | Playwright: Docs health **scan** regression plus **session** UI tests (throwaway workspace via `scripts/e2e-lenses-with-fixture.sh`). See **[`../docs/maintainer/docs-health-mvp.md`](../docs/maintainer/docs-health-mvp.md)** (Playwright section). |

See the **forge-lenses** root **[README.md](../README.md)** for full Studio workflow, Electron, and LLM setup.
