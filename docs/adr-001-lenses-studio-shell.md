# ADR 001: Lenses Studio shell — framework and Electron

## Status

Accepted (React SPA + Python API; Vite build in `lenses-enterprise/` → `lenses/static/studio/`).

## Context

**Lenses Studio** is the **Electron-first** control-plane UI in the `forge-lenses` repo. The former name “Lenses Enterprise UI” was **renamed** to avoid collision with the **Enterprise** **subscription** tier. Studio shares the **Python server** (`python3 -m lenses`) and JSON APIs with Classic Lenses. The desktop shell lives under `desktop/`; the SPA is served at **`/studio/`** from `lenses/static/studio/`.

**Dual-surface parity:** New UI is implemented **in Studio first**, then **duplicated in Classic** (server-rendered) so both surfaces stay equivalent unless explicitly scoped otherwise.

## Decision

1. **Renderer framework:** **React 19 + TypeScript + Vite** in `lenses-enterprise/`, `base: '/studio/'`, `react-router-dom` for client-side routes; Python serves **`index.html`** for unknown **`/studio/…`** paths (hashed assets 404 when missing).
2. **Electron:** Keep **contextIsolation: true**, **nodeIntegration: false**; use **preload** only for audited OS bridges if needed. Data access uses **`fetch`** to `http://127.0.0.1:<port>/api/…` on the same origin as the Python server.
3. **Styling:** Reuse **Forge/Kitchen Sink CSS variables** (amber/cyan/surfaces) for parity with `forgesdlc-pack-enterprise.css` semantics on static sites.
4. **Serving:** The Python server exposes **`/studio/`** static files from `lenses/static/studio/` so the Electron `BrowserWindow` can load `http://127.0.0.1:<port>/studio/` without a separate dev server in production.
5. **Legacy URLs:** **`/enterprise`** and **`/enterprise/…`** respond with **302** to **`/studio/`** and **`/studio/…`**.

## Consequences

- A **Vite** project lives in `lenses-enterprise/` with `build.outDir` pointing at `lenses/static/studio` and `npm run build` before packaging Electron.
- **RBAC** remains enforced on the server; the renderer must not trust paths from the client without validation.

## Electron entry

Set **`LENSES_STUDIO_UI=1`** when starting the desktop app to open **`/studio/`** instead of **`/`**. **`LENSES_ENTERPRISE_UI=1`** remains accepted as a legacy alias.

## Related documentation

- **Kitchen Sink (canonical guidelines):** `forgesdlc-kitchensink/docs/design/lenses-studio-shell.md` — Electron window contract, preload API, `/__ks/` assets, what belongs in KS vs `lenses-enterprise/`, build checklist.
- **Enterprise UI theme packs (static sites):** `forgesdlc-kitchensink/docs/design/forge-enterprise-ui.md`.
- **Product IA (Classic vs Studio):** `forge-lenses/lenses/website/interface-pages.md`.
