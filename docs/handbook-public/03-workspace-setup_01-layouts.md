---
nav_title: Common workspace layouts for Lenses (siblings vs host repo)
public_publish: true
audience: public
product_area: lenses
tier: overview
handbook_area: lenses
learning_level: '201'
---

# Common workspace layouts for Lenses (sibling repos vs host repo)

## What it is

Typical **folder arrangements** for Lenses scans: **sibling repos** on disk versus **forge-lenses nested** inside a host product repository. This page is **scenario-first**: pick the layout that matches how your team clones code, then use [Choosing the root](03-workspace-setup_02-root-choice.md) to point `LENSES_WORKSPACE_ROOT` at the right folder.

**Parent:** [Workspace setup](03-workspace-setup.md).

## When to use it

Before you set `LENSES_WORKSPACE_ROOT` or when teammates disagree whether Lenses should live “next to” or “inside” product repos.

## Prerequisites

- You know where your **git clones** live on disk (paths, not URLs).

## Layouts (summary)

| Layout | Typical `LENSES_WORKSPACE_ROOT` | When it works well |
|--------|----------------------------------|--------------------|
| **Sibling repos** | Parent folder listing `forge-lenses/`, `product-a/`, `product-b/` | Most teams; clearest multi-repo scans |
| **Single product + submodule** | **Host** repository root after startup script | One primary product repo with Lenses as a nested checkout |

### Layout choice (visual)

```blueprint-diagram
key: board
alt: Sibling layout vs host-repo layout — pick one before choosing the root
```

## Worked example — sibling repos (most common)

**Starting situation:** You cloned `forge-lenses` and two services into one parent folder for local development.

**Before (folder tree):**

```text
~/work/acme/
  forge-lenses/
  billing-api/
  auth-lib/
```

**You set** `LENSES_WORKSPACE_ROOT` to **`~/work/acme`** (the parent — not inside `billing-api`).

**Expected outcome:** **Projects** lists `billing-api` and `auth-lib` as separate cards; **Overview** can relate work across them. Lenses itself appears as a folder under the root but is usually not your “product” card unless you treat it as such.

## Worked example — host repo with nested Lenses

**Starting situation:** Your company keeps `forge-lenses` as a **submodule** (or nested clone) under a **host** monorepo root so every developer gets the same layout.

**Before (conceptual tree):**

```text
~/work/acme-platform/          ← host root (often the git root)
  forge-lenses/                ← nested Lenses checkout
  services/
  libs/
```

**You set** `LENSES_WORKSPACE_ROOT` to the **host root** (`~/work/acme-platform`), not to `forge-lenses/` inside it, when you want cards for `services/*` and `libs/*`. If you only set root to `forge-lenses/`, you will mostly see that subtree — fine for Lenses-only work, wrong for full-program visibility.

**Expected outcome:** Project discovery follows the **host** tree; local caches from [Scan and host setup](03-workspace-setup_03-scan-host.md) stay where your runbook expects.

## Symptom → likely mistake → fix

| Symptom | Likely mistake | Fix |
|---------|----------------|-----|
| Only one repo appears though you have several | Root is **inside** one clone (e.g. `.../billing-api` only) | Move `LENSES_WORKSPACE_ROOT` **up** to the parent that lists all repos |
| Wrong repos mixed in | Root is too **high** (e.g. your entire home directory) | Narrow root to the folder that should be your **program** workspace |
| Paths differ per teammate | Everyone uses a different parent | Document one **canonical** parent path in your internal wiki |

## How to verify success

- The folder you document as the workspace root **matches** what `LENSES_WORKSPACE_ROOT` points at after a server restart.
- **Projects** shows the set of product repos you intended for this workspace, not a random slice of your disk.

## What to do next

- [Workspace setup](03-workspace-setup.md)
- [Choosing the root](03-workspace-setup_02-root-choice.md)
