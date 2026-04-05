# Reference architecture — Lenses Studio

**Lenses Studio** is the **React** single-page application served at **`/studio/`** on the same Python server as **Classic** Lenses. It shares the workspace scan and JSON **`/api/...`** endpoints; the desktop **Electron** shell in **`desktop/`** can open **`/studio/`** as the default surface when **`LENSES_STUDIO_UI=1`**. Product intent: **Studio first** for new UI, then parity in Classic where feasible (see [Interface pages](/docs/interface-pages.html)).

The authoritative decision record is **ADR 001: Lenses Studio shell** — source: `docs/adr-001-lenses-studio-shell.md` in the **forge-lenses** repo; built as **[ADR 001 (handbook)](/docs/adr-001-lenses-studio-shell.html)** when you run `python3 generator/build-lenses-docs.py`.

## Runtime view

The canonical end-to-end picture is **not** duplicated here as a separate diagram: it lives in **Kitchen Sink** as numbered **data flow** and tables — see **[Lenses Studio shell](https://github.com/autowww/forgesdlc-kitchensink/blob/main/docs/design/lenses-studio-shell.md)** (§1 *End-to-end architecture*, §4 *What lives in Kitchen Sink vs Studio repo*).

Summary aligned with that doc:

1. **Electron** opens a **BrowserWindow** loading `http://127.0.0.1:<port>/studio/` (or use the browser without Electron).
2. **Python** (`lenses/serve.py`) serves **`lenses/static/studio/`** (Vite output) and **`/api/…`** JSON.
3. The **SPA** loads shared styles/scripts from **`/__ks/css/*`**, **`/__ks/js/*`** (Kitchen Sink).
4. **Preload** exposes **`window.lensesElectron`** for window controls only — no Node in the React bundle.

- **Build:** sources live in **`lenses-enterprise/`**; **`npm run build`** writes hashed assets and **`index.html`** into **`lenses/static/studio/`** (Vite `base: '/studio/'`).
- **Serve:** **`python3 -m lenses`** serves static files for **`/studio/`** and falls through to **`index.html`** for client-side routes; data uses **`fetch`** to **`http://127.0.0.1:<port>/api/...`** (same origin as the dashboard).
- **Electron:** **`desktop/`** loads the same URL; optional **`LENSES_STUDIO_UI=1`** opens **`/studio/`** instead of **`/`**. **`/enterprise/…`** redirects to **`/studio/…`**.
- **Kitchen Sink:** chart routes reuse **`/__ks/js/forge-data-charts.js`** and related CSS for parity with Classic chart pages. Design contract (what belongs in KS vs **`lenses-enterprise/`**, Electron preload): **[Kitchen Sink — Lenses Studio shell](https://github.com/autowww/forgesdlc-kitchensink/blob/main/docs/design/lenses-studio-shell.md)**.

## Components (repository layout)

| Location | Role |
|----------|------|
| **`lenses-enterprise/`** | React 19 + TypeScript + Vite source; **`npm run build`** → **`lenses/static/studio/`**; **`npm run watch`** for local iteration with the Python server on **:8080**. |
| **`lenses/static/studio/`** | Production build output (served at **`/studio/`**); do not edit by hand. |
| **`lenses/serve.py`** | HTTP server: static **`/studio/`**, JSON APIs, Classic HTML routes. |
| **`desktop/`** | Electron shell; spawns or connects to the same **`python3 -m lenses`** process. |

For build commands, tests, and Electron behavior, see the **Lenses Studio** section of the repo **[README](https://github.com/autowww/forge-lenses/blob/main/README.md)**.

## Data plane (shell to API)

Studio shell modules map to existing endpoints; there is no separate “Studio-only” workspace API for the MVP shell. Summary:

| Shell area | Typical data source |
|------------|---------------------|
| **Context / workspace label** | **`GET /api/workspace-state`** (`workspace_root`, `resolved_at`, …) |
| **Executive KPI strip** | **`GET /api/workspace-state?git_extended=1`**, **`GET /api/chart-data/overview`** (e.g. commit activity) |
| **Attention stream** | Derived **client-side** from workspace state (dirty trees, standards gaps, missing roadmap/WBS, etc.) |
| **Evidence rail** | Static routes + workspace state; links to **`/docs/`**, tutorials, search, **`/api/workspace-state`** for traceability |

Full mapping, confidence labels, and **gaps** (future APIs) are in **[Studio shell — API mapping and gaps](/docs/studio-shell-api-map.html)** (source: `docs/studio-shell-api-map.md`).

## Dual-surface parity (Studio and Classic)

New user-visible capabilities are implemented **in Lenses Studio first**, then **ported to Classic** (server-rendered HTML) so both surfaces stay equivalent unless explicitly scoped otherwise. Navigation and IA are described in **[Interface pages](/docs/interface-pages.html)**.

## Related reading

- **[Interface pages](/docs/interface-pages.html)** — plan-aware shells, Classic vs Studio, URL map, RBAC overview  
- **[HTTP API and routes](/docs/http-api-and-routes.html)** — endpoint reference used by Studio and Classic  
- **[Package architecture](/docs/architecture.html)** — package layout and server responsibilities  
- **[ADR 001 — Lenses Studio shell](/docs/adr-001-lenses-studio-shell.html)** — framework, Electron, serving, legacy redirects  
- **[Studio shell — API mapping](/docs/studio-shell-api-map.html)** — detailed shell-to-API table  
- **[Kitchen Sink — Lenses Studio shell](https://github.com/autowww/forgesdlc-kitchensink/blob/main/docs/design/lenses-studio-shell.md)** — Electron window contract, **`/__ks/`** usage, build checklist  
- **[Blueprints Wizard — usage](/docs/blueprints-wizard-usage.html)** — experimental Studio-only guided flow (feature flags, sessions, operators)
