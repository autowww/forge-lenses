---


nav_title: Wizard operator trust boundaries
public_publish: true
audience: public
product_area: wizard
tier: practitioner
handbook_area: wizard
learning_level: '201'
section: studio-wizard
status: experimental
description: What stays on-disk, what crosses the browser boundary, and what never auto-edits your repo.
page_type: topic
---

# Wizard — operator trust boundaries

## What it is

A concise map of **who** may observe or mutate **Wizard session data** versus **your git working tree**, **LLM vendors**, and **Forge Fleet**. Implementation touch points live under `lenses/blueprints_wizard/` in the **forge-lenses** repository.

## Boundaries (expanded)

| Surface | Ships today | Operator responsibility |
|---------|-------------|-------------------------|
| **Browser (Studio)** | Renders steps; holds **transient** UI state | Hard-refresh can drop unsaved UI — rely on server persistence for the session envelope |
| **Lenses HTTP API** | `GET`/`POST` families under **`/api/blueprints/wizard/*`** ([builder API](wizard-builder-session-api.md)) | Restrict network path to trusted clients on your LAN/VPN |
| **`.lenses-local/`** | Session JSON, telemetry, optional export scratch | Classify as **sensitive** working data — backup/retention per [Security and local-first](17-security-and-local-first.md) |
| **Product repos** | Wizard does **not** auto-commit Blueprints submodule or product branches | Review diffs yourself; exports are **suggestions** |
| **LLM** | Optional **Refine** / **Interpret** / similar **POST** routes | Redact regulated content; route via approved gateways |
| **Forge Fleet** | Optional async jobs when wired | Bearer tokens are **production** secrets |

## Sequence view

Same story as the overview diagram — trust flows across Studio, Lenses, and optional outbound services:

```blueprint-diagram
key: sequence
alt: Trust boundaries for Wizard sessions vs repo and outbound services
caption: Session envelope persists server-side; outbound calls are explicit POSTs
```

## Verify

Your runbook names **where session files live** on disk (`.lenses-local/…`) and states that **no** Wizard route implies an automatic `git push`.

## What to do next

- [Blueprints Wizard overview](08-wizard-overview.md)
- [Wizard builder session API](wizard-builder-session-api.md)
