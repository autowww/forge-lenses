---
audience: maintainer
section: maintainers
status: internal
nav_title: Maintainer handbook index
description: Internal index for contributors — ADRs, architecture, and publishing workflow.
---

# forge-lenses — maintainer handbook index

**This page is for contributors and operators** who need architecture notes, ADRs, Wizard implementation detail, and the full static doc build (including pages not shipped on the lean public site).

Human-facing product documentation for end users and evaluators is published at **[lenses.forgesdlc.com](https://lenses.forgesdlc.com)**. The **[Blueprints Lenses hub](https://blueprints.forgesdlc.com/lenses/)** remains the methodology quickstart companion.

## Public vs maintainer builds

- **`build_profile=public`** (Firebase / `forge-lenses-website`) — only paths declared in [`docs/nav.yml`](../nav.yml).
- **`build_profile=full`** (`generator/build-lenses-docs.py` default) — all handbook Markdown under `docs/` plus this tree, grouped with **Maintainers & reference** at the end of the sidebar.

See also [`docs/NAV-FRONTMATTER.md`](../NAV-FRONTMATTER.md) and [`docs/plans/DOCUMENTATION-AUDIT.md`](../plans/DOCUMENTATION-AUDIT.md).

See also [`docs-quality.md`](docs-quality.md) for **`scripts/check-docs.sh`**, diagram policy, and CI gates; [`release-docs.md`](release-docs.md) for publishing; [`../strategy/documentation-governance.md`](../strategy/documentation-governance.md) for ownership and deprecations.

## Local lenses-docs build

```bash
python3 generator/build-lenses-docs.py
```

Output: **`lenses-docs/`**. Optional reference PNG previews require Playwright — see generator docstring.

## Tutorial pipeline (dashboard “Tutorial” link)

`lenses/fa-tutorial-md/` → forge-autodoc → `lenses/tutorials/` / repo `tutorial/`.

```bash
pip install markdown PyYAML
./build-fa-tutorials.sh
```

## Forge Studio (Lenses Studio)

React SPA at **`/studio/`**; shares `/api/…` with Classic Lenses. Build from **`lenses-enterprise/`**.

- Interface / dashboard design notes — **`docs/maintainer/website/`**
- [Studio shell — API mapping and gaps](../studio-shell-api-map.md)
- [Studio flow shell — MVP scope](../studio-flow-shell-mvp-scope.md)
- [Studio shell — Classic parity](../studio-shell-classic-parity.md)
- [ADR 001 — Lenses Studio shell](../adr-001-lenses-studio-shell.md)
- [ADR 001 — Lenses Enterprise framework](../adr-001-lenses-enterprise-framework.md)

## Blueprints Wizard (experimental)

Guided flow in **Forge Studio** only (`/studio/blueprints/wizard/…`). Does **not** edit the **blueprints** submodule.

**User-facing guides** (also on lenses.forgesdlc.com): start from [Wizard overview](../handbook-public/08-wizard-overview.md).

**Maintainer / implementation:**

- [Blueprints Wizard — usage](../blueprints/wizard-usage.md)
- [Blueprints Wizard — architecture](../blueprints/wizard-architecture.md)
- [Blueprints Wizard — domain model](../blueprints/wizard-domain-model.md)
- [Blueprints Wizard — file map](../blueprints/wizard-file-map.md)
- [Blueprints Wizard — extending](../blueprints/wizard-extending.md)
- [Blueprints Wizard — implementation plan](../blueprints/wizard-implementation-plan.md)
- [ADR 002 — Blueprints Wizard trust / GitHub](../adr-002-blueprints-wizard-trust-github.md)

## Package reference & ADRs

- [Roadmap — Project Management (governance)](../roadmap-project-management.md)
- [Package architecture](../../lenses/website/architecture.md)
- [Forge plan UI map (roadmap → evidence)](../website/ui-map-workflow.md)
- [HTTP API and routes](../../lenses/website/http-api-and-routes.md)
- [Showcase workspace (orchestration demo)](../showcase-workspace.md)
- [ADR 013 — Governance, OIDC foundation, audit (Sprint 10)](../adr-013-governance-sprint10.md)
- [ADR 014 — Methodology bridge spine and registry (Sprint B1)](../adr-014-bridge-spine-registry.md)
- [ADR 015 — Artifact, evidence, and decision bridge (Sprint B2)](../adr-015-methodology-b2-artifacts-decisions.md)
- [ADR 016 — Agentic bridge: governed agent execution (Sprint B3)](../adr-016-agentic-bridge-b3.md)
- [ADR 017 — Ceremony bridge: methodology-neutral orchestration (Sprint B4)](../adr-017-ceremony-bridge-b4.md)
- [ADR 018 — Closed-loop Cursor / Claude handoff bridge (Sprint B5)](../adr-018-handoff-bridge-b5.md)
- [ADR 019 — PDLC outcome bridge: launch → learning → demand (Sprint B6)](../adr-019-pdlc-outcome-bridge-b6.md)
- [Workspace scan contract](../../lenses/website/workspace-scan-contract.md)
- [Registry configuration](../website/registry-configuration.md)
- [Dashboard pages](../website/dashboard-pages.md)
- [Requirements — WBS](../requirements/WBS.md)
- [Git workflow (Forge Team tier)](../GIT-WORKFLOW.md)

## Website / Firebase

[`forge-lenses-website-handbook.md`](forge-lenses-website-handbook.md) describes the static handbook pipeline and submodule bump workflow.
