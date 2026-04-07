---
nav_title: Workspace setup
public_publish: true
audience: public
product_area: lenses
tier: overview
handbook_area: lenses
learning_level: '201'
---

# Workspace setup

## What it is

Choosing **which folders** Lenses scans: usually a **parent directory** that contains your product repos and the **forge-lenses** checkout as siblings.

## When to use it

Before you rely on multi-repo overview, project cards, or cross-repo links — or when the dashboard shows the wrong tree.

## Prerequisites

- Server runs ([Install and run](02-install-and-run.md)).
- You know the absolute path to the folder that should be the workspace root.

## Common layouts

| Layout | Typical `LENSES_WORKSPACE_ROOT` | When it works well |
|--------|----------------------------------|--------------------|
| **Sibling repos** | Parent folder listing `forge-lenses/`, `product-a/`, `product-b/` | Most teams; clearest scans |
| **Single product + submodule** | Host repository root after `lenses-startup` | One primary product repo with Lenses nested |

## Choosing the root (good vs bad)

| Good | Bad |
|------|-----|
| Parent of **all** repos you want cards for | A single repo folder when you need multi-repo visibility |
| Stable path your team can document | A transient mount that changes between sessions |

If **Projects** or **Overview** look empty, the root is almost always too shallow or too deep — move up or down one directory and restart the server.

## Steps

1. **Prefer an environment variable** — Set **`LENSES_WORKSPACE_ROOT`** to the parent folder that contains your clones (the directory that lists `forge-lenses/` next to other repos). Restart the server after changing it.

2. **Optional registry** — Some teams use a small **`workspace-registry.json`** at the forge-lenses repo root to label repos and tune scanning. You only need this if your team already standardized on it; otherwise start without it.

3. **Host-repo layout** — When forge-lenses is a **submodule** of a product repo, run **`./scripts/lenses-startup.sh`** once from the documented flow so **`.lenses-local/`** and **`.lenses-repo/<login>/`** are created at the **host** root (not inside `forge-lenses/`). That keeps local caches and shared notes where your team expects them.

Desktop app and JSON config details for workspace resolution are documented for operators in the **forge-lenses** repository on GitHub (maintainer documentation).

## How to verify success

- **Projects** and **Overview** reflect repos you expect under the chosen root.

## What to do next

- [Studio overview](04-studio-overview.md)
- [Troubleshooting](12-troubleshooting.md) if scans look empty or permission errors appear