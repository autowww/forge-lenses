---
nav_title: "Workspace: Common layouts"
public_publish: true
audience: public
product_area: lenses
tier: overview
handbook_area: lenses
learning_level: '201'
---

# Workspace setup — Common layouts

## What it is

Typical **folder arrangements** for Lenses scans: sibling repos vs host-repo layout.

**Parent:** [Workspace setup](03-workspace-setup.md).

## Layouts

| Layout | Typical `LENSES_WORKSPACE_ROOT` | When it works well |
|--------|----------------------------------|--------------------|
| **Sibling repos** | Parent folder listing `forge-lenses/`, `product-a/`, `product-b/` | Most teams; clearest scans |
| **Single product + submodule** | Host repository root after `lenses-startup` | One primary product repo with Lenses nested |

## What to do next

- [Workspace setup](03-workspace-setup.md)
- [Choosing the root](03-workspace-setup_02-root-choice.md)
