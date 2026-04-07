---
nav_title: Troubleshooting
public_publish: true
audience: public
product_area: lenses
tier: troubleshooting
handbook_area: lenses
learning_level: troubleshooting
---

# Troubleshooting

## What it is

Common fixes for **Lenses**, **Forge Studio**, and the **Blueprints Wizard** — user-facing symptoms first; build and server tuning for operators stay in the **forge-lenses** repository.

## When to use it

Something failed during [Install and run](02-install-and-run.md), [Workspace setup](03-workspace-setup.md), [Studio 101](05-studio-101.md), or [Wizard 101](09-wizard-101.md).

## Prerequisites

- Note the **symptom** (blank page, missing wizard, save errors, etc.).

## Steps

| Symptom | What to try |
|---------|-------------|
| **`/studio/` blank** | Confirm the Python server is running and the URL/port match [Install and run](02-install-and-run.md). If the dashboard works but Studio does not, reinstall or update from a fresh clone and repeat [Install and run](02-install-and-run.md). If it still fails, ask whoever runs or maintains your Lenses server. |
| **Wizard missing** | Confirm you are in Forge Studio under the Wizard entry points described in [Wizard overview](08-wizard-overview.md). If the feature is disabled in your deployment, ask whoever runs the server to enable it or use a build where it is available. |
| **“Local draft only”** | Ensure Lenses is running; click **Retry**; check server logs for errors. |
| **Wrong repos scanned** | Set **`LENSES_WORKSPACE_ROOT`** to the parent of your clones; restart the server. |
| **LLM / Refine errors** | Confirm loopback policy for local APIs; check server stderr. |
| **Save / PUT errors** | Disk space; permissions on **`.lenses-local/`**; avoid multiple tabs on one session for critical saves. |
| **Architecture or HTTP details** | Use the **forge-lenses** repository on GitHub — not this public handbook. |

## How to verify success

- The blocking issue is gone or you have a clear next step (restart, workspace path, or follow-up with your server operator).

## What to do next

- [Lenses overview](01-lenses-overview.md)
- [Install and run](02-install-and-run.md)