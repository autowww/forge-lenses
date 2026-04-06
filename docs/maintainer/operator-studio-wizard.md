# Operator notes — Studio bundle, workspace desktop, Wizard flags

**Audience:** Maintainers and operators. Not part of the public handbook on blueprints.forgesdlc.com.

## Studio bundle (blank `/studio/`)

If the Studio UI is blank or assets are missing, build the front-end bundle from the **`lenses-enterprise/`** directory in your clone:

```bash
cd lenses-enterprise
npm install
npm run build
```

Refresh `/studio/` after a successful build. For live development, `npm run watch` in `lenses-enterprise/` with the desktop app from `desktop/` and `LENSES_STUDIO_UI=1` is documented in the upstream README.

## Vite / API base / CORS

If you run a separate dev server for Studio, ensure API calls reach the Python Lenses process. See the repository README for `VITE_LENSES_API_BASE` and loopback CORS defaults.

## Electron / `lenses-desktop.json`

The desktop app may resolve workspace via `lenses-desktop.json` or a folder picker. Set **`LENSES_WORKSPACE_ROOT`** for a stable path across launches; see workspace docs in-repo.

## Blueprints Wizard — feature flags

Server and client builds can gate Wizard routes and APIs. Exact variable names and defaults are defined in the forge-lenses README and server configuration — search there for experimental Wizard flags.

## Blueprints Wizard — optional GitHub repository creation

When enabled, tokens are read from the **server environment**, not session JSON. Policy and setup are described in maintainer architecture docs under `docs/blueprints/` in this repository.
