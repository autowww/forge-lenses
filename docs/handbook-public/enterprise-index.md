---


nav_title: Enterprise hub
public_publish: true
audience: public
product_area: lenses
tier: overview
handbook_area: lenses
learning_level: overview
section: enterprise
status: shipped
description: Index of enterprise, security, and local-first operations topics.
page_type: landing
---

# Enterprise operations (hub)

Short pages for **binding**, **identity**, **automation flags**, **LLM boundaries**, **Fleet**, and **backup/upgrade** — all cross-linking [Configuration reference](../reference/config-env.md) and the **[high-risk env matrix](../strategy/env-matrix.yaml)**.

## Operator spine (what each page proves)

| Concern | Read for |
|---------|-----------|
| **Local vs outbound** | Which sockets bind locally vs require egress ([network binding](enterprise-network-binding.md), [LLM boundaries](enterprise-llm-boundaries.md)). |
| **Disk writes & retention** | Where snapshots/logs land on disk ([backup & upgrades](enterprise-backup-upgrades.md)). |
| **Repo mutation** | Whether automation flags may alter repos ([allowlists](enterprise-actions-allowlists.md)). |
| **Rollback / availability** | Upgrade sequencing + outage drills ([deployment](enterprise-deployment.md), [backup & upgrades](enterprise-backup-upgrades.md)). |
| **Audit evidence** | Logs + manifests operators can attach to incidents ([incident response](enterprise-incident-response.md)). |

```blueprint-diagram
key: roadmap
alt: Enterprise spine from security review through binding, OIDC, allowlists, Fleet, backups
caption: Each hub row is intentionally short so operators can deep-link into focused runbooks
```

| Topic | Page |
|-------|------|
| Security overview & `.lenses-local` | [Security and local-first operations](17-security-and-local-first.md) |
| Network binding & proxies | [Enterprise — network binding](enterprise-network-binding.md) |
| OIDC & reverse proxies | [Enterprise — OIDC sessions](enterprise-oidc-sessions.md) |
| `LENSES_ALLOW_*` flags | [Enterprise — actions allowlists](enterprise-actions-allowlists.md) |
| LLM data boundaries | [Enterprise — LLM boundaries](enterprise-llm-boundaries.md) |
| Forge Fleet | [Enterprise — Fleet integration](enterprise-fleet-integration.md) |
| Backup, retention, upgrades | [Enterprise — backup and upgrades](enterprise-backup-upgrades.md) |

## Verify

Every **`LENSES_*`** variable listed in [env matrix](../strategy/env-matrix.yaml) appears in [Configuration reference](../reference/config-env.md).

## What to do next

- [Builders — auth and safety](builders-auth-and-safety.md)
