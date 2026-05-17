---


nav_title: Enterprise — deployment runbook (local-first)
public_publish: true
audience: public
product_area: lenses
tier: practitioner
handbook_area: lenses
learning_level: '301'
section: enterprise
status: shipped
description: Deployment runbook for widening network surfaces responsibly — binds,
  OIDC, automation allowlists, backups, rollback, evidence for incidents.
page_type: runbook
---

# Enterprise — deployment (local-first)

Use this checklist when translating a developer laptop install into something operators can babysit nightly. Maintainer-only depth ships as **[enterprise-runbook-template.md on GitHub](https://github.com/autowww/forge-lenses/blob/main/docs/maintainer/enterprise-runbook-template.md)**.

## Scenario

Operators need repeatable cold starts for **`python3 -m lenses`**, systemd/pm2 equivalents, paired reverse proxies, and backup policies while keeping POST surfaces non-public unless explicitly guarded.

```blueprint-diagram
key: swimlane
alt: Operator checkpoints before widening binds or enabling proxies
caption: Freeze identity → tighten binds/OIDC → widen automation deliberately
```

## Risks vs controls

| Risk | Indicator | Recovery |
|------|-------------|-----------|
| **Accidental egress** when enabling LLMs or Fleet | Surprise outbound HTTPS from ops hosts | Clamp per [LLM boundaries](enterprise-llm-boundaries.md) + binds from [network binding](enterprise-network-binding.md) |
| **Public POST surface** exposed | `/api/**` reachable without reverse-proxy auth | Re-enable **[OIDC sessions](enterprise-oidc-sessions.md)** checkpoints; rerun auth smoke (`curl` rejects on missing tokens) |
| **Upgrade drift** | Mixed Python / wheel versions across machines | Freeze `git describe` artifact in change tickets; reinstall from Releases |

## Ownership (minimal)

**Platform owner** freezes identity + systemd unit content. **Security reviewer** signs off widen-to-prod decisions. Both attach logs from `python3 -m lenses` stderr and sanitized config headers to **[incident response](enterprise-incident-response.md)** timelines when anything regresses.


## Steps

| Step | Action | Notes |
|------|--------|-------|
| 1 | Freeze identity | Capture git SHA (`git describe`) + Python version documented in **[Install and run](02-install-and-run.md)** |
| 2 | Bind responsibly | Decide loopback-only vs bastion/proxy ingress per **[Enterprise — network binding](enterprise-network-binding.md)** |
| 3 | Session hardening | Enable **[Enterprise — OIDC sessions](enterprise-oidc-sessions.md)** whenever `/api/**` crosses trust zones |
| 4 | Allowlists | Cross-check **`LENSES_ALLOW_*`** with **[Enterprise — actions allowlists](enterprise-actions-allowlists.md)** and **[Configuration reference](../reference/config-env.md)** |
| 5 | Backups | Align `.lenses-local/` + repos with **[Enterprise — backup and upgrades](enterprise-backup-upgrades.md)** retention targets |

## Verify

Maintainers mirror the canonical matrix on GitHub — [`docs/strategy/env-matrix.yaml`](https://github.com/autowww/forge-lenses/blob/main/docs/strategy/env-matrix.yaml) — with the handbook page **[Configuration reference](../reference/config-env.md)** inside this repo. Locally, **`pytest tests/test_env_matrix_docs.py`** asserts every variable from the matrix appears in that reference page.

## Recover

Revert network binds to loopback, disable automation allowlists temporarily, redeploy binaries from **[GitHub Releases](https://github.com/autowww/forge-lenses/releases)**, then re-run **[Builders — auth and safety](builders-auth-and-safety.md)** smoke tests prior to widening access again.

## What to read next

- **[Enterprise hub](enterprise-index.md)**
