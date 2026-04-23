---
nav_title: How to choose LENSES_WORKSPACE_ROOT for Studio and Wizard
public_publish: true
audience: public
product_area: lenses
tier: overview
handbook_area: lenses
learning_level: '201'
---

# How to choose LENSES_WORKSPACE_ROOT for Studio and Wizard

## What it is

How to pick a **workspace root** so **Projects** and **Overview** in Lenses (including **Forge Studio** and the **Blueprints Wizard**) show the repos and folders you expect. **`LENSES_WORKSPACE_ROOT`** is the environment variable that tells the server which directory on disk is the **top of the tree** to scan.

**Parent:** [Workspace setup](03-workspace-setup.md).

## When to use it

When the dashboard looks **empty**, shows **too much**, or **misses** a repo you know exists — after you have picked a [layout](03-workspace-setup_01-layouts.md).

## Prerequisites

- [Common layouts](03-workspace-setup_01-layouts.md) read once.
- Ability to set an environment variable and **restart** the Lenses server.

## Good vs bad roots

| Good | Bad |
|------|-----|
| Parent of **all** repos you want cards for | A single repo folder when you need **multi-repo** visibility |
| **Stable** path your team can document | A **transient** mount or temp path that changes between sessions |
| Same path in **docs** and on the **machine that runs** the server | Each developer pointing at a different parent without agreeing |

## Worked example — root too deep

**Starting situation:** You have three siblings under `~/work/acme/` but set `LENSES_WORKSPACE_ROOT` to `~/work/acme/billing-api`.

**Before:**

```text
LENSES_WORKSPACE_ROOT=~/work/acme/billing-api
```

**Symptom:** **Projects** shows only `billing-api` (or one tree); **auth-lib** never appears.

**After:**

```text
LENSES_WORKSPACE_ROOT=~/work/acme
```

Restart the server. **Projects** should list both product folders you care about.

## Worked example — root too shallow (too high)

**Starting situation:** You pointed the root at `~/work` to “see everything.”

**Symptom:** Unrelated folders appear as discoverable trees; scans feel slow or noisy; teammates see repos that are not part of your program.

**Fix:** Narrow `LENSES_WORKSPACE_ROOT` to **one** program folder (e.g. `~/work/acme`) and document that as the standard.

## Symptom → likely mistake → fix

| Symptom | Likely mistake | Fix |
|---------|----------------|-----|
| Empty **Projects** / **Overview** | Root **inside** one repo only | Move root **up** one level to the parent that contains all clones |
| Missing one repo | That repo lives **outside** the chosen parent | Either move the clone under the documented parent or **widen** the root (team decision) |
| Different results after reboot | Root uses a **relative** or **symlink** path that resolves differently | Use a **stable absolute** path in runbooks |
| Classic `/` works but paths feel wrong in Studio | Same underlying root issue | Fix root first; then refresh Studio |

### Root choice flow (visual)

```blueprint-diagram
key: decision
alt: Too empty — move root up; too noisy — move root down; then restart server
```

## Expected outcome (plain language)

After a correct root and restart:

- **Projects** lists the product repositories (or subtrees) your team agreed belong in this workspace.
- **Overview** and cross-repo views **make sense** for that same set — not your whole laptop.

## How to verify success

- You can state the workspace root path **in one sentence** and it matches the running server configuration.
- A second teammate using the same path sees the **same** project set (modulo their own clone state).

## What to do next

- [Workspace setup](03-workspace-setup.md)
- [When projects or scans look wrong](03-workspace-setup_03-scan-host.md) if the root is right but scans still fail
