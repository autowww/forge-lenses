---
nav_title: Studio 301
public_publish: true
audience: public
product_area: studio
tier: '301'
handbook_area: studio
learning_level: '301'
---

# Studio 301 — Advanced

## What it is

Optional **power-user** help for **Forge Studio**: getting more from **embedded views**, staying aligned with **Classic** (the dashboard at `/`), and knowing **when Studio and Classic differ** so you can pick the right surface without blocking your work.

## When to use it

After [Studio 201](06-studio-201.md), when you are tuning how you work across Studio and Classic or hitting edge cases.

## Prerequisites

- Comfortable with [Studio 201](06-studio-201.md).

## Decision framework (when to reach for 301)

Use **Studio 301** when you already know [Studio 201](06-studio-201.md) basics and you need to **choose** between Classic and Studio deliberately, or when you are **debugging** a mismatch (empty chart, slow scan) without reinstalling. Stay on **Studio 201** if you are still learning navigation and first-session checks.

| Situation | Prefer |
|-----------|--------|
| New team member first week | [Studio 201](06-studio-201.md) only |
| Same data in Classic but not in Studio | This page + [Troubleshooting](12-troubleshooting.md) |
| Experimental Studio-only flow | This page; fall back to Classic if the flow blocks work |

### Advanced vs Classic (visual)

```blueprint-diagram
key: decision
alt: Prefer Studio 201 for learning; use Studio 301 when choosing Classic vs Studio or debugging mismatches
```

## Advanced scenarios

| Scenario | Suggested approach |
|----------|-------------------|
| Chart empty in Studio | Verify the **same project** in Classic first; refresh Studio |
| Conflicting status | Pick **one** surface for status meetings; reconcile before switching |
| Large workspace slow after restart | Wait for scan idle before deep navigation |

## Limitations and fallbacks

Not every **Classic** report or route exists in **Studio** yet, and some Studio flows are still **experimental**. When something you need is missing or flaky, prefer **Classic** at `/` for that task rather than forcing an unsupported path.

| Limitation | Fallback |
|------------|----------|
| Classic route not in Studio yet | Use **Classic** at `/` for that report |
| Experimental Studio feature unstable | Do the same task in **Classic** until the feature is stable in **your** deployment |
| Wizard or export step unavailable in Studio | Complete the step in **Classic** or retry after refresh ([Wizard 301](11-wizard-301.md) for advanced Wizard flows) |

### Advanced note — local or custom builds

If you run Lenses from **source**, a **preview** build, or an internal fork, Studio can briefly **lag** Classic on a given feature. That is an **operator/build** concern, not something most readers need to manage. **Fallback:** use **Classic** for the blocked step; if the gap persists, use [Troubleshooting](12-troubleshooting.md) and whoever maintains your server.

## Steps

1. **Charts and data views** — Studio may show chart or summary views that mirror what Classic exposes. If a view looks empty, open the **same project** in Classic and confirm data appears there first, then return to Studio and refresh.

2. **Compare Classic vs Studio** — Use Classic when you need a route or report that Studio has not replicated yet; use Studio for newer flows. Keep one **source of truth** for status (same workspace root, same project selection).

3. **Gaps and experimental features** — When a route or control is missing in Studio, or labeled experimental, complete the work in **Classic** or wait for a refresh after your team updates Lenses — see **Limitations and fallbacks** above.

4. **Advanced note — performance and stability** — Large workspaces: give scans time after restart; avoid flipping workspace roots while Studio tabs are mid-request. If the UI stalls, reload the page after the server is idle.

## How to verify success

- You can complete your advanced workflow without blocking day-to-day use, or you know to fall back to Classic for a specific gap.

## What to do next

- [Troubleshooting](12-troubleshooting.md)
- [Wizard 301](11-wizard-301.md)
