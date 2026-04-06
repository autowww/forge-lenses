# forge-lenses — reference handbook (internal)

**This is the internal maintainer handbook** for the `lenses` package: architecture, APIs, ADRs, wizard internals, and repository workflow. It is built into **`lenses-docs/`** and served at **`/docs/`** when you run Lenses locally.

**User-facing documentation** (how to use Lenses, Forge Studio, and the Blueprints Wizard) is published at **[blueprints.forgesdlc.com/lenses/](https://blueprints.forgesdlc.com/lenses/)** and maintained under **`docs/website/`** in this repository.

## Published user guide (mirror of website content)

These pages are also emitted to the public handbook when `blueprints-website` builds the lenses subtree. Local slugs match the published site:

- [User guide home](home.html) — start here for end-user topics
- [Interface pages](interface-pages.html) — Classic vs Forge Studio, plan-aware shells
- [Dashboard pages](dashboard-pages.html) — major screens and routes
- [Registry configuration](registry-configuration.html) — `workspace-registry.json`, RBAC overview
- [Forge plan UI map (roadmap → evidence)](ui-map-workflow.html) — `/plan` lens
- [Blueprints Wizard — guides](wizard-index.html) — progressive wizard help (101 / 201 / 301)

**Tutorial pipeline** (setup, submodules, publishing, extensions, Studio reference architecture) lives in **`lenses/fa-tutorial-md/`**, built with **forge-autodoc** into **`lenses/tutorials/`** and synced to repo-root **`tutorial/`** for the dashboard **Tutorial** link:

```bash
pip install markdown PyYAML
./build-fa-tutorials.sh
```

Open **`/local-site/<repo>/tutorial/index.html`** on the lenses server after building.

## Forge Studio (Lenses Studio)

React SPA at **`/studio/`** on the local Python server; shares **`/api/…`** with Classic Lenses. Build from **`lenses-enterprise/`**; architecture and Kitchen Sink reuse: see the [forge-lenses README](https://github.com/autowww/forge-lenses/blob/main/README.md#Lenses-Studio-experimental) (Lenses Studio section).

- [Interface pages](interface-pages.html) — plan-aware shells, Classic vs Lenses Studio, shared IA, backend URL map, open vs team (RBAC)
- [Studio shell — API mapping and gaps](studio-shell-api-map.html) — shell areas to endpoints
- [Studio flow shell — MVP scope](studio-flow-shell-mvp-scope.html)
- [Studio shell — Classic parity](studio-shell-classic-parity.html)
- [ADR 001 — Lenses Studio shell](adr-001-lenses-studio-shell.html)
- [ADR 001 — Lenses Enterprise framework](adr-001-lenses-enterprise-framework.html)

## Blueprints Wizard (experimental)

Guided methodology-aligned flow in **Forge Studio** only (`/studio/blueprints/wizard/…`). Does **not** edit the **blueprints** git submodule. **Operators:** [wizard usage](blueprints-wizard-usage.html).

**End-user guides** (published): [Wizard guides index](wizard-index.html) — see also **`docs/website/wizard/`**.

- [Blueprints Wizard — usage](blueprints-wizard-usage.html) — feature flags, hub vs session, telemetry, LLM trust
- [Blueprints Wizard — architecture](blueprints-wizard-architecture.html)
- [Blueprints Wizard — domain model](blueprints-wizard-domain-model.html)
- [Blueprints Wizard — file map](blueprints-wizard-file-map.html)
- [Blueprints Wizard — extending](blueprints-wizard-extending.html)
- [Blueprints Wizard — implementation plan](blueprints-wizard-implementation-plan.html)
- [ADR 002 — Blueprints Wizard trust / GitHub](adr-002-blueprints-wizard-trust-github.html)

## Reference (Python package)

Built by `generator/build-lenses-docs.py` from **`docs/`** (internal pages), **`docs/website/`** (user-facing pages; flat slugs), and **`lenses/website/`** (maintainer package reference). See `_load_pages()` in the generator for ordering.

- [Roadmap — Project Management (governance)](roadmap-project-management.html) — planned PM governance capabilities (NOW / NEXT / LATER), aligned with blueprints PRODUCT-MANAGEMENT §2 / §10 / §11
- [Package architecture](architecture.html)
- [Forge plan UI map (roadmap → evidence)](ui-map-workflow.html)
- [HTTP API and routes](http-api-and-routes.html)
- [Workspace scan contract](workspace-scan-contract.html)
- [Registry configuration](registry-configuration.html)
- [Dashboard pages](dashboard-pages.html)
- [Requirements — WBS](requirements-wbs.html) — work breakdown (repository maintainer reference)
- [Git workflow (Forge Team tier)](git-workflow.html) — source: `docs/GIT-WORKFLOW.md`

**Optional — reference page preview images** on this home: install [html2image](https://pypi.org/project/html2image/) and Chromium or Google Chrome, then `python3 generator/build-lenses-docs.py --previews` or set **`LENSES_BUILD_DOC_PREVIEWS=1`**. PNGs are written under **`lenses-docs/previews/`**.
