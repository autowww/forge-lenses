---

nav_title: Tutorial ladder — 101 overview
public_publish: true
audience: public
product_area: lenses
learning_level: '101'
section: tutorials-101
description: Map of beginner tutorials — Studio and Wizard first sessions.
status: shipped
tier: tutorial
handbook_area: tutorials-101
page_type: landing
---

# Tutorials — 101 (overview)

## Prerequisites

- Finish **[Install and run](02-install-and-run.md)** so **`python3 -m lenses`** listens on localhost.
- Have a disposable repo or clone you can inspect through Studio/Wizard surfaces.

Beginner paths assume **[Install and run](02-install-and-run.md)** is complete and the server answers on loopback.

| Guide | Time (typ.) | Outcome |
|-------|-------------|---------|
| [Studio 101](05-studio-101.md) | 5–10 min | `/studio/` loads; you complete one navigation path |
| [First Classic dashboard](05-studio-101_01-first-classic-dashboard.md) | 5 min | Classic `/` loads; you review one useful Classic view |
| [First Docs Health scan](05-studio-101_02-first-docs-health-scan.md) | 2–5 min | Summary and work-items (GET-only) make sense for your workspace |
| [Wizard 101](09-wizard-101.md) | 15–25 min | Create or resume a Wizard session; understand hub vs session URLs |

## Verify (101 lane)

- Each linked tutorial above loads without maintainer-only banners for `audience: public` builds.
- You can articulate **one observable artifact** after each row (Studio chrome, Classic dashboard snapshot, Docs Health summary row, Wizard session JSON).

## Studio IA (optional reads)

| Page | Why open it |
|------|-------------|
| [Studio route atlas](14-studio-route-map.md) | **Canonical** `/studio/...` token checklist |
| [Studio — navigation and shell](studio-navigation-and-shell.md) | Header, sidebar, route families |
| [Studio — troubleshooting](studio-troubleshooting.md) | Blank shell / wrong API origin |

## Suggested order

```blueprint-diagram
key: swimlane
alt: Suggested 101 learning lanes for Studio and Wizard
caption: Either lane can start first; both assume install is done
```

## Recover

When installation fails, rerun the Prerequisites checklist, then escalate through **[Studio troubleshooting](studio-troubleshooting.md)** before assuming a Wizard-specific bug.

## Scenario (no secrets)

You cloned **forge-lenses** beside your product repo, started the server, and want **one** win today: either see Studio chrome and a project row, **or** create a throwaway Wizard session to learn the twelve-step UX — without connecting a real LLM if you are offline.

## Next ladder

When 101 feels comfortable, open **[Tutorials — 201](tutorials-201.md)** for daily habits and Wizard 201 flows.
