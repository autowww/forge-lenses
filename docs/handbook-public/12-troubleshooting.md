---

nav_title: Troubleshooting
public_publish: true
audience: public
product_area: lenses
tier: troubleshooting
handbook_area: lenses
learning_level: troubleshooting
section: resources
status: shipped
description: Symptom-oriented fixes for Forge Lenses — Classic and Studio routing, Wizard
  sessions, workspace scans, offline lookup, and when to escalate to server operators or
  deeper maintainer diagnostics.
page_type: troubleshooting
---

# Troubleshooting

## What it is

**Symptoms and simple fixes first** — for **Lenses**, **Forge Studio**, and the **Blueprints Wizard**. Deeper **server checks**, log reading, and **architecture** detail belong in the sections below marked **advanced** or in the **forge-lenses** repository on GitHub — not in the main reading path.

## When to use it

Something failed during [Install and run](02-install-and-run.md), [Workspace setup](03-workspace-setup.md), [Studio 101](05-studio-101.md), or [Wizard 101](09-wizard-101.md).

## Search & offline lookup

Static Firebase hosting does **not** ship a bundled search index yet. Use **browser Find** (`Ctrl+F` / `⌘F`) on long references such as [`api-routes.md`](../generated/api-routes.md), rely on the **horizontal IA + contextual sidebar** for discovery, or jump via [Cross-site map](cross-site-map.md). Full-text search remains on the backlog pending a Pagefind-style spike.

## Prerequisites

- Note the **symptom** (blank page, missing wizard, save errors, etc.).

## Fast triage

| Order | Check |
|-------|-------|
| 1 | Server process running; terminal shows the listen port |
| 2 | URL matches host/port; no stale bookmark |
| 3 | If your team sets a **workspace root** for Lenses, it points at the **parent of your clones** (see [Workspace setup](03-workspace-setup.md)) |

## Common fixes

| Symptom | Area | What to try |
|---------|------|-------------|
| **`/studio/` blank** | Studio | Confirm the Python server is running and the URL/port match [Install and run](02-install-and-run.md). If the dashboard works but Studio does not, reinstall or update from a fresh clone and repeat [Install and run](02-install-and-run.md). If it still fails, ask whoever runs or maintains your Lenses server. |
| **Wizard missing** | Wizard | Confirm you are in Forge Studio under the Wizard entry points described in [Wizard overview](08-wizard-overview.md). If the feature is disabled in your deployment, ask whoever runs the server to enable it or use a build where it is available. |
| **“Local draft only”** | Wizard | Ensure Lenses is running; click **Retry**. If it keeps failing, ask whoever runs the server — you do not need to read logs yourself. |
| **Wrong repos scanned** | Workspace | Set **`LENSES_WORKSPACE_ROOT`** to the parent of your clones; restart the server ([When projects or scans look wrong](03-workspace-setup_03-scan-host.md)). |
| **Save or sync errors** | General | Check **disk space**; **retry** the save; avoid **multiple browser tabs** on one session for critical saves. If errors continue, ask whoever runs or maintains the server. |

## Advanced — if you run or debug the server

Use this when **Fast triage** and **Common fixes** are not enough **and** you run Lenses yourself or sit with someone who does.

| Check | Why it helps |
|-------|--------------|
| Last lines of output in the terminal where the server runs | Often shows import, port, or scan errors in plain language |
| Whether the workspace health endpoint returns data in your browser (when your team’s doc names it) | Separates “UI only” from “server unhealthy” |
| Whether Classic `/` works but `/studio/` does not | Narrows to Studio asset or routing issues |
| **LLM / Refine** failures | Loopback policy for local APIs; **stderr** from the server process |
| **Save / PUT** still failing | Permissions on **`.lenses-local/`** and related paths on the machine that hosts Lenses |

## Maintainer / architecture

| Need | Where |
|------|--------|
| HTTP API shape, internal architecture, JSON contracts | **forge-lenses** repository on GitHub — not this public handbook |

## How to verify success

- The blocking issue is gone or you have a clear next step (restart, workspace path, or follow-up with your server operator).

## What to do next

- [Lenses overview](01-lenses-overview.md)
- [Install and run](02-install-and-run.md)