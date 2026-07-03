---


nav_title: Studio route atlas
public_publish: true
audience: public
product_area: studio
tier: practitioner
handbook_area: studio
learning_level: '201'
section: studio-wizard
description: Forge Studio URL map from lenses-enterprise App.tsx to API families and troubleshooting.
status: shipped
page_type: concept
---

# Studio route atlas

Use this page as the **canonical token table**. Deeper UX context lives in the focused guides below (shell, workspace, Docs Health UI, settings, Studio troubleshooting).

## Focused guides

- [Studio — navigation and shell](studio-navigation-and-shell.md)
- [Studio — workspace and projects](studio-workspace-and-projects.md)
- [Studio — Docs Health UI](studio-docs-health-ui.md)
- [Studio — LLM and Fleet settings](studio-settings-llm-fleet.md)
- [Studio — troubleshooting](studio-troubleshooting.md)

## What it is

**Forge Studio** (`lenses-enterprise` React SPA) mounts at **`/studio/`** from `python3 -m lenses`. Client routes come from [`lenses-enterprise/src/App.tsx`](https://github.com/autowww/forge-lenses/blob/main/lenses-enterprise/src/App.tsx) (`BrowserRouter` + nested `<Route>` declarations). Each area fans out to JSON endpoints catalogued in **`http-api-and-routes.html`** (maintainer build) and summarized for builders in [Schemas and API (builders)](16-schemas-and-api-for-builders.md).

## When to read it

- You need **URL → API** alignment for screenshots, support, or QA.
- You extended Studio and must document new **`GET`** vs **`POST`** behavior.

## Daily flow (swimlane)

```blueprint-diagram
key: swimlane
alt: Operator and Studio client responsibilities for a typical review session
caption: Browser routes call /api helpers; persistence lands under .lenses-local
```

## Route families vs network hops

```blueprint-diagram
key: network
alt: Studio browser routes connect to local Lenses HTTP API then workspace state
caption: All Studio surfaces share the same Lenses origin; no separate Studio API host
```

## Client route checklist (from `App.tsx`)

Paths below are **relative to `/ studio /`** (spaces added to avoid accidental linkification in plain Markdown editors). Token text matches `studio-route-doc-coverage.yaml` for CI.

| Area | Path tokens (representative) | Typical APIs | Notes |
|------|------------------------------|--------------|--------|
| Home | `overview/charts`, `projects`, `projects/:name`, `projects/:name/charts`, `projects/:name/strategy`, `projects/:name/branching`, `projects/:name/forge-run`, `projects/:name/docs-health`, `projects/:name/docs-health/master`, `projects/:name/docs-health/session/:sessionId` | workspace state, chart bundles, git proxies | Project scoping is the busiest subtree. |
| Discovery | `search`, `chat` | search indices, assistant | `chat` may be gated by LLM config. |
| Settings | `settings/llm`, `settings/fleet`, `settings/ux-insights`, `settings/agent-runtime` | LLM gateway, Fleet jobs, experiments | `fleet` also appears in settings paths. |
| Governance | `governance/connectors`, `governance/audit` | governance APIs | Distinct from methodology knowledge panes. |
| Productivity | `toolset`, `toolset/:name` | tool runner | `:name` selects packaged automation. |
| Sites | `websites`, `websites/browse/:site` | blog + workspace markdown indexes | Includes Forge SDLC blog surfaces. |
| Structure | `wbs`, `wbs/view` | WBS readers | |
| Planning | `plan`, `plan/matrix`, `timeline`, `board`, `board/:id` | plan spine, matrix, boards | `plan/matrix` is the matrix lens. |
| Learning | `tutorials` | guided content | |
| Embedded | `view/docs/*`, `view/local-site/*`, `workspace-md`, `workspace-md/view` | static file proxies | `local-site` serves selected static previews. |
| Content | `blog`, `blog/post/:slug` | blog feeds | `post` segment is static in the router. |
| Knowledge | `knowledge/methodology/evidence`, `knowledge/methodology/decisions`, `knowledge/methodology/record/:entityId`, `knowledge/methodology/readiness`, `knowledge/agentic-bridge` | methodology registries | Includes **evidence**, **decisions**, **record**, **readiness**, and **agentic-bridge**. |
| Foundry | `foundry`, `foundry/runs/:runId` | Dark Factory bounded runs | Bounded L1 draft runs with human promote; `runs/:runId` is a probe/deep-link surface. |
| Autonomy | `autonomy-maturity`, `projects/:name/autonomy-maturity` | `/api/autonomy-maturity/*`, `/api/project/:name/autonomy-maturity` | Experimental (flag-gated, default off): observed autonomy level+grade and 0-100 maturity score per project. See [Autonomy maturity](studio-autonomy-maturity.md). |
| Labs | `roadmap-section`, `feature-showcase` | experimental panes | treat as optional / flag-gated. |
| Wizard | `blueprints/wizard`, `blueprints/wizard/session/:sessionId` | `/api/blueprints/wizard/*` | Session deep links for debugging. |

## Decision: blank Studio shell

```blueprint-diagram
key: decision
alt: Troubleshooting decision tree for blank Studio or 404 assets
caption: Check API origin before assuming a Studio bug
```

## Troubleshooting

See **[Studio — troubleshooting](studio-troubleshooting.md)** for blank shell, assets, and API-origin checks (includes the same steps formerly duplicated here).

1. Watch **Network** while visiting each family above; compare methods to **`http-api-and-routes.html`**.
2. Keep this table aligned with [`docs/strategy/studio-route-doc-coverage.yaml`](../strategy/studio-route-doc-coverage.yaml) — CI asserts tokens stay documented.
