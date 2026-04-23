# forge-lenses — reference handbook (internal)

**This is the internal maintainer handbook** for the `lenses` package: architecture, APIs, ADRs, wizard internals, and repository workflow. It is built into **`lenses-docs/`** and served at **`/docs/`** when you run Lenses locally.

## Public user guides (canonical URLs)

**End-user documentation** (how to run Lenses, use Forge Studio, and work with the Blueprints Wizard) is published only on **blueprints.forgesdlc.com**, not as a mirror of this `index.html` tree:

- **Hub:** [blueprints.forgesdlc.com/lenses/](https://blueprints.forgesdlc.com/lenses/)
- **Chapters** (same Markdown as `docs/handbook-public/` in this repo):  
  [01 Lenses overview](https://blueprints.forgesdlc.com/lenses/guides/01-lenses-overview.html) · [02 Install and run](https://blueprints.forgesdlc.com/lenses/guides/02-install-and-run.html) · [03 Workspace setup](https://blueprints.forgesdlc.com/lenses/guides/03-workspace-setup.html) · [04–07 Studio](https://blueprints.forgesdlc.com/lenses/guides/04-studio-overview.html) · [08–11 Wizard](https://blueprints.forgesdlc.com/lenses/guides/08-wizard-overview.html) · [12 Troubleshooting](https://blueprints.forgesdlc.com/lenses/guides/12-troubleshooting.html)

Do not link the public site to **`/lenses/handbook/`** — that path is a legacy redirect to the hub. Maintainer-only pages below are for **local `lenses-docs/`** or raw files on GitHub.

## Local lenses-docs build (maintainers)

The full doc set (internal + `docs/handbook-public/` + `lenses/website/`) is generated for local preview:

```bash
python3 generator/build-lenses-docs.py
```

Output: **`lenses-docs/`**. See `_load_pages()` in the generator for ordering.

**Optional — reference page preview PNGs** on this home: `pip install playwright`, run `playwright install chromium`, then:

```bash
python3 generator/build-lenses-docs.py --previews
```

or set **`LENSES_BUILD_DOC_PREVIEWS=1`**. PNGs are written under **`lenses-docs/previews/`**.

**Tutorial pipeline** (setup, submodules, publishing, extensions, Studio reference architecture) lives in **`lenses/fa-tutorial-md/`**, built with **forge-autodoc** into **`lenses/tutorials/`** and synced to repo-root **`tutorial/`** for the dashboard **Tutorial** link:

```bash
pip install markdown PyYAML
./build-fa-tutorials.sh
```

Open **`/local-site/<repo>/tutorial/index.html`** on the lenses server after building.

## Forge Studio (Lenses Studio)

React SPA at **`/studio/`** on the local Python server; shares **`/api/…`** with Classic Lenses. Build from **`lenses-enterprise/`**; architecture and Kitchen Sink reuse: see the [forge-lenses README](https://github.com/autowww/forge-lenses/blob/main/README.md#Lenses-Studio-experimental) (Lenses Studio section).

- Contributor: former interface/dashboard pages — see **`docs/maintainer/website/`**
- [Studio shell — API mapping and gaps](studio-shell-api-map.html) — shell areas to endpoints
- [Studio flow shell — MVP scope](studio-flow-shell-mvp-scope.html)
- [Studio shell — Classic parity](studio-shell-classic-parity.html)
- [ADR 001 — Lenses Studio shell](adr-001-lenses-studio-shell.html)
- [ADR 001 — Lenses Enterprise framework](adr-001-lenses-enterprise-framework.html)

## Blueprints Wizard (experimental)

Guided methodology-aligned flow in **Forge Studio** only (`/studio/blueprints/wizard/…`). Does **not** edit the **blueprints** git submodule.

**Published end-user guides:** [Wizard overview](https://blueprints.forgesdlc.com/lenses/guides/08-wizard-overview.html) (source: **`docs/handbook-public/`**).

**Maintainer / operator (local lenses-docs or GitHub):**

- [Blueprints Wizard — usage](blueprints-wizard-usage.html) — feature flags, hub vs session, telemetry, LLM trust
- [Blueprints Wizard — architecture](blueprints-wizard-architecture.html)
- [Blueprints Wizard — domain model](blueprints-wizard-domain-model.html)
- [Blueprints Wizard — file map](blueprints-wizard-file-map.html)
- [Blueprints Wizard — extending](blueprints-wizard-extending.html)
- [Blueprints Wizard — implementation plan](blueprints-wizard-implementation-plan.html)
- [ADR 002 — Blueprints Wizard trust / GitHub](adr-002-blueprints-wizard-trust-github.html)

## Reference (Python package)

Internal pages from **`docs/`** and **`lenses/website/`** (see generator for full list):

- [Roadmap — Project Management (governance)](roadmap-project-management.html) — planned PM governance capabilities (NOW / NEXT / LATER), aligned with blueprints PRODUCT-MANAGEMENT §2 / §10 / §11
- [Package architecture](architecture.html)
- [Forge plan UI map (roadmap → evidence)](ui-map-workflow.html)
- [HTTP API and routes](http-api-and-routes.html)
- [Showcase workspace (orchestration demo)](showcase-workspace.html) — env flags and fixture map for end-to-end demos
- [ADR 013 — Governance, OIDC foundation, audit (Sprint 10)](adr-013-governance-sprint10.html)
- [ADR 014 — Methodology bridge spine and registry (Sprint B1)](adr-014-bridge-spine-registry.html)
- [ADR 015 — Artifact, evidence, and decision bridge (Sprint B2)](adr-015-methodology-b2-artifacts-decisions.html)
- [ADR 016 — Agentic bridge: governed agent execution (Sprint B3)](adr-016-agentic-bridge-b3.html)
- [ADR 017 — Ceremony bridge: methodology-neutral orchestration (Sprint B4)](adr-017-ceremony-bridge-b4.html)
- [ADR 018 — Closed-loop Cursor / Claude handoff bridge (Sprint B5)](adr-018-handoff-bridge-b5.html)
- [ADR 019 — PDLC outcome bridge: launch → learning → demand (Sprint B6)](adr-019-pdlc-outcome-bridge-b6.html)
- [Workspace scan contract](workspace-scan-contract.html)
- [Registry configuration](registry-configuration.html)
- [Dashboard pages](dashboard-pages.html)
- [Requirements — WBS](requirements-wbs.html) — work breakdown (repository maintainer reference)
- [Git workflow (Forge Team tier)](git-workflow.html) — source: `docs/GIT-WORKFLOW.md`
