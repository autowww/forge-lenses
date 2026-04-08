---
nav_title: Lenses scan, environment variable, and host cache layout
public_publish: true
audience: public
product_area: lenses
tier: overview
handbook_area: lenses
learning_level: '201'
---

# Workspace setup — Scan, env var, and host caches

## What it is

Operational steps: set **`LENSES_WORKSPACE_ROOT`**, optionally use a **workspace registry** file, and (when Lenses lives **inside** a host repo) run the **startup script** so local caches sit at the **host** root. Use this after [Choosing the root](03-workspace-setup_02-root-choice.md) when the UI still misbehaves or your team uses a **submodule** layout.

**Parent:** [Workspace setup](03-workspace-setup.md).

## When to use it

- You have chosen a layout and root, but scans stay empty, permissions fail, or caches land in the wrong place.

## Prerequisites

- [Install and run](02-install-and-run.md) completed.
- Shell access to the machine that runs the server.

## Steps

1. **Set the environment variable** — Set **`LENSES_WORKSPACE_ROOT`** to the parent folder that contains your clones (the directory that lists `forge-lenses/` next to other repos in a **sibling** layout, or the **host** root in a nested layout). **Restart** the server after every change.

2. **Optional registry** — Some teams add **`workspace-registry.json`** at the forge-lenses repo root to label repos or tune scanning. Start **without** it unless your runbook already requires it.

3. **Host-repo layout** — When forge-lenses is a **submodule** of a product repo, run **`./scripts/lenses-startup.sh`** once from your team’s documented flow so **`.lenses-local/`** and **`.lenses-repo/<login>/`** are created at the **host** root (not inside `forge-lenses/`). That keeps local caches and shared notes where contributors expect them.

## Worked example — env var forgotten

**Symptom:** Server starts, but **Projects** is empty or shows only the Lenses repo.

**Likely mistake:** `LENSES_WORKSPACE_ROOT` unset or still pointing at an old path.

**Fix:** Export or configure the variable to your **agreed** parent (see [Choosing the root](03-workspace-setup_02-root-choice.md)), restart, reload the browser.

## Worked example — caches under the wrong directory

**Symptom:** Teammates see different local data paths; backups omit `.lenses-local/`.

**Likely mistake:** Skipped **host-root** startup when using a submodule layout; caches were created under `forge-lenses/` instead of the host.

**Fix:** Run **`lenses-startup.sh`** from the documented **host** root once per clone (per team runbook), then confirm `.lenses-local/` exists at the host.

## Symptom → likely mistake → fix

| Symptom | Likely mistake | Fix |
|---------|----------------|-----|
| Permission denied in logs | Server user cannot **read** some repos under the root | Fix filesystem permissions or move clones to a readable path |
| Scan never finishes | Root too **broad** (e.g. home directory) | **Narrow** `LENSES_WORKSPACE_ROOT` |
| “Wrong” repo set after pull | Registry or config overrides | Review optional **`workspace-registry.json`** with your maintainer |
| Need desktop-app or JSON details | — | Maintainer docs for **forge-lenses** on GitHub |

### Scan order (visual)

```blueprint-diagram
key: linear
alt: Set LENSES_WORKSPACE_ROOT → restart → confirm Projects; optional registry; host startup for submodule layout
```

## Expected outcome (plain language)

- The server process and your runbook **agree** on one workspace root path.
- Local state directories exist where **your team** expects them for a **host** layout.
- [Troubleshooting](12-troubleshooting.md) steps for “wrong repos” are about **data**, not “mystery empty UI.”

## How to verify success

- After restart, **Projects** reflects the root you set; permission errors in the terminal are **gone** or explained.

## What to do next

- [Workspace setup](03-workspace-setup.md)
- [Studio overview](04-studio-overview.md)
- [Troubleshooting](12-troubleshooting.md) if scans look empty or permission errors appear
