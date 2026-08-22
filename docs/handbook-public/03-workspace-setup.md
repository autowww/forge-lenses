---

nav_title: Workspace setup
public_publish: true
audience: public
product_area: lenses
tier: overview
handbook_area: lenses
learning_level: '201'
section: get-started
status: shipped
description: Workspace setup — Forge Lenses handbook entry (start).
page_type: how-to
---

# Workspace setup

## What it is

Choosing **which folders** Lenses scans: usually a **parent directory** that contains your product repos and the **forge-lenses** checkout as siblings.

**Read this first:** Lenses treats one directory on disk as the **workspace root**. Everything else — which repos appear, how links resolve, and whether Studio feels “empty” — follows from that choice. If the root is too narrow, you will only see one clone; if it is wrong, scans and project cards will not match what you expect. The child pages below unpack **layouts**, **how to pick the root**, and **what to do when projects or scans still look wrong**.

## When to use it

Before you rely on multi-repo overview, project cards, or cross-repo links — or when the dashboard shows the wrong tree.

## Prerequisites

- Server runs ([Install and run](02-install-and-run.md)).
- You know the absolute path to the folder that should be the workspace root.

## Topics

**Common layouts** describes sibling checkouts versus a host-repo layout — the shape of folders on disk before you set any environment variable. Use it when you are unsure whether `forge-lenses` should sit next to product repos or inside another tree.

**Choosing the root** is where you commit to a single path for `LENSES_WORKSPACE_ROOT` (or equivalent). Read it when the UI shows fewer repos than you have on disk, or when you intentionally want a smaller scope.

**When projects or scans look wrong** walks through the usual **env var + restart** fix first, then optional **advanced** notes for nested/host layouts. Use it when the root looks correct but **Projects** is still empty, permissions fail, or caches are not where your team expects.

Each child page is **scenario-first**: worked examples, folder trees, symptom-to-fix tables, and an **expected outcome** in plain language before you jump to the next topic.

| Topic | Page |
|-------|------|
| **Layouts (siblings vs host)** | [Common workspace layouts](03-workspace-setup_01-layouts.md) |
| **Choosing the workspace root** | [How to choose `LENSES_WORKSPACE_ROOT`](03-workspace-setup_02-root-choice.md) |
| **When projects or scans look wrong** | [When projects or scans look wrong](03-workspace-setup_03-scan-host.md) |

### Topic order (visual)

Read **layouts**, then **root choice**, then **when projects or scans look wrong** if the overview still misbehaves.

```blueprint-diagram
key: decision
alt: Workspace setup — common layouts, then choosing the root, then fixes when projects or scans look wrong
title: Workspace setup reading order
summary: Navigate layouts, root choice, and scan troubleshooting in sequence before relying on Studio overview.
node: Topics
detail: The three child pages that structure workspace setup on disk.
more: Read layouts first, then root choice, then scan-host fixes when Projects or Overview still look wrong.
node: Current state
detail: Your grasp of folder layout and whether a workspace root is already chosen.
node: Checkpoint / gate
detail: Confirms prerequisites before advancing to the next setup topic.
more: Each child page states an expected outcome; verify it matches your disk layout and env var before moving on.
node: refine or escalate
detail: Revisit an earlier topic or open troubleshooting when the gate fails.
more: Empty Projects or wrong repo counts usually mean returning to root choice or the scan-host page, not skipping ahead.
node: Continue flow
detail: Proceed to the next handbook page in the bounded setup sequence.
fallback_ascii: |
  Topics

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

## How to verify success

- **Projects** and **Overview** reflect repos you expect under the chosen root.

## What to do next

- [Studio overview](04-studio-overview.md)
- [Troubleshooting](12-troubleshooting.md) if scans look empty or permission errors appear