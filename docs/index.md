---

nav_title: Home
audience: public
section: product
learning_level: overview
product_area: lenses
tier: product
handbook_area: product
status: shipped
public_publish: true
description: Install Forge Lenses locally, navigate Classic Lenses, Forge Studio, and the Blueprints Wizard, and integrate with schemas and APIs—without sending code to a SaaS reviewer.
page_type: landing
---

# Forge Lenses — see your Forge workspace locally

Forge Lenses is a **local Python server and browser dashboard** for Forge SDLC–aligned repos: inspect plans, sibling projects, documentation health, and workshop flows entirely on machines you control.

This site (**[lenses.forgesdlc.com](https://lenses.forgesdlc.com)**) is the **canonical product documentation home** for Lenses—install guides, tutorials, enterprise posture, and builder-facing API/schema notes. **[Forge SDLC](https://forgesdlc.com/)** carries adoption and methodology narrative; **[Blueprints](https://blueprints.forgesdlc.com/)** holds methodology guides and Wizard background; **[Kitchen Sink](https://ks.forgesdlc.com/)** documents the diagram and layout primitives used here.

```blueprint-diagram
key: linear
alt: Hero path from install through workspace root selection to Classic or Studio
caption: Typical first-session path through documentation
```

## Start here — primary actions

| Goal | Start |
|------|--------|
| **Install and run** | [Install and run](handbook-public/02-install-and-run.md) |
| **First Studio session** | [Studio 101](handbook-public/05-studio-101.md) |
| **First Wizard session** (experimental) | [Wizard 101](handbook-public/09-wizard-101.md) |
| **Enterprise / security posture** | [Security and local-first](handbook-public/17-security-and-local-first.md) → [Enterprise hub](handbook-public/enterprise-index.md) |
| **HTTP API, schemas, examples** | [Builders overview](handbook-public/builders-api-overview.md) → [Schemas and API (builders)](handbook-public/16-schemas-and-api-for-builders.md) |

## Choose your role

Pick a path curated for **how you evaluate or operate** Lenses.

| Role | Start | Typical next steps |
|------|-------|---------------------|
| **Evaluator** | [Lenses overview](handbook-public/01-lenses-overview.md) | [Install and run](handbook-public/02-install-and-run.md), [Security and local-first](handbook-public/17-security-and-local-first.md) |
| **Solo developer** | [Workspace setup](handbook-public/03-workspace-setup.md) | [Studio 101](handbook-public/05-studio-101.md), [Docs Health](handbook-public/15-docs-health.md) |
| **Team lead** | [Tutorials — 201](handbook-public/tutorials-201.md) | [Wizard 201](handbook-public/10-wizard-201.md), [Examples hub](handbook-public/19-examples-hub.md) |
| **Platform operator** | [Enterprise hub](handbook-public/enterprise-index.md) | [Network binding](handbook-public/enterprise-network-binding.md), [Backup and upgrades](handbook-public/enterprise-backup-upgrades.md), [Configuration reference](reference/config-env.md) |
| **Security reviewer** | [Security and local-first](handbook-public/17-security-and-local-first.md) | [OIDC sessions](handbook-public/enterprise-oidc-sessions.md), [Action allowlists](handbook-public/enterprise-actions-allowlists.md), [LLM boundaries](handbook-public/enterprise-llm-boundaries.md) |
| **Builder / integrator** | [Builders overview](handbook-public/builders-api-overview.md) | [Route families](handbook-public/builders-route-families.md), [HTTP API route catalog](generated/api-routes.md), [JSON examples](handbook-public/19-examples-hub.md) |

Detailed journey tables live on **[Pick your path](handbook-public/role-based-paths.md)**—including topics *not* to start from on day one.

## Time horizons

| Horizon | Goal |
|---------|------|
| **First 10 minutes** | Understand products and trust posture → install → choose a workspace root. |
| **First hour** | Complete a **[Studio 101](handbook-public/05-studio-101.md)** or **[Wizard 101](handbook-public/09-wizard-101.md)** exercise; optional **[Docs Health](handbook-public/15-docs-health.md)** scan. |
| **First day** | Establish day-two flows (**[Studio 201](handbook-public/06-studio-201.md)**, **[Wizard 201](handbook-public/10-wizard-201.md)**), optional LLM/offline stance (**[LLM and AI setup](handbook-public/13-llm-and-ai-setup.md)**). |
| **First week** | Enterprise rollout inputs (binding, backups, Fleet if used), **[Tutorials — 301](handbook-public/tutorials-301.md)**, **[Builders](handbook-public/builders-api-overview.md)** integration sketches. |

## Product map — what sits on one server

| Area | Plain language |
|------|----------------|
| **Classic Lenses** | Server-rendered workspace dashboard at **`/`** — projects, Forge plan lenses, rooted in your clones. |
| **Forge Studio** | React UX at **`/studio/`** — newer flows and dashboards on the **same `/api`** surface as Classic. |
| **Blueprints Wizard** | Experimental guided workshop/session flow **inside Studio** (`/studio/blueprints/wizard/`): exports and facilitation; **no automatic Blueprints submodule commits**. |
| **Docs Health** | Analysis/reporting surfaces for handbook and doc quality (**[Docs Health](handbook-public/15-docs-health.md)**). |
| **Fleet / LLM settings** | **Optional**: remote Fleet hooks and model usage when you deliberately enable them in settings or environment. |

```blueprint-diagram
key: tree
alt: One server hosting Classic dashboard, Forge Studio, shared API, Docs Health signals
caption: Forge Lenses — one server, Classic and Studio/Wizard surfaces
```

## Enterprise trust posture (summary)

| Property | Meaning |
|---------|---------|
| **Local-first** | Repos and Wizard session data stay **on volumes you manage** unless you integrate outbound services. |
| **Loopback by default** | Bind to **`127.0.0.1`** until you knowingly expose the server for LAN/testing. |
| **Optional outbound** | Fleet and LLMs are **opt-in configurations** — read enterprise pages before enabling. |
| **Explicit write scope** | High-impact actions honor **operator allowlists** and settings; failures should be surfaced in UI/API. |

For the full reviewer-oriented narrative, **[Security and local-first](handbook-public/17-security-and-local-first.md)** and the **[Enterprise hub](handbook-public/enterprise-index.md)**.

## Ecosystem map — where each site helps

| Site | Responsibility |
|------|----------------|
| **[forgesdlc.com](https://forgesdlc.com/)** | Forge SDLC methodology, adoption narratives, encyclopedia pointers. |
| **[blueprints.forgesdlc.com](https://blueprints.forgesdlc.com/)** | Blueprints practice library; methodology depth that **supports** Wizard and planning work. |
| **[lenses.forgesdlc.com](https://lenses.forgesdlc.com/)** (**this handbook**) | **Product usage**, installation, tutorials, ops, schemas, APIs. |
| **[ks.forgesdlc.com](https://ks.forgesdlc.com/)** | Kitchen Sink design system — components, diagrams, generator patterns mirrored in handbook builds. |

See **[Cross-site map](handbook-public/cross-site-map.md)** for deeper linking.

## Next steps and support

| Need | Doc |
|------|-----|
| **Troubleshooting** | [Troubleshooting](handbook-public/12-troubleshooting.md) |
| **Release notes / versions** | [Release notes](handbook-public/24-release-notes.md), [Docs versioning](handbook-public/25-docs-versioning.md) |
| **Terms** | [Glossary](handbook-public/21-glossary.md), [Support](handbook-public/20-support.md) |

## Maintainer & contributor handbook

Publishing workflow, deeper ADRs, and raw route inventories remain in **`docs/maintainer/`** in the **[forge-lenses repo on GitHub](https://github.com/autowww/forge-lenses/tree/main/docs/maintainer)**. They intentionally **omit** from the lean public handbook build—you will not navigate there from primary reader journeys on this site.

## Local handbook build

With **[Kitchen Sink](https://github.com/autowww/forgesdlc-kitchensink)** at `kitchensink/`:

```bash
python3 generator/build-lenses-docs.py
# Mirror production page set:
# LENSES_DOCS_BUILD_PROFILE=public python3 generator/build-lenses-docs.py
```

Output: **`lenses-docs/`**. The Firebase-hosted shell consumes the same subtree via **`forge-lenses-website`**.
