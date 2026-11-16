---

nav_title: When projects or scans look wrong
public_publish: true
audience: public
product_area: lenses
tier: overview
handbook_area: lenses
learning_level: '201'
section: get-started
status: shipped
description: When projects or scans look wrong — Forge Lenses handbook entry (start).
page_type: how-to
---

# Workspace setup — When projects or scans look wrong

## What it is

The usual fix when **Projects** looks empty, scans seem wrong, or repos do not match what you expect: set **`LENSES_WORKSPACE_ROOT`** to the **parent folder your team agreed on**, **restart** the Lenses server, and reload the browser to confirm **Projects**. Use this page after you have already picked a layout and root in [Choosing the root](03-workspace-setup_02-root-choice.md) but the UI still misbehaves.

**Parent:** [Workspace setup](03-workspace-setup.md).

## When to use it

- You have chosen a layout and root, but scans stay empty, permissions fail, or caches land in the wrong place.

## Prerequisites

- [Install and run](02-install-and-run.md) completed.
- Shell access to the machine that runs the server.

## Steps (what most people need)

1. **Set the workspace root** — Set **`LENSES_WORKSPACE_ROOT`** to the parent folder that contains your clones (the directory that lists `forge-lenses/` next to other repos in a **sibling** layout, or the **host** root in a nested layout). **Restart** the server after every change.

2. **Verify** — Reload the app and confirm **Projects** lists the repos you expect under that parent.

3. **Still wrong?** — Re-read [Choosing the root](03-workspace-setup_02-root-choice.md) and make sure the path matches your **intended** workspace (not a single clone unless that is deliberate). Then repeat step 1.

## Advanced note — submodule / host layout (optional)

**Most teams can skip this.** It matters when **forge-lenses** lives **inside** another repo (for example as a submodule) and you want local caches and shared notes at the **host** repository root instead of under `forge-lenses/`.

- **Optional registry** — Some teams add **`workspace-registry.json`** at the forge-lenses repo root to label repos or tune scanning. Prefer starting **without** it unless your team’s internal doc or maintainer already requires it.

- **Host startup script** — When using that nested layout, your team may run **`./scripts/lenses-startup.sh`** once from the **host** root so **`.lenses-local/`** and **`.lenses-repo/<login>/`** are created next to your product tree (not inside `forge-lenses/`). Follow whatever your team documents for that layout.

For **desktop-app**, JSON APIs, or contributor-level detail, use the **forge-lenses** repository on GitHub — not this handbook.

## Worked example — env var forgotten

**Symptom:** Server starts, but **Projects** is empty or shows only the Lenses repo.

**Likely mistake:** `LENSES_WORKSPACE_ROOT` unset or still pointing at an old path.

**Fix:** Follow **Steps** above: set the variable to your **agreed** parent (see [Choosing the root](03-workspace-setup_02-root-choice.md)), restart, reload the browser.

## Worked example — caches under the wrong directory

**Symptom:** Teammates see different local data paths; backups omit `.lenses-local/`.

**Likely mistake:** Using a **nested / submodule** layout without the host-root setup your team expects; caches were created under `forge-lenses/` instead of the host.

**Fix:** If your team nests Lenses in a product repo, see **Advanced note — submodule / host layout** above (startup script and cache locations). Otherwise, confirm **`LENSES_WORKSPACE_ROOT`** and the host layout with whoever maintains your workspace doc.

## Symptom → likely mistake → fix

| Symptom | Likely mistake | Fix |
|---------|----------------|-----|
| Permission denied in logs | Server user cannot **read** some repos under the root | Fix filesystem permissions or move clones to a readable path |
| Scan never finishes | Root too **broad** (e.g. home directory) | **Narrow** `LENSES_WORKSPACE_ROOT` |
| Still wrong after env var + restart | Optional registry or maintainer-only overrides | Ask your **maintainer** or see **forge-lenses** on GitHub — avoid editing **`workspace-registry.json`** unless your team owns that workflow |
| Need desktop-app or JSON details | — | Maintainer docs for **forge-lenses** on GitHub |

### Scan order (visual)

```blueprint-diagram
key: linear
alt: Set LENSES_WORKSPACE_ROOT → restart → confirm Projects; if nested host layout, see advanced note for startup and caches
title: Symptom to fix flow
summary: Move from a wrong Projects or scan outcome to a bounded fix using this page's worked examples and table.
node: Symptom
detail: Name what Projects or scans show that does not match expectation.
more: Empty UI, permission errors, slow scans, or caches under the wrong directory are common starting points described in the worked examples above.
node: likely mistake
detail: Match the symptom to the usual root cause from the table above.
more: Wrong LENSES_WORKSPACE_ROOT, unreadable paths, an overly broad root, or nested host layout without startup setup are frequent mistakes on this page.
node: fix
detail: Apply the documented fix, then restart the server and reload to verify.
more: Set the agreed workspace root, fix permissions or narrow the root, run the host startup script when nested, or ask your maintainer before editing workspace-registry.json.
fallback_ascii: |
  Symptom
      |
      v
  likely mistake
      |
      v
  fix
```

## Expected outcome (plain language)

- The server process and **your team’s agreed workspace path** line up after a restart.
- If you use a **host** layout, local state directories end up where **your team** expects (see advanced note when relevant).
- [Troubleshooting](12-troubleshooting.md) for “wrong repos” is about **paths and data**, not unexplained empty UI.

## How to verify success

- After restart, **Projects** reflects the root you set; permission errors in the terminal are **gone** or explained.

## What to do next

- [Workspace setup](03-workspace-setup.md)
- [Studio overview](04-studio-overview.md)
- [Troubleshooting](12-troubleshooting.md) if scans look empty or permission errors appear