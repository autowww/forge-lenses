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
title: Operator deployment checkpoints
summary: How platform and security lanes coordinate before widening binds, proxies, or automation surfaces.
node: Scenario
detail: Frames the local-first handoff from developer install to operator-managed deployment.
more: Operators need repeatable cold starts, process managers, reverse proxies, and backup policies while POST surfaces stay non-public unless explicitly guarded.
node: Lane A
detail: Platform ownership lane for identity freeze and operational handoff.
more: The platform owner freezes identity and systemd unit content before any widen-to-prod change proceeds.
node: handoff
detail: Transfers frozen git SHA, Python version, and unit definitions to ops.
more: Captures git describe artifact and documented Python version per the freeze-identity checkpoint in the Steps table.
node: shared outcome
detail: Agreed operational baseline ready for deliberate network widening.
more: Both lanes converge on a traceable baseline before binds, OIDC, or allowlists change in production.
node: Lane B
detail: Security review lane that inspects trust-zone crossings before sign-off.
more: The security reviewer signs off widen-to-prod decisions and attaches logs to incident timelines when anything regresses.
node: inspect / adapt
detail: Reviews binds, OIDC checkpoints, and allowlists against enterprise controls.
more: Cross-checks network binding, OIDC sessions for /api/**, and LENSES_ALLOW_* against documented allowlists and the configuration reference.
node: feedback
detail: Returns findings or approval before access is widened again.
more: Failed checks loop back through recovery: revert binds to loopback, disable allowlists temporarily, redeploy from Releases, rerun auth smoke.
caption: Freeze identity → tighten binds/OIDC → widen automation deliberately
fallback_ascii: |
  Scenario

  Lane A ──► handoff ──► shared outcome
  Lane B ──► inspect / adapt ──► feedback
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
