---

nav_title: Security and local-first operation
public_publish: true
audience: public
product_area: lenses
tier: overview
handbook_area: lenses
learning_level: '101'
section: enterprise
status: shipped
description: Security and local-first operation — Forge Lenses handbook entry (enterprise).
page_type: concept
---

# Security posture and `.lenses-local` writes

## What it is

Lenses deliberately defaults to **`127.0.0.1`** binding (`--bind-all-interfaces` is opt-in **and** logs a scary banner). Sensitive writes land in **`<workspace>/.lenses-local/`** (sessions, FTS DB, Wizard state, telemetry). Shared GitHub overlays store under **`.lenses-repo/<login>/…`** once GitHub PAT auth succeeds.

```blueprint-diagram
key: decision
alt: Widening binds or automation flags forks into OIDC prerequisites versus rollback
caption: Operators treat loopback-first posture as default and branch only with evidence
```

## When to revisit this checklist

Before enabling **`LENSES_ALLOW_ACTIONS`** or **`LENSES_ALLOW_GIT_ACTIONS`**, before widening bind surfaces, and before attaching reverse proxies that expose **`/studio/`** or **`/api/`** beyond trusted networks.

## Key controls

| Control | Meaning |
|---------|---------|
| **Loopback default** | Keeps **`POST`** surfaces (LLM provider saves, Wizard refine, Fleet probes) unreachable from LAN accidentally. |
| **`LENSES_ALLOW_ACTIONS=1`** | Opt-in WAN/LAN privilege — still requires GitHub / OIDC session for destructive flows. |
| **`LENSES_ALLOW_GIT_ACTIONS=1`** | Permits scripted git + tool runner **`POST`** remotely — treat like sharing your shell history. |
| **RBAC file** **`lenses-access.json`** | Per-project scopes + auditing once bootstrapped. |

High-risk variables are listed in [`docs/strategy/env-matrix.yaml`](../strategy/env-matrix.yaml) and explained in [Configuration reference](../reference/config-env.md).

## Focused enterprise pages

Detailed sections moved for clarity — start at **[Enterprise hub](enterprise-index.md)** for binding, OIDC, allowlists, LLM boundaries, Fleet, and backup/upgrade.

## Verification

1. Run `ss -lptn sport = :8080` → expect **loopback-only** binds unless intentionally widened.
2. Inspect **`~/.lenses-local/governance-audit.jsonl`** after policy edits — tamper-evident-ish trail.
3. Cross-check the **[HTTP API route catalog](../generated/api-routes.md)** and the long-form [HTTP narrative on GitHub](https://github.com/autowww/forge-lenses/blob/main/lenses/website/http-api-and-routes.md) whenever OIDC knobs or Fleet probes change.

## What to do next

- [Enterprise hub](enterprise-index.md)
- [Builders — auth and safety](builders-auth-and-safety.md)
