---


nav_title: Enterprise — incident logging
public_publish: true
audience: public
product_area: lenses
tier: practitioner
handbook_area: lenses
learning_level: '201'
section: enterprise
status: shipped
description: Capture evidence responsibly when Wizard/Studio regressions coincide with tightened security posture.
page_type: concept
---

# Enterprise — incident response (notebook)

Treat this chapter as **evidence scaffolding**: it aligns with **`sample-audit-notification.json`** payloads under `docs/examples/` so automation teams can correlate JSON fixtures with narratives.

## Scenario

Someone widened binds, flipped OIDC proxies, or installed a Fleet shim and now **`/studio/`** flashes blank shells / Wizard sessions silently fail.

## Prerequisites

| Input | Detail |
|-------|--------|
| Time window | Narrow to last change that touched **`LENSES_*`** vars |
| Backups | Snapshots rooted per **[Enterprise — backup and upgrades](enterprise-backup-upgrades.md)** |
| Telemetry | Decide whether Forge Fleet exposes job ids via **[Fleet integration](enterprise-fleet-integration.md)** |

## Step-by-step

1. Freeze configuration — archive `/proc/<pid>/cmdline` equivalents + sanitized env deltas (omit secrets).
2. Route signal — categorize UI vs networking vs **`/api`** using **[Troubleshooting](12-troubleshooting.md)**.
3. Replay minimal GET-only flows (**Docs Health** panels) before re-enabling **`POST`** / mutation allowlists.

## Verify

Captured notes include timestamps, impacted routes, remediation owner, plus whether **[LLM boundaries](enterprise-llm-boundaries.md)** were involved.

## Recover

Restore known-good env files, rerun **`pytest tests/test_env_matrix_docs.py`** locally prior to widening trust again.

## Next steps:

- **`sample-audit-notification.json`** illustrates how JSON fixtures align with SOC-friendly narratives (`docs/schemas/audit-notification.schema.json`).

