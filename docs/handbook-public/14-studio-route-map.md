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
- [Studio — Doc Management](studio-doc-management.md)
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
title: Studio review swimlane
summary: How operator handoff and client inspection align during a typical Studio review session.
node: Daily flow (swimlane)
detail: Frames operator and Studio client responsibilities for one review pass.
more: Maps browser routes to /api helpers with persistence under .lenses-local, as described in this atlas.
node: Lane A
detail: Operator track for initiating and closing the session.
more: Covers the human-owned side of a review: context handoff and confirming the shared outcome.
node: handoff
detail: Operator transfers review context into Studio.
more: Session state reaches the workspace through Lenses HTTP API helpers the client calls.
node: shared outcome
detail: Both lanes converge on a reviewable, agreed result.
more: API responses and .lenses-local persistence should reflect the outcome the operator expects.
node: Lane B
detail: Studio client track for inspection and adaptation.
more: The lenses-enterprise SPA at /studio/ drives this lane via nested client routes from App.tsx.
node: inspect / adapt
detail: Client surfaces routes, APIs, and workspace state for review.
more: Use the route family table and Network tab to align screenshots and QA with documented tokens.
node: feedback
detail: Findings loop back to refine the handoff or escalate.
more: Misaligned API origin or missing assets often surface here before assuming a Studio rendering bug.
caption: Browser routes call /api helpers; persistence lands under .lenses-local
fallback_ascii: |
  Daily flow (swimlane)

  Lane A ──► handoff ──► shared outcome
  Lane B ──► inspect / adapt ──► feedback
```

## Route families vs network hops

```blueprint-diagram
key: network
alt: Studio browser routes connect to local Lenses HTTP API then workspace state
title: Studio route network hops
summary: How Studio client routes fan out from one Lenses origin to API families and workspace state.
node: Route families vs network hops
detail: Overview of browser-to-API alignment across Studio surfaces.
more: Every Studio area shares the same Lenses host; there is no separate Studio API server.
node: Root / intake
detail: Studio mounts at /studio/ on the Lenses HTTP server.
more: Client routes come from lenses-enterprise App.tsx via BrowserRouter and nested Route declarations.
node: branch A
detail: One route family with its typical JSON endpoints.
more: Align paths and methods with http-api-and-routes.html and the client route checklist below.
node: branch B
detail: Sibling family sharing the same origin and persistence model.
more: Home, discovery, settings, and governance areas each map to distinct API groups on one host.
node: branch C
detail: Another family following the same local network hop pattern.
more: Planning, content, Foundry, and Wizard sessions use the same Lenses origin and workspace state.
caption: All Studio surfaces share the same Lenses origin; no separate Studio API host
fallback_ascii: |
  Route families vs network hops

  Root / intake
      +-- branch A
      +-- branch B
      +-- branch C
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
| Content | `blog`, `blog/post/:slug`, `doc-management`, `doc-management/session/:sessionId` | `/api/forgesdlc-blog/*`, `/api/doc-management/*` | Doc Management: Hydration v2 sessions (intake → run → approve → promote). See [Studio — Doc Management](studio-doc-management.md). |
| Knowledge | `knowledge/methodology/evidence`, `knowledge/methodology/decisions`, `knowledge/methodology/record/:entityId`, `knowledge/methodology/readiness`, `knowledge/agentic-bridge` | methodology registries | Includes **evidence**, **decisions**, **record**, **readiness**, and **agentic-bridge**. |
| Foundry | `foundry`, `foundry/runs/:runId` | Dark Factory bounded runs | Bounded L1 draft runs with human promote; `runs/:runId` is a probe/deep-link surface. |
| Autonomy | `autonomy-maturity`, `projects/:name/autonomy-maturity` | `/api/autonomy-maturity/*`, `/api/project/:name/autonomy-maturity` | Experimental (flag-gated, default off): observed autonomy level+grade and 0-100 maturity score per project. See [Autonomy maturity](studio-autonomy-maturity.md). |
| Labs | `roadmap-section`, `feature-showcase` | experimental panes | treat as optional / flag-gated. |
| Wizard | `blueprints/wizard`, `blueprints/wizard/session/:sessionId` | `/api/blueprints/wizard/*` | Session deep links for debugging. |

## Decision: blank Studio shell

```blueprint-diagram
key: decision
alt: Troubleshooting decision tree for blank Studio or 404 assets
title: Blank Studio shell decision
summary: Gate whether a blank shell is an API-origin problem or needs deeper troubleshooting.
node: Decision: blank Studio shell
detail: Entry when Studio renders empty or static assets return 404.
more: Full blank-shell, assets, and API-origin steps live in Studio troubleshooting linked from this page.
node: Current state
detail: Confirm what the browser shows and which /studio/ URL loaded.
more: Note whether the shell is blank, partially rendered, or missing assets under the Studio mount.
node: Checkpoint / gate
detail: Verify API origin and asset paths before blaming Studio UI.
more: Studio and its JSON endpoints must share the same Lenses origin; a mismatch often yields a blank shell.
node: refine or escalate
detail: Fix origin, assets, or configuration when the gate fails.
more: Compare Network requests to http-api-and-routes.html and the troubleshooting guide.
node: Continue flow
detail: Proceed with route-family checks when origin and assets look correct.
more: Use the client route checklist and studio-route-doc-coverage.yaml tokens to isolate the failing area.
caption: Check API origin before assuming a Studio bug
fallback_ascii: |
  Decision: blank Studio shell

  Current state
      |
      v
  Checkpoint / gate
      |
      +-- no ──► refine or escalate
      |
     yes
      v
  Continue flow
```

## Troubleshooting

See **[Studio — troubleshooting](studio-troubleshooting.md)** for blank shell, assets, and API-origin checks (includes the same steps formerly duplicated here).

1. Watch **Network** while visiting each family above; compare methods to **`http-api-and-routes.html`**.
2. Keep this table aligned with [`docs/strategy/studio-route-doc-coverage.yaml`](../strategy/studio-route-doc-coverage.yaml) — CI asserts tokens stay documented.
